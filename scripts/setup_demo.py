"""
Programmatically set up the Amanat demo environment.

OneDrive:
  - Creates /HRC-Demo/ folder
  - Uploads all files from demo-data/drive/ with realistic sharing settings

Slack:
  - Creates #field-updates, #general, #protection channels
  - Posts scripted PII-laden messages in each
  - Uploads the GBV and biometric PDFs as file attachments

Run after logging into Amanat at least once (to populate /tmp/amanat_tokens.txt):
    uv run python scripts/setup_demo.py
"""

import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).parent.parent
DRIVE_DIR = REPO_ROOT / "demo-data" / "drive"

DOMAIN = os.environ["AUTH0_DOMAIN"]
CLIENT_ID = os.environ["AUTH0_CLIENT_ID"]
CLIENT_SECRET = os.environ["AUTH0_CLIENT_SECRET"]
GRAPH = "https://graph.microsoft.com/v1.0"


# ── Token exchange ─────────────────────────────────────────────────────────────

def _get_refresh_token() -> str:
    try:
        text = Path("/tmp/amanat_tokens.txt").read_text()
        for line in text.splitlines():
            if line.startswith("refresh_token:"):
                return line.split(":", 1)[1].strip()
    except FileNotFoundError:
        pass
    sys.exit("No refresh token found. Log into Amanat at http://localhost:8000 first.")


def _exchange_token(refresh_token: str, connection: str, scopes: list[str]) -> str:
    """Exchange Auth0 refresh token for a federated service access token via Token Vault."""
    r = httpx.post(f"https://{DOMAIN}/oauth/token", data={
        "grant_type": "urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "subject_token": refresh_token,
        "subject_token_type": "urn:ietf:params:oauth:token-type:refresh_token",
        "requested_token_type": "http://auth0.com/oauth/token-type/federated-connection-access-token",
        "connection": connection,
        "scope": " ".join(scopes),
    })
    if r.status_code != 200:
        raise RuntimeError(f"Token exchange failed for {connection}: {r.text[:300]}")
    return r.json()["access_token"]


# ── OneDrive setup ─────────────────────────────────────────────────────────────

def _create_folder(headers: dict, parent_id: str, name: str) -> str | None:
    """Create a folder under parent_id, return its ID."""
    r = httpx.post(f"{GRAPH}/me/drive/items/{parent_id}/children", headers=headers, json={
        "name": name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "replace",
    })
    if r.status_code in (200, 201):
        fid = r.json()["id"]
        print(f"  Created /{name}/ ({fid[:16]}...)")
        return fid
    print(f"  Folder {name}: {r.status_code} {r.text[:150]}")
    return None


def _upload_file(headers: dict, folder_id: str, local_path: Path) -> str | None:
    """Upload a file to a folder, return its item ID."""
    content = local_path.read_bytes()
    r = httpx.put(
        f"{GRAPH}/me/drive/items/{folder_id}:/{local_path.name}:/content",
        headers={**headers, "Content-Type": "application/octet-stream"},
        content=content,
        timeout=60,
    )
    if r.status_code in (200, 201):
        return r.json()["id"]
    print(f"  Upload {local_path.name}: {r.status_code} {r.text[:100]}")
    return None


def _share_publicly(headers: dict, item_id: str, name: str):
    """Create an anonymous sharing link on a file (the violation for demo)."""
    r = httpx.post(
        f"{GRAPH}/me/drive/items/{item_id}/createLink",
        headers=headers,
        json={"type": "view", "scope": "anonymous"},
    )
    if r.status_code in (200, 201):
        print(f"    -> Shared publicly (anyone with link)")


