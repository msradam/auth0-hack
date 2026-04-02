"""
Slack integration via Auth0 Token Vault.

Scans real Slack messages and channels for PII / data governance violations
using the Slack Web API. Auth is via Bearer token obtained from Token Vault.
"""

import json
import httpx

from amanat.tools.scanner import detect_pii_in_text
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
        if violations:
            for v in violations:
                lines.append(
                    f"  - {v['severity'].upper()}: {v['rule_name']}. "
                    f"{v['finding']} "
                    f"Action: {v['action']}"
                )
        lines.append("")

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
            if not text:
                continue

            total_messages += 1
            pii = detect_pii_in_text(text)
            if not pii:
                continue

            author = msg.get("user", "unknown")
            visibility = "public_channel"
            guest_access = is_ext_shared

            msg_dict = {
                "channel": f"#{channel_name}",
                "visibility": visibility,
                "guest_access": guest_access,
                "author": author,
                "content": text,
                "pii_detected": True,
                "pii_types": [p["type"] for p in pii],
                "pii_categories": list(set(p["category"] for p in pii)),
                "timestamp": msg.get("ts", ""),
            }

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
