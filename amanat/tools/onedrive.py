"""
Microsoft OneDrive integration via Auth0 Token Vault.

Scans real OneDrive files via Microsoft Graph API, checks sharing permissions,
downloads content for local PII analysis, and performs remediation.
"""

import io
import json
import httpx

from amanat.tools.scanner import detect_pii_in_text
from amanat.knowledge.rules import evaluate_file

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def _list_all_files(access_token: str, folder_id: str = "root") -> list[dict]:
    """Recursively list all files in a OneDrive folder and its subfolders."""
    url = f"{GRAPH_BASE}/me/drive/items/{folder_id}/children"
    params = {
        "$select": "id,name,file,folder,size,lastModifiedDateTime,createdBy,shared,parentReference",
        "$top": "100",
    }
    resp = httpx.get(url, headers=_headers(access_token), params=params, timeout=30)
    if resp.status_code != 200:
        return []

    items = resp.json().get("value", [])
    files = []
    for item in items:
        if "file" in item:
            files.append(item)
        elif "folder" in item:
            # Recurse into subfolders
            files.extend(_list_all_files(access_token, item["id"]))
    return files


def scan_onedrive(access_token: str, query: str | None = None) -> str:
    """List files from OneDrive and scan for PII risk indicators.
    Recursively scans all folders and subfolders."""
    # List all files, filter by query BEFORE downloading/scanning.
    all_items = _list_all_files(access_token)

    if query:
        q = query.lower()
        items = [
            i for i in all_items
            if q in i.get("name", "").lower()
            or q in i.get("parentReference", {}).get("path", "").lower()
        ]
        if not items:
            # Fallback: Graph content search
            try:
                url = f"{GRAPH_BASE}/me/drive/root/search(q='{query}')"
                params = {
                    "$select": "id,name,file,size,lastModifiedDateTime,createdBy,shared,parentReference",
                    "$top": "50",
                }
                resp = httpx.get(url, headers=_headers(access_token), params=params, timeout=30)
                resp.raise_for_status()
                items = [i for i in resp.json().get("value", []) if "file" in i]
            except Exception:
                pass
        if not items:
            items = all_items
    else:
        items = all_items

    scanned = []
    for item in items:
        if "file" not in item:
            continue

        file_id = item["id"]
        name = item["name"]
        size = item.get("size", 0)
        mime = item.get("file", {}).get("mimeType", "")

        # Determine sharing scope
        sharing = _classify_sharing(access_token, file_id)

        # Download and scan for PII using hybrid detection (regex + LLM)
        pii = []
        if size < 5_000_000:
            content = _download_text(access_token, file_id, mime)
            if content:
                pii = detect_pii_in_text(content, use_llm=True)

        owner = ""
        created_by = item.get("createdBy", {})
        if created_by.get("user"):
            owner = created_by["user"].get("displayName", "")

        # Get folder path for context
        parent_ref = item.get("parentReference", {})
        folder_path = parent_ref.get("path", "").replace("/drive/root:", "", 1) or "/"

        file_result = {
            "file_id": file_id,
            "name": name,
            "folder": folder_path,
            "type": mime,
            "size": str(size),
            "owner": owner,
            "sharing": sharing,
            "last_modified": item.get("lastModifiedDateTime", ""),
            "pii_detected": len(pii) > 0,
            "pii_categories": list(set(p["category"] for p in pii)),
            "risk_level": (
                "critical" if any(p["severity"] == "critical" for p in pii) else
                "warning" if pii else "info"
            ),
        }
        # Evaluate against governance rules
        violations = evaluate_file(file_result)
        if violations:
            file_result["violations"] = violations
            if any(v["severity"] == "critical" for v in violations):
                file_result["risk_level"] = "critical"
        scanned.append(file_result)

    # Build text summary for the agent (before JSON)
    lines = [
        f"Scanned {len(scanned)} files, {sum(1 for s in scanned if s['pii_detected'])} contain PII",
    ]
    # Collect violating file IDs for batch remediation
    violating_ids = []
    for s in scanned:
        risk = s.get("risk_level", "info")
        sharing = s.get("sharing", "unknown")
        icon = "🔴" if risk == "critical" else "🟡" if risk == "warning" else "🟢"
        lines.append(f"{icon} {s['name']} — {risk} risk, shared: {sharing}")
        if s.get("pii_detected") and sharing in ("anyone_with_link", "org_wide"):
            violating_ids.append(s["file_id"])

    if violating_ids:
        ids_str = ",".join(violating_ids)
        lines.append("")
        lines.append(f"VIOLATING FILES REQUIRING REMEDIATION: {len(violating_ids)} file(s)")
        lines.append(f"To revoke all at once, call: revoke_sharing(file_id=\"{ids_str}\", service=\"onedrive\")")

    lines.append("\n---JSON---")
    lines.append(json.dumps({
        "service": "onedrive",
        "files_scanned": len(scanned),
        "files_with_pii": sum(1 for s in scanned if s["pii_detected"]),
        "results": scanned,
    }))
    return "\n".join(lines)