def setup_onedrive(token: str):
    print("\n=== OneDrive ===")
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Delete ALL existing files in root
    print("  Clearing existing files...")
    r = httpx.get(f"{GRAPH}/me/drive/root/children",
                  headers=headers, params={"$top": "100"}, timeout=30)
    if r.status_code == 200:
        for item in r.json().get("value", []):
            name = item.get("name", "")
            httpx.delete(f"{GRAPH}/me/drive/items/{item['id']}",
                         headers=headers, timeout=15)
            print(f"    Deleted {name}")
    time.sleep(1)

    # Step 2: Create folder structure
    # /WRA Operations/
    #   /Beneficiary Records/    — registration, displaced registry (sensitive)
    #   /Protection/             — GBV reports, protection assessments (CRITICAL)
    #   /Biometric Data/         — enrollment logs, verification (special category)
    #   /Field Operations/       — staff contacts, site registers
    #   /Donor Relations/        — donor reports (should be clean)
    #   /Scanned Documents/      — uploaded PDFs from field (image-only)

    root_r = httpx.get(f"{GRAPH}/me/drive/root", headers=headers)
    root_id = root_r.json()["id"]

    wra_id = _create_folder(headers, root_id, "WRA Operations")
    if not wra_id:
        return

    beneficiary_id = _create_folder(headers, wra_id, "Beneficiary Records")
    protection_id = _create_folder(headers, wra_id, "Protection")
    biometric_id = _create_folder(headers, wra_id, "Biometric Data")
    field_id = _create_folder(headers, wra_id, "Field Operations")
    donor_id = _create_folder(headers, wra_id, "Donor Relations")
    scanned_id = _create_folder(headers, wra_id, "Scanned Documents")

    # Step 3: Upload files into appropriate folders
    # Map files to folders with sharing violations
    file_plan = [
        # (filename, folder_id, share_publicly)
        ("Cataclysm_Displaced_Registry_2026.csv", beneficiary_id, False),
        ("GBV_Incident_Reports_2026.csv",         protection_id,  True),   # VIOLATION: public share
        ("GBV_Incident_Report_Scanned.pdf",       protection_id,  True),   # VIOLATION: public share
        ("Protection_Assessment_Scanned.pdf",     protection_id,  False),
        ("Biometric_Enrollment_Log.csv",          biometric_id,   True),   # VIOLATION: public share
        ("Biometric_Consent_Scanned.pdf",         biometric_id,   True),   # VIOLATION: public share
        ("Biometric_Verification_Log_Scanned.pdf", biometric_id,  True),   # VIOLATION: public share
        ("Field_Team_Contacts.csv",               field_id,       False),
        ("Site_Population_Register_Scanned.pdf",  field_id,       False),
        ("Beneficiary_Registration_Scanned.pdf",  scanned_id,     False),
        ("Donor_Report_Q1_2026.txt",              donor_id,       False),
    ]

    for fname, folder, share in file_plan:
        fpath = DRIVE_DIR / fname
        if not fpath.exists():
            print(f"  Skipping {fname} — not found")
            continue
        if not folder:
            print(f"  Skipping {fname} — no folder")
            continue

        item_id = _upload_file(headers, folder, fpath)
        if item_id:
            print(f"  Uploaded {fname}")
            if share:
                _share_publicly(headers, item_id, fname)

    print("  OneDrive setup complete.")
    print()
    print("  Folder structure:")
    print("  /WRA Operations/")
    print("    /Beneficiary Records/   — displaced registry")
    print("    /Protection/            — GBV reports (PUBLIC — violation!)")
    print("    /Biometric Data/        — enrollment logs (PUBLIC — violation!)")
    print("    /Field Operations/      — staff contacts, site register")
    print("    /Donor Relations/       — donor report")
    print("    /Scanned Documents/     — registration form PDF")


# ── Slack setup ────────────────────────────────────────────────────────────────

SLACK_API = "https://slack.com/api"

CHANNELS = [
    {"name": "field-updates", "is_private": False},
    {"name": "general",       "is_private": False},
    {"name": "protection",    "is_private": True},
]

MESSAGES = {
    "field-updates": [
        "Update from Kanbaloh: Rozel al-Bahar (case WAQ-26C00891) didn't show for his appointment today. His wife says he went to Ambara for medical treatment. Will follow up tomorrow. His shelter is Block 4, #17 if anyone is in the area.",
        "Sofala update: 3 new GBV referrals this week. One involves a 15-year-old in Vakwa Shelter — flagging for child protection team. Case details uploaded to shared drive.",
        "Finley Maji (WAQ-26C00892) needs urgent medical transport to Ambara Village. She's 8 months pregnant and HIV positive — the Kanbaloh clinic can't handle high-risk deliveries. Can someone arrange transport by Thursday?",
    ],
    "general": [
        "Reminder: donor visit next week. Make sure all beneficiary data is accessible for the audit. I've shared the case files folder with the Ambara Development Fund audit team's email (audit@ambara-fund.org).",
        "New contractor starting Monday — a Majali researcher from Majala. They'll need access to the displaced persons database for the records migration. Can someone share the credentials?",
    ],
    "protection": [
        "CONFIDENTIAL: GBV case GBV-2026-003 update. Survivor has agreed to proceed with legal case. Perpetrator identified as distribution staff member. Do NOT discuss in #general.",
    ],
}

