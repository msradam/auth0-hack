"""
Slack integration via Auth0 Token Vault.

Scans real Slack messages and channels for PII / data governance violations
using the Slack Web API. Auth is via Bearer token obtained from Token Vault.
Also supports posting data protection notifications to channels.
Handles file attachments — downloads and scans them for PII using Docling
for binary formats (PDF, DOCX) and direct text decoding for plain text.
"""

import json
import tempfile
from pathlib import Path

import httpx

from amanat.tools.scanner import detect_pii_in_text, redact_pii_in_text
from amanat.knowledge.rules import evaluate_message

SLACK_BASE = "https://slack.com/api"

# Module-level cache for channel info to avoid repeated API calls
_channel_cache: dict[str, dict] = {}


def _headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def _get_channel_info(access_token: str, channel_id: str) -> dict:
    """Helper: fetch channel metadata and cache the result."""
    if channel_id in _channel_cache:
        return _channel_cache[channel_id]

    try:
        resp = httpx.get(
            f"{SLACK_BASE}/conversations.info",
            headers=_headers(access_token),
            params={"channel": channel_id},
            timeout=15,
        )
        data = resp.json()
        if not data.get("ok"):
            info = {
                "channel_id": channel_id,
                "name": channel_id,
                "is_private": False,
                "is_ext_shared": False,
                "num_members": 0,
                "error": data.get("error", "unknown"),
            }
            _channel_cache[channel_id] = info
            return info

        ch = data["channel"]
        info = {
            "channel_id": channel_id,
            "name": ch.get("name", channel_id),
            "is_private": ch.get("is_private", False),
            "is_ext_shared": ch.get("is_ext_shared", False) or ch.get("is_shared", False),
            "num_members": ch.get("num_members", 0),
        }
    except Exception as exc:
        info = {
            "channel_id": channel_id,
            "name": channel_id,
            "is_private": False,
            "is_ext_shared": False,
            "num_members": 0,
            "error": str(exc),
        }

    _channel_cache[channel_id] = info
    return info