def check_onedrive_sharing(access_token: str, file_id: str) -> str:
    """Check detailed sharing permissions for a OneDrive file."""
    # Get file info
    url = f"{GRAPH_BASE}/me/drive/items/{file_id}"
    resp = httpx.get(
        url,
        headers=_headers(access_token),
        params={"$select": "id,name,shared,createdBy"},
        timeout=30,
    )
    resp.raise_for_status()
    item = resp.json()

    # Get permissions
    perm_url = f"{GRAPH_BASE}/me/drive/items/{file_id}/permissions"
    perm_resp = httpx.get(perm_url, headers=_headers(access_token), timeout=30)
    perms = perm_resp.json().get("value", []) if perm_resp.status_code == 200 else []

    sharing = _classify_from_permissions(perms)

    sharing_risk = {
        "anyone_with_link": "critical",
        "org_wide": "warning",
        "specific_people": "info",
        "private": "info",
    }

    result = {
        "file_id": file_id,
        "name": item.get("name", ""),
        "sharing_scope": sharing,
        "sharing_risk": sharing_risk.get(sharing, "unknown"),
        "permissions": [
            {
                "type": p.get("link", {}).get("scope", p.get("grantedTo", {}).get("user", {}).get("displayName", "owner")),
                "role": ", ".join(p.get("roles", [])),
                "link_type": p.get("link", {}).get("type", ""),
            }
            for p in perms
        ],
    }

    if sharing == "anyone_with_link":
        result["issue"] = (
            "File is accessible to anyone with the link. This includes people outside "
            "the organisation. If this file contains beneficiary data, any person with "
            "the URL can access sensitive personal information."
        )
    elif sharing == "org_wide":
        result["issue"] = (
            "File is shared with the entire organisation. Not all staff may be authorised "
            "to view this data. Apply need-to-know access restrictions."
        )

    return json.dumps(result, indent=2)


def detect_onedrive_pii(access_token: str, file_id: str) -> str:
    """Download a OneDrive file and scan its content for PII."""
    # Get file metadata
    url = f"{GRAPH_BASE}/me/drive/items/{file_id}"
    resp = httpx.get(
        url,
        headers=_headers(access_token),
        params={"$select": "id,name,file,size"},
        timeout=30,
    )
    resp.raise_for_status()
    item = resp.json()

    mime = item.get("file", {}).get("mimeType", "")
    content = _download_text(access_token, file_id, mime)

    if not content:
        return json.dumps({
            "file_id": file_id,
            "name": item.get("name", ""),
            "pii_findings": [],
            "summary": "Could not extract text content from this file.",
        })

    pii_findings = detect_pii_in_text(content, use_llm=True)

    return json.dumps({
        "file_id": file_id,
        "name": item.get("name", ""),
        "pii_findings": pii_findings,
        "total_pii_types": len(pii_findings),
        "has_special_category_data": any(
            p["category"] in ("special_category_data", "biometric_data")
            for p in pii_findings
        ),
        "summary": (
            f"Found {len(pii_findings)} types of PII/sensitive data. "
            f"Categories: {', '.join(set(p['category'] for p in pii_findings))}"
            if pii_findings else "No PII detected."
        ),
    }, indent=2)


def _revoke_single_file(access_token: str, file_id: str) -> dict:
    """Revoke sharing links on a single OneDrive file. Returns result dict."""
    perm_url = f"{GRAPH_BASE}/me/drive/items/{file_id}/permissions"
    perm_resp = httpx.get(perm_url, headers=_headers(access_token), timeout=30)
    perms = perm_resp.json().get("value", []) if perm_resp.status_code == 200 else []

    item_resp = httpx.get(
        f"{GRAPH_BASE}/me/drive/items/{file_id}",
        headers=_headers(access_token),
        params={"$select": "name"},
        timeout=30,
    )
    name = item_resp.json().get("name", file_id) if item_resp.status_code == 200 else file_id

    removed = []
    for p in perms:
        if p.get("link"):
            scope = p["link"].get("scope", "")
            if scope in ("anonymous", "organization"):
                del_url = f"{GRAPH_BASE}/me/drive/items/{file_id}/permissions/{p['id']}"
                del_resp = httpx.delete(del_url, headers=_headers(access_token), timeout=30)
                if del_resp.status_code in (200, 204):
                    removed.append(scope)

    return {
        "file_id": file_id,
        "name": name,
        "permissions_removed": len(removed),
        "status": "revoked" if removed else "no_public_permissions",
    }


