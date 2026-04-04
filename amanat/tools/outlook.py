"""
Microsoft Outlook / email integration via Microsoft Graph API.

Scans real Outlook emails via Graph API for PII and data governance violations.
Uses Bearer token auth obtained through Auth0 Token Vault.
"""

import json
import re
from datetime import datetime, timedelta, timezone

import httpx

from amanat.tools.scanner import detect_pii_in_text
from amanat.knowledge.rules import evaluate_message

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def _extract_email_text(body: dict) -> str:
    """Extract plain text from a Graph API body object.

    The body dict has ``contentType`` ("text" or "html") and ``content``.
    For HTML content we do a basic tag strip — no full parser needed.
    """
    content = body.get("content", "")
    content_type = body.get("contentType", "text")

    if content_type == "html":
        # Strip HTML tags
        text = re.sub(r"<[^>]+>", " ", content)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    return content


def _is_external_recipient(sender_domain: str, recipients: list[dict]) -> bool:
    """Check if any recipient's email domain differs from the sender domain.

    Recipients use Graph API format::

        [{"emailAddress": {"name": "...", "address": "user@domain.com"}}]
    """
    for recip in recipients:
        addr = recip.get("emailAddress", {}).get("address", "")
        if "@" in addr:
            domain = addr.split("@")[-1].lower()
            if domain and domain != sender_domain.lower():
                return True
    return False