# Files to attach to Slack channels
SLACK_FILE_ATTACHMENTS = {
    "field-updates": ["GBV_Incident_Report_Scanned.pdf"],
    "protection":    ["GBV_Incident_Reports_2026.csv", "Biometric_Consent_Scanned.pdf"],
}


def _slack(method: str, endpoint: str, token: str, **kwargs) -> dict:
    r = httpx.request(
        method,
        f"{SLACK_API}/{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        **kwargs,
    )
    data = r.json()
    if not data.get("ok"):
        print(f"  Slack {endpoint} error: {data.get('error', data)}")
    return data


def setup_slack(token: str):
    print("\n=== Slack ===")

    channel_ids = {}

    # Find existing channels first
    result = _slack("GET", "conversations.list", token,
                    params={"types": "public_channel", "limit": 200})
    if result.get("ok"):
        for c in result.get("channels", []):
            channel_ids[c["name"]] = c["id"]

    for ch in CHANNELS:
        name = ch["name"]
        if name in channel_ids:
            print(f"  Found #{name} ({channel_ids[name]})")
        else:
            # Try to create if we have the scope
            r = _slack("POST", "conversations.create", token, json={
                "name": name,
                "is_private": ch["is_private"],
            })
            if r.get("ok"):
                channel_ids[name] = r["channel"]["id"]
                print(f"  Created #{name} ({channel_ids[name]})")
            else:
                print(f"  #{name} not found and can't create ({r.get('error', 'unknown')})")

    # Post messages
    for ch_name, msgs in MESSAGES.items():
        ch_id = channel_ids.get(ch_name)
        if not ch_id:
            print(f"  Skipping #{ch_name} — no channel ID")
            continue
        for msg in msgs:
            r = _slack("POST", "chat.postMessage", token, json={
                "channel": ch_id,
                "text": msg,
            })
            if r.get("ok"):
                print(f"  Posted message to #{ch_name}")
            time.sleep(0.5)  # Slack rate limit

    # Upload file attachments
    for ch_name, file_names in SLACK_FILE_ATTACHMENTS.items():
        ch_id = channel_ids.get(ch_name)
        if not ch_id:
            continue
        for fname in file_names:
            fpath = DRIVE_DIR / fname
            if not fpath.exists():
                print(f"  File not found: {fname}")
                continue

            content = fpath.read_bytes()
            file_size = len(content)

            # Use the newer upload URL flow
            r = _slack("GET", "files.getUploadURLExternal", token, params={
                "filename": fname,
                "length": file_size,
            })
            if not r.get("ok"):
                print(f"  Could not get upload URL for {fname}: {r.get('error')}")
                continue

            upload_url = r["upload_url"]
            file_id = r["file_id"]

            # Upload the file content
            up = httpx.post(upload_url, content=content, headers={
                "Content-Type": "application/octet-stream",
            })
            if up.status_code not in (200, 201):
                print(f"  Upload failed for {fname}: {up.status_code}")
                continue

            # Complete the upload and share to channel
            complete = _slack("POST", "files.completeUploadExternal", token, json={
                "files": [{"id": file_id, "title": fname}],
                "channel_id": ch_id,
                "initial_comment": f"Field document: {fname}",
            })
            if complete.get("ok"):
                print(f"  Uploaded {fname} to #{ch_name}")
            time.sleep(1)

    print("  Slack setup complete.")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    rt = _get_refresh_token()
    print(f"Got refresh token ({rt[:12]}...)")

    od_token = sl_token = None

    print("Exchanging for OneDrive token...")
    try:
        od_token = _exchange_token(rt, "microsoft-graph", ["Files.ReadWrite", "offline_access"])
        print(f"  OneDrive token: {od_token[:16]}...")
    except RuntimeError as e:
        print(f"  OneDrive skipped: {e}")

    print("Exchanging for Slack token...")
    try:
        sl_token = _exchange_token(rt, "sign-in-with-slack", ["channels:read", "channels:history", "chat:write", "files:write", "search:read"])
        print(f"  Slack token: {sl_token[:16]}...")
    except RuntimeError as e:
        print(f"  Slack skipped: {e}")
        print("  -> Connect Slack first: http://localhost:8000 -> Connect Slack")

    if od_token:
        setup_onedrive(od_token)
    if sl_token:
        setup_slack(sl_token)

    print("\nDone.")