def revoke_onedrive_sharing(access_token: str, file_id: str) -> str:
    """Revoke sharing links on one or more OneDrive files.

    file_id: a single ID or multiple comma-separated IDs.
    """
    results = []
    ids = [fid.strip() for fid in file_id.split(",") if fid.strip()]
    for fid in ids:
        results.append(_revoke_single_file(access_token, fid))

    total_revoked = sum(r["permissions_removed"] for r in results)
    revoked_names = [r["name"] for r in results if r["status"] == "revoked"]
    skipped_names = [r["name"] for r in results if r["status"] == "skipped_no_pii"]

    lines = []
    if revoked_names:
        lines.append(
            f"Revoked public sharing on {len(revoked_names)} file(s) containing PII: "
            f"{', '.join(revoked_names)}."
        )
    if skipped_names:
        lines.append(
            f"Kept sharing on {len(skipped_names)} file(s) with no PII detected: "
            f"{', '.join(skipped_names)}."
        )
    if not revoked_names and not skipped_names:
        lines.append("No publicly shared files found matching the criteria.")

    return json.dumps({
        "action": "revoke_sharing",
        "files_processed": len(results),
        "files_revoked": len(revoked_names),
        "files_skipped_no_pii": len(skipped_names),
        "total_permissions_removed": total_revoked,
        "files": results,
        "message": " ".join(lines),
    }, indent=2)


def download_onedrive_file(access_token: str, file_id: str) -> str:
    """Download a OneDrive file to local storage."""
    # Get file metadata
    url = f"{GRAPH_BASE}/me/drive/items/{file_id}"
    resp = httpx.get(
        url,
        headers=_headers(access_token),
        params={"$select": "id,name,file,size"},
        timeout=30,
    )
    resp.raise_for_status()
    item = resp.json()

    mime = item.get("file", {}).get("mimeType", "")
    content = _download_text(access_token, file_id, mime)

    if content:
        import os
        local_dir = os.path.expanduser("~/.amanat/downloads")
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, item["name"])
        with open(local_path, "w") as fp:
            fp.write(content)

        return json.dumps({
            "file_id": file_id,
            "name": item["name"],
            "action": "download",
            "local_path": local_path,
            "size_bytes": len(content),
            "status": "success",
            "message": f"File downloaded to {local_path}. Data remains on this machine only.",
        }, indent=2)

    return json.dumps({
        "file_id": file_id,
        "name": item.get("name", ""),
        "action": "download",
        "status": "failed",
        "message": "Could not download file content.",
    }, indent=2)


def delete_onedrive_file(access_token: str, file_id: str) -> str:
    """Delete a file from OneDrive (moves to recycle bin, recoverable)."""
    # Get file name first
    url = f"{GRAPH_BASE}/me/drive/items/{file_id}"
    resp = httpx.get(
        url,
        headers=_headers(access_token),
        params={"$select": "id,name"},
        timeout=30,
    )
    resp.raise_for_status()
    name = resp.json().get("name", file_id)

    # Delete (moves to recycle bin)
    del_resp = httpx.delete(url, headers=_headers(access_token), timeout=30)

    if del_resp.status_code in (200, 204):
        return json.dumps({
            "file_id": file_id,
            "name": name,
            "action": "delete",
            "status": "success",
            "message": f"File '{name}' moved to recycle bin. It can be recovered within 93 days.",
        }, indent=2)

    return json.dumps({
        "file_id": file_id,
        "name": name,
        "action": "delete",
        "status": "failed",
        "message": f"Failed to delete file: {del_resp.status_code} {del_resp.text[:200]}",
    }, indent=2)


# --- Helpers ---

def _classify_sharing(access_token: str, file_id: str) -> str:
    """Classify sharing scope by checking file permissions."""
    perm_url = f"{GRAPH_BASE}/me/drive/items/{file_id}/permissions"
    try:
        resp = httpx.get(perm_url, headers=_headers(access_token), timeout=10)
        if resp.status_code != 200:
            return "unknown"
        perms = resp.json().get("value", [])
        return _classify_from_permissions(perms)
    except Exception:
        return "unknown"


def _classify_from_permissions(perms: list[dict]) -> str:
    """Classify sharing scope from OneDrive permissions list."""
    for p in perms:
        link = p.get("link", {})
        scope = link.get("scope", "")
        if scope == "anonymous":
            return "anyone_with_link"
        if scope == "organization":
            return "org_wide"
    # If there are granted permissions beyond owner
    granted = [p for p in perms if p.get("grantedToV2") or p.get("grantedTo")]
    if len(granted) > 1:
        return "specific_people"
    return "private"


def _download_text(access_token: str, file_id: str, mime_type: str) -> str:
    """Download file content as text from OneDrive.

    For plain text formats (CSV, TXT, JSON, Markdown): decode directly.
    For binary document formats (PDF, DOCX, PPTX, XLSX): use Docling to
    extract text, including OCR for scanned PDFs with no embedded text.
    """
    from amanat.tools.docling_tool import DOCLING_MIMES, extract_text_from_bytes

    try:
        url = f"{GRAPH_BASE}/me/drive/items/{file_id}/content"
        resp = httpx.get(url, headers=_headers(access_token), timeout=30, follow_redirects=True)

        if resp.status_code != 200:
            return ""

        # Binary document formats — use Docling for text extraction
        if mime_type in DOCLING_MIMES:
            return extract_text_from_bytes(resp.content, mime_type)

        # Plain text formats — decode directly
        try:
            return resp.content.decode("utf-8")
        except UnicodeDecodeError:
            return resp.content.decode("latin-1", errors="replace")

    except Exception:
        return ""