# MIME types that Docling can handle (binary document formats)
_DOCLING_MIMES = {
    "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

# MIME types we can decode directly as text
_TEXT_MIMES = {
    "text/plain", "text/csv", "text/tab-separated-values",
    "application/json", "text/markdown", "text/html",
}

# Extension fallback for when MIME is generic
_TEXT_EXTENSIONS = {".csv", ".txt", ".tsv", ".json", ".md", ".html"}


def _scan_slack_file(access_token: str, file_info: dict) -> dict | None:
    """Download a Slack file attachment and scan it for PII.

    Returns a dict with file metadata + PII findings, or None if the file
    can't be scanned (e.g. image, video).
    """
    name = file_info.get("name", "unknown")
    mime = file_info.get("mimetype", "")
    size = file_info.get("size", 0)
    url = file_info.get("url_private", "")

    if not url:
        return None

    # Skip very large files (>10MB) and non-document types
    if size > 10_000_000:
        return None

    suffix = Path(name).suffix.lower()
    is_text = mime in _TEXT_MIMES or suffix in _TEXT_EXTENSIONS
    is_docling = mime in _DOCLING_MIMES or suffix in {".pdf", ".docx", ".pptx", ".xlsx"}

    if not is_text and not is_docling:
        return None

    # Download the file
    try:
        resp = httpx.get(url, headers=_headers(access_token), timeout=30, follow_redirects=True)
        if resp.status_code != 200:
            return None
    except Exception:
        return None

    # Extract text
    text = ""
    if is_docling:
        from amanat.tools.docling_tool import extract_text_from_bytes
        text = extract_text_from_bytes(resp.content, mime)
    elif is_text:
        try:
            text = resp.content.decode("utf-8")
        except UnicodeDecodeError:
            text = resp.content.decode("latin-1", errors="replace")

    if not text.strip():
        return None

    pii = detect_pii_in_text(text)
    if not pii:
        return None

    return {
        "file_name": name,
        "file_id": file_info.get("id", ""),
        "file_type": mime,
        "file_size": size,
        "text_length": len(text),
        "pii_detected": True,
        "pii_types": [p["type"] for p in pii],
        "pii_categories": list(set(p["category"] for p in pii)),
        "pii_count": sum(p["count"] for p in pii),
        "pii_findings": pii,
    }


def search_slack_messages(access_token: str, query: str) -> str:
    """Search Slack messages for a query and scan each hit for PII / violations."""
    try:
        resp = httpx.get(
            f"{SLACK_BASE}/search.messages",
            headers=_headers(access_token),
            params={"query": query, "count": 20},
            timeout=30,
        )
        data = resp.json()
        if not data.get("ok"):
            return json.dumps({
                "error": f"Slack API error: {data.get('error', 'unknown')}",
            }, indent=2)
    except Exception as exc:
        return json.dumps({"error": f"Slack request failed: {exc}"}, indent=2)

    matches = data.get("messages", {}).get("matches", [])

    results = []
    for match in matches:
        text = match.get("text", "")
        channel_obj = match.get("channel", {})
        channel_id = channel_obj.get("id", "") if isinstance(channel_obj, dict) else str(channel_obj)
        channel_name = channel_obj.get("name", channel_id) if isinstance(channel_obj, dict) else str(channel_obj)
        author = match.get("username", match.get("user", "unknown"))

        # Get channel details for visibility / guest assessment
        ch_info = _get_channel_info(access_token, channel_id) if channel_id else {
            "is_private": False, "is_ext_shared": False, "name": channel_name,
        }

        visibility = "private_channel" if ch_info.get("is_private") else "public_channel"
        guest_access = ch_info.get("is_ext_shared", False)

        # PII detection
        pii = detect_pii_in_text(text)

        msg_dict = {
            "channel": f"#{ch_info.get('name', channel_name)}",
            "visibility": visibility,
            "guest_access": guest_access,
            "author": author,
            "content": text,
            "pii_detected": len(pii) > 0,
            "pii_types": [p["type"] for p in pii],
            "timestamp": match.get("ts", ""),
            "permalink": match.get("permalink", ""),
        }

        # Scan file attachments
        file_findings = []
        for f in match.get("files", []):
            finding = _scan_slack_file(access_token, f)
            if finding:
                file_findings.append(finding)
                # Merge file PII types into the message-level results
                pii_types_from_files = [t for ff in file_findings for t in ff["pii_types"]]
                msg_dict["pii_types"] = list(set(msg_dict["pii_types"] + pii_types_from_files))
                msg_dict["pii_detected"] = True

        if file_findings:
            msg_dict["file_attachments"] = file_findings

        # Evaluate against message governance rules
        violations = evaluate_message(msg_dict)
        if violations:
            msg_dict["violations"] = violations

        results.append(msg_dict)

    # --- Text-first output (same format as scanner.py _search_messages) ---
    with_violations = sum(1 for r in results if r.get("violations"))

    lines = [
        f"Searched slack for '{query}'. Found {len(results)} messages with sensitive content. "
        f"{with_violations} have policy violations.",
        "",
    ]
    for r in results:
        channel = r.get("channel", "unknown")
        author = r.get("author", "unknown")
        violations = r.get("violations", [])
        pii_types = ", ".join(r.get("pii_types", [])) or "none"

        lines.append(f"MESSAGE in {channel} by {author} | PII: {pii_types}")
        if r.get("file_attachments"):
            for fa in r["file_attachments"]:
                lines.append(
                    f"  ATTACHED FILE: {fa['file_name']} — "
                    f"{fa['pii_count']} PII instances ({', '.join(fa['pii_types'])})"
                )
        if violations:
            for v in violations:
                lines.append(
                    f"  - {v['severity'].upper()}: {v['rule_name']}. "
                    f"{v['finding']} "
                    f"Action: {v['action']}"
                )
        lines.append("")

    # Add per-channel alert instructions
    if with_violations:
        affected_channels = list(set(r.get("channel", "") for r in results if r.get("violations")))
        lines.append("")
        lines.append(f"AFFECTED CHANNELS: {', '.join(affected_channels)}")
        lines.append(f"Post alerts to each affected channel using: notify_channel(channel=\"CHANNEL_NAME\", pii_summary=\"...\", service=\"slack\")")

    lines.append("\n---JSON---")
    lines.append(json.dumps({
        "service": "slack",
        "query": query,
        "messages_found": len(results),
        "messages_with_violations": with_violations,
        "results": results,
    }))
    return "\n".join(lines)


def scan_slack_channels(access_token: str) -> str:
    """List Slack channels and scan recent messages in public ones for PII / violations."""
    try:
        resp = httpx.get(
            f"{SLACK_BASE}/conversations.list",
            headers=_headers(access_token),
            params={"types": "public_channel,private_channel", "limit": 100},
            timeout=30,
        )
        data = resp.json()
        if not data.get("ok"):
            return json.dumps({
                "error": f"Slack API error: {data.get('error', 'unknown')}",
            }, indent=2)
    except Exception as exc:
        return json.dumps({"error": f"Slack request failed: {exc}"}, indent=2)

    channels = data.get("channels", [])
    all_results = []
    channels_scanned = 0
    total_messages = 0

    for ch in channels:
        # Only scan public channels (we have channels:history scope)
        if ch.get("is_private"):
            continue

        channel_id = ch["id"]
        channel_name = ch.get("name", channel_id)
        is_ext_shared = ch.get("is_ext_shared", False) or ch.get("is_shared", False)

        # Cache this channel info
        _channel_cache[channel_id] = {
            "channel_id": channel_id,
            "name": channel_name,
            "is_private": False,
            "is_ext_shared": is_ext_shared,
            "num_members": ch.get("num_members", 0),
        }

        # Fetch recent messages
        try:
            hist_resp = httpx.get(
                f"{SLACK_BASE}/conversations.history",
                headers=_headers(access_token),
                params={"channel": channel_id, "limit": 50},
                timeout=20,
            )
            hist_data = hist_resp.json()
            if not hist_data.get("ok"):
                continue
        except Exception:
            continue

        messages = hist_data.get("messages", [])
        channels_scanned += 1

        for msg in messages:
            text = msg.get("text", "")
            has_files = bool(msg.get("files"))

            if not text and not has_files:
                continue

            total_messages += 1
            pii = detect_pii_in_text(text) if text else []

            # Scan file attachments
            file_findings = []
            for f in msg.get("files", []):
                finding = _scan_slack_file(access_token, f)
                if finding:
                    file_findings.append(finding)

            if not pii and not file_findings:
                continue

            author = msg.get("user", "unknown")
            visibility = "public_channel"
            guest_access = is_ext_shared

            all_pii_types = [p["type"] for p in pii]
            all_pii_categories = list(set(p["category"] for p in pii))
            for ff in file_findings:
                all_pii_types.extend(ff["pii_types"])
                all_pii_categories.extend(ff["pii_categories"])

            msg_dict = {
                "channel": f"#{channel_name}",
                "visibility": visibility,
                "guest_access": guest_access,
                "author": author,
                "content": text,
                "pii_detected": True,
                "pii_types": list(set(all_pii_types)),
                "pii_categories": list(set(all_pii_categories)),
                "timestamp": msg.get("ts", ""),
            }

            if file_findings:
                msg_dict["file_attachments"] = file_findings

            violations = evaluate_message(msg_dict)
            if violations:
                msg_dict["violations"] = violations

            all_results.append(msg_dict)

    # --- Text-first output ---
    with_violations = sum(1 for r in all_results if r.get("violations"))

    lines = [
        f"Scanned {channels_scanned} public channels ({total_messages} messages). "
        f"Found {len(all_results)} messages with PII. {with_violations} have policy violations.",
        "",
    ]
    for r in all_results:
        channel = r.get("channel", "unknown")
        author = r.get("author", "unknown")
        violations = r.get("violations", [])
        pii_types = ", ".join(r.get("pii_types", [])) or "none"

        lines.append(f"MESSAGE in {channel} by {author} | PII: {pii_types}")
        if r.get("file_attachments"):
            for fa in r["file_attachments"]:
                lines.append(
                    f"  ATTACHED FILE: {fa['file_name']} — "
                    f"{fa['pii_count']} PII instances ({', '.join(fa['pii_types'])})"
                )
        if violations:
            for v in violations:
                lines.append(
                    f"  - {v['severity'].upper()}: {v['rule_name']}. "
                    f"{v['finding']} "
                    f"Action: {v['action']}"
                )
        lines.append("")

    if not all_results:
        lines.append("No messages with PII detected in public channels.")

    # Add per-channel alert instructions
    if with_violations:
        affected_channels = list(set(r.get("channel", "") for r in all_results if r.get("violations")))
        lines.append("")
        lines.append(f"AFFECTED CHANNELS: {', '.join(affected_channels)}")
        lines.append(f"Post alerts to each affected channel using: notify_channel(channel=\"CHANNEL_NAME\", pii_summary=\"...\", service=\"slack\")")

    lines.append("\n---JSON---")
    lines.append(json.dumps({
        "service": "slack",
        "channels_scanned": channels_scanned,
        "total_messages_checked": total_messages,
        "messages_with_pii": len(all_results),
        "messages_with_violations": with_violations,
        "results": all_results,
    }))
    return "\n".join(lines)


def notify_slack_channel(access_token: str, channel: str, pii_summary: str) -> str:
    """Post a data protection notification to a Slack channel.

    Used after scanning detects PII in a channel — alerts the team and
    lists what was found so they can take action.

    Uses the Slack Bot Token (SLACK_BOT_TOKEN) for posting, so the alert
    comes from "Amanat" bot rather than the user's account. The user's
    access_token (via Token Vault) is used for read operations only.

    Args:
        access_token: Slack user token (unused for posting — bot token used instead).
        channel: Channel ID or name (e.g. "C0APFFB1XLJ" or "#field-updates").
        pii_summary: Human-readable summary of findings to include in the alert.
    """
    import os
    bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not bot_token:
        return json.dumps({
            "status": "error",
            "error": "SLACK_BOT_TOKEN not configured",
            "message": "Set SLACK_BOT_TOKEN in .env to enable Slack notifications.",
        }, indent=2)
    # Use bot token for posting — alerts come from "Amanat" bot
    access_token = bot_token
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Data Protection Alert", "emoji": True},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Data Protection Alert*\n\n"
                    f"{pii_summary}"
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Posted by Amanat Data Governance Agent | All analysis runs locally",
                },
            ],
        },
    ]

    fallback_text = f"Data Protection Alert: {pii_summary}"

    try:
        resp = httpx.post(
            f"{SLACK_BASE}/chat.postMessage",
            headers=_headers(access_token),
            json={
                "channel": channel,
                "text": fallback_text,
                "blocks": blocks,
            },
            timeout=15,
        )
        data = resp.json()
        if data.get("ok"):
            return json.dumps({
                "status": "success",
                "channel": channel,
                "message_ts": data.get("ts", ""),
                "message": f"Data protection alert posted to {channel}.",
            }, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "error": data.get("error", "unknown"),
                "message": f"Failed to post notification: {data.get('error')}",
            }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
            "message": f"Slack API request failed: {e}",
        }, indent=2)
