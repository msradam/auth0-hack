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


def scan_onedrive(access_token: str, query: str | None = None) -> str:
    """List files from OneDrive and scan for PII risk indicators."""
    # Search or list files
    if query:
        url = f"{GRAPH_BASE}/me/drive/root/search(q='{query}')"
    else:
        url = f"{GRAPH_BASE}/me/drive/root/children"

    params = {
        "$select": "id,name,file,size,lastModifiedDateTime,createdBy,shared,parentReference",
        "$top": "25",
    }

    resp = httpx.get(url, headers=_headers(access_token), params=params, timeout=30)
    resp.raise_for_status()
    items = resp.json().get("value", [])

    scanned = []
    for item in items:
        # Skip folders
        if "file" not in item:
            continue

        file_id = item["id"]
        name = item["name"]
        size = item.get("size", 0)
        mime = item.get("file", {}).get("mimeType", "")

        # Determine sharing scope
        sharing = _classify_sharing(access_token, file_id)

        # Download and scan small text-like files for PII
        pii = []
        if size < 5_000_000:
            content = _download_text(access_token, file_id, mime)
            if content:
                pii = detect_pii_in_text(content)

        owner = ""
        created_by = item.get("createdBy", {})
        if created_by.get("user"):
            owner = created_by["user"].get("displayName", "")

        file_result = {
            "file_id": file_id,
            "name": name,
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

    return json.dumps({
        "service": "onedrive",
        "files_scanned": len(scanned),
        "files_with_pii": sum(1 for s in scanned if s["pii_detected"]),
        "results": scanned,
    }, indent=2)


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

    pii_findings = detect_pii_in_text(content)

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


def revoke_onedrive_sharing(access_token: str, file_id: str) -> str:
    """Revoke sharing links on a OneDrive file."""
    # Get current permissions
    perm_url = f"{GRAPH_BASE}/me/drive/items/{file_id}/permissions"
    perm_resp = httpx.get(perm_url, headers=_headers(access_token), timeout=30)
    perms = perm_resp.json().get("value", []) if perm_resp.status_code == 200 else []

    # Get file name
    item_resp = httpx.get(
        f"{GRAPH_BASE}/me/drive/items/{file_id}",
        headers=_headers(access_token),
        params={"$select": "name"},
        timeout=30,
    )
    name = item_resp.json().get("name", file_id) if item_resp.status_code == 200 else file_id

    removed = []
    for p in perms:
        # Remove sharing links (anonymous or organization-wide)
        if p.get("link"):
            scope = p["link"].get("scope", "")
            if scope in ("anonymous", "organization"):
                del_url = f"{GRAPH_BASE}/me/drive/items/{file_id}/permissions/{p['id']}"
                del_resp = httpx.delete(del_url, headers=_headers(access_token), timeout=30)
                if del_resp.status_code in (200, 204):
                    removed.append({
                        "scope": scope,
                        "type": p["link"].get("type", ""),
                        "permission_id": p["id"],
                    })

    return json.dumps({
        "file_id": file_id,
        "name": name,
        "action": "revoke_sharing",
        "permissions_removed": removed,
        "status": "success" if removed else "no_public_permissions_found",
        "message": (
            f"Removed {len(removed)} public/link sharing permissions. "
            f"File is now restricted to explicitly shared users only."
            if removed else
            "No public or link-based permissions found on this file."
        ),
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
    """Download file content as text from OneDrive."""
    try:
        # Text-like files: download directly
        text_mimes = (
            "text/plain", "text/csv", "text/tab-separated-values",
            "application/json", "text/markdown", "text/html",
        )

        url = f"{GRAPH_BASE}/me/drive/items/{file_id}/content"
        resp = httpx.get(url, headers=_headers(access_token), timeout=30, follow_redirects=True)

        if resp.status_code != 200:
            return ""

        # Try to decode as text
        try:
            return resp.content.decode("utf-8")
        except UnicodeDecodeError:
            return resp.content.decode("latin-1", errors="replace")

    except Exception:
        return ""