def search_outlook_messages(access_token: str, query: str) -> str:
    """Search Outlook emails via Microsoft Graph and scan for PII / policy violations."""
    url = f"{GRAPH_BASE}/me/messages"
    params = {
        "$search": f'"{query}"',
        "$top": "25",
        "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,bodyPreview,body,hasAttachments",
    }

    try:
        resp = httpx.get(url, headers=_headers(access_token), params=params, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 403:
            return json.dumps({
                "error": "Outlook access denied. Reconnect Microsoft with Mail.Read permissions via the Connect Microsoft link on the welcome screen.",
            }, indent=2)
        return json.dumps({
            "error": f"Graph API error: {exc.response.status_code} {exc.response.text[:300]}",
        }, indent=2)
    except httpx.RequestError as exc:
        return json.dumps({"error": f"Request failed: {exc}"}, indent=2)

    messages = resp.json().get("value", [])

    results = []
    for msg in messages:
        body_text = _extract_email_text(msg.get("body", {}))
        # Fall back to bodyPreview if body content is empty
        if not body_text.strip():
            body_text = msg.get("bodyPreview", "")

        pii = detect_pii_in_text(body_text)

        sender_addr = msg.get("from", {}).get("emailAddress", {}).get("address", "")
        sender_domain = sender_addr.split("@")[-1] if "@" in sender_addr else ""

        to_recipients = msg.get("toRecipients", [])
        cc_recipients = msg.get("ccRecipients", [])
        first_to = (
            to_recipients[0].get("emailAddress", {}).get("address", "")
            if to_recipients else ""
        )

        external = _is_external_recipient(
            sender_domain, to_recipients + cc_recipients
        )

        # Build a dict compatible with evaluate_message()
        message_dict = {
            "subject": msg.get("subject", ""),
            "from": sender_addr,
            "to": first_to,
            "content": body_text,
            "pii_detected": len(pii) > 0,
            "pii_types": [p["type"] for p in pii],
            "external_recipient": external,
            "timestamp": msg.get("receivedDateTime", ""),
            "has_attachments": msg.get("hasAttachments", False),
            "message_id": msg.get("id", ""),
        }

        violations = evaluate_message(message_dict)
        if violations:
            message_dict["violations"] = violations

        results.append(message_dict)

    # Text-first output (same format as scanner.py _search_messages)
    with_violations = sum(1 for r in results if r.get("violations"))

    lines = [
        f"Searched Outlook for '{query}'. Found {len(results)} messages with content. "
        f"{with_violations} have policy violations.",
        "",
    ]
    violating_contacts = set()
    for r in results:
        subject = r.get("subject", "(no subject)")
        sender = r.get("from", "unknown")
        recipient = r.get("to", "unknown")
        violations = r.get("violations", [])
        pii_types = ", ".join(r.get("pii_types", [])) or "none"
        ext_flag = " [EXTERNAL]" if r.get("external_recipient") else ""

        lines.append(f"EMAIL: {subject} | from: {sender} | to: {recipient}{ext_flag} | PII: {pii_types}")
        if violations:
            violating_contacts.add(sender)
            violating_contacts.add(recipient)
            for v in violations:
                lines.append(
                    f"  - {v['severity'].upper()}: {v['rule_name']}. "
                    f"{v['finding']} "
                    f"Action: {v['action']}"
                )
        lines.append("")

    if violating_contacts:
        lines.append(f"CONTACTS TO ALERT: {', '.join(violating_contacts)}")
        lines.append("Send alert emails using: send_email(to=\"ADDRESS\", subject=\"Data Protection Alert\", body=\"...\")")

    lines.append("\n---JSON---")
    lines.append(json.dumps({
        "service": "outlook",
        "query": query,
        "messages_found": len(results),
        "messages_with_violations": with_violations,
        "results": results,
    }))
    return "\n".join(lines)


def scan_outlook_recent(access_token: str, days: int = 30) -> str:
    """Scan recent Outlook emails for PII leaks and policy violations."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    url = f"{GRAPH_BASE}/me/messages"
    params = {
        "$top": "50",
        "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,bodyPreview,body,hasAttachments",
        "$orderby": "receivedDateTime desc",
        "$filter": f"receivedDateTime ge {cutoff_str}",
    }

    try:
        resp = httpx.get(url, headers=_headers(access_token), params=params, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return json.dumps({
            "error": f"Graph API error: {exc.response.status_code} {exc.response.text[:300]}",
        }, indent=2)
    except httpx.RequestError as exc:
        return json.dumps({"error": f"Request failed: {exc}"}, indent=2)

    messages = resp.json().get("value", [])

    results = []
    for msg in messages:
        body_text = _extract_email_text(msg.get("body", {}))
        if not body_text.strip():
            body_text = msg.get("bodyPreview", "")

        pii = detect_pii_in_text(body_text)
        if not pii:
            continue  # Only include emails with PII findings

        sender_addr = msg.get("from", {}).get("emailAddress", {}).get("address", "")
        sender_domain = sender_addr.split("@")[-1] if "@" in sender_addr else ""

        to_recipients = msg.get("toRecipients", [])
        cc_recipients = msg.get("ccRecipients", [])
        first_to = (
            to_recipients[0].get("emailAddress", {}).get("address", "")
            if to_recipients else ""
        )

        external = _is_external_recipient(
            sender_domain, to_recipients + cc_recipients
        )

        message_dict = {
            "subject": msg.get("subject", ""),
            "from": sender_addr,
            "to": first_to,
            "content": body_text,
            "pii_detected": True,
            "pii_types": [p["type"] for p in pii],
            "pii_categories": list(set(p["category"] for p in pii)),
            "external_recipient": external,
            "timestamp": msg.get("receivedDateTime", ""),
            "has_attachments": msg.get("hasAttachments", False),
            "message_id": msg.get("id", ""),
        }

        violations = evaluate_message(message_dict)
        if violations:
            message_dict["violations"] = violations

        results.append(message_dict)

    with_violations = sum(1 for r in results if r.get("violations"))

    lines = [
        f"Scanned last {days} days of Outlook email. "
        f"Found {len(results)} emails containing PII. "
        f"{with_violations} have policy violations.",
        "",
    ]
    for r in results:
        subject = r.get("subject", "(no subject)")
        sender = r.get("from", "unknown")
        violations = r.get("violations", [])
        pii_types = ", ".join(r.get("pii_types", [])) or "none"
        ext_flag = " [EXTERNAL]" if r.get("external_recipient") else ""

        lines.append(f"EMAIL: {subject} from {sender}{ext_flag} | PII: {pii_types}")
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
        "service": "outlook",
        "scan_type": "recent",
        "days_scanned": days,
        "messages_with_pii": len(results),
        "messages_with_violations": with_violations,
        "results": results,
    }))
    return "\n".join(lines)


def send_outlook_email(access_token: str, to: str, subject: str, body: str) -> str:
    """Send an email via Microsoft Graph API."""
    resp = httpx.post(
        f"{GRAPH_BASE}/me/sendMail",
        headers=_headers(access_token) | {"Content-Type": "application/json"},
        json={
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": to}}],
            }
        },
        timeout=15,
    )
    if resp.status_code == 202:
        return json.dumps({"status": "success", "to": to, "subject": subject,
                           "message": f"Email sent to {to}."})
    return json.dumps({"status": "error", "code": resp.status_code,
                       "message": f"Failed to send: {resp.text[:200]}"})
