"""
Live integration tests — hit real APIs via Auth0 Token Vault.

Requires:
  - Auth0 tenant configured with Connected Accounts
  - A valid refresh token in /tmp/amanat_tokens.txt (from a Chainlit login)
  - Connected services (Slack, OneDrive, Outlook) linked via the app

Run:  uv run python tests/test_live_integrations.py [service]
  service: slack, onedrive, outlook, all (default: all)
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

import httpx
from amanat.auth import Auth0TokenVault, CONNECTIONS


def get_refresh_token() -> str:
    """Read the refresh token from the token file."""
    try:
        with open("/tmp/amanat_tokens.txt") as f:
            content = f.read()
        rt = content.split("refresh_token: ", 1)[1].strip()
        if len(rt) < 10:
            raise ValueError("Token too short")
        return rt
    except (FileNotFoundError, IndexError, ValueError) as e:
        print(f"ERROR: No valid refresh token found: {e}")
        print("Log in via the Chainlit app first, then retry.")
        sys.exit(1)


def exchange_token(service: str, refresh_token: str) -> str:
    """Exchange refresh token for a service-specific access token via Token Vault."""
    domain = os.environ["AUTH0_DOMAIN"]
    client_id = os.environ["AUTH0_CLIENT_ID"]
    client_secret = os.environ["AUTH0_CLIENT_SECRET"]

    conn_config = CONNECTIONS[service]

    resp = httpx.post(f"https://{domain}/oauth/token", data={
        "grant_type": "urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token",
        "client_id": client_id,
        "client_secret": client_secret,
        "subject_token": refresh_token,
        "subject_token_type": "urn:ietf:params:oauth:token-type:refresh_token",
        "requested_token_type": "http://auth0.com/oauth/token-type/federated-connection-access-token",
        "connection": conn_config["connection"],
        "scope": " ".join(conn_config["scopes"]) if conn_config["scopes"] else "",
    })

    if resp.status_code != 200:
        error = resp.json()
        print(f"  Token exchange FAILED: {error.get('error_description', error.get('error', resp.text))}")
        return ""

    data = resp.json()
    token = data["access_token"]
    print(f"  Token exchanged OK (scope: {data.get('scope', 'n/a')}, expires: {data.get('expires_in', '?')}s)")
    return token


def test_slack(token: str):
    """Test Slack API calls."""
    print("\n--- Slack: conversations.list ---")
    resp = httpx.get("https://slack.com/api/conversations.list", params={
        "types": "public_channel", "limit": "5",
    }, headers={"Authorization": f"Bearer {token}"})
    data = resp.json()
    if not data.get("ok"):
        print(f"  FAIL: {data.get('error', data)}")
        return
    channels = data.get("channels", [])
    print(f"  Found {len(channels)} public channels:")
    for ch in channels[:5]:
        print(f"    #{ch['name']} ({ch['num_members']} members, shared={ch.get('is_ext_shared', False)})")

    print("\n--- Slack: search.messages ---")
    resp2 = httpx.get("https://slack.com/api/search.messages", params={
        "query": "displaced", "count": "5",
    }, headers={"Authorization": f"Bearer {token}"})
    data2 = resp2.json()
    if not data2.get("ok"):
        print(f"  FAIL: {data2.get('error', data2)}")
        print("  (search:read scope may not be granted)")
        return
    msgs = data2.get("messages", {}).get("matches", [])
    print(f"  Search 'beneficiary': {len(msgs)} results")
    for m in msgs[:3]:
        print(f"    [{m.get('channel', {}).get('name', '?')}] {m.get('text', '')[:80]}")

    # Test our integration module
    print("\n--- Slack: Amanat scan_slack_channels ---")
    from amanat.tools.slack import scan_slack_channels
    result = scan_slack_channels(token)
    text = result.split("\n---JSON---")[0]
    print(f"  {text[:500]}")


def test_onedrive(token: str):
    """Test OneDrive API calls."""
    print("\n--- OneDrive: list files ---")
    resp = httpx.get("https://graph.microsoft.com/v1.0/me/drive/root/children", params={
        "$select": "id,name,file,size,lastModifiedDateTime",
        "$top": "5",
    }, headers={"Authorization": f"Bearer {token}"})

    if resp.status_code != 200:
        print(f"  FAIL: {resp.status_code} {resp.text[:200]}")
        return

    items = resp.json().get("value", [])
    print(f"  Found {len(items)} items:")
    for item in items[:5]:
        kind = "file" if "file" in item else "folder"
        print(f"    {kind}: {item['name']} ({item.get('size', 0)} bytes)")

    # Test our integration module
    print("\n--- OneDrive: Amanat scan ---")
    from amanat.tools.onedrive import scan_onedrive
    result = scan_onedrive(token)
    try:
        data = json.loads(result)
        print(f"  Scanned {data.get('files_scanned', 0)} files, {data.get('files_with_pii', 0)} with PII")
    except json.JSONDecodeError:
        print(f"  {result[:300]}")


def test_outlook(token: str):
    """Test Outlook/Mail API calls."""
    print("\n--- Outlook: recent messages ---")
    resp = httpx.get("https://graph.microsoft.com/v1.0/me/messages", params={
        "$select": "id,subject,from,toRecipients,receivedDateTime,bodyPreview",
        "$top": "5",
        "$orderby": "receivedDateTime desc",
    }, headers={"Authorization": f"Bearer {token}"})

    if resp.status_code != 200:
        print(f"  FAIL: {resp.status_code} {resp.text[:200]}")
        return

    msgs = resp.json().get("value", [])
    print(f"  Found {len(msgs)} recent emails:")
    for m in msgs[:5]:
        sender = m.get("from", {}).get("emailAddress", {}).get("address", "?")
        print(f"    From: {sender} | {m.get('subject', '(no subject)')[:60]}")

    # Test our integration module
    print("\n--- Outlook: Amanat search ---")
    from amanat.tools.outlook import search_outlook_messages
    result = search_outlook_messages(token, "displaced")
    text = result.split("\n---JSON---")[0]
    print(f"  {text[:500]}")


TESTS = {
    "slack": ("sign-in-with-slack", test_slack),
    "onedrive": ("microsoft-graph", test_onedrive),
    "outlook": ("microsoft-graph", test_outlook),
}


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    services = list(TESTS.keys()) if target == "all" else [target]

    refresh_token = get_refresh_token()
    print(f"Refresh token: {refresh_token[:10]}...{refresh_token[-5:]}")

    results = []
    for service in services:
        if service not in TESTS:
            print(f"Unknown service: {service}")
            continue

        connection_name, test_fn = TESTS[service]
        print(f"\n{'='*60}")
        print(f"TESTING: {service.upper()}")
        print(f"{'='*60}")

        print(f"\n--- Token Vault exchange ({connection_name}) ---")
        token = exchange_token(service, refresh_token)

        if not token:
            print(f"  SKIP: No token (service may not be connected)")
            results.append((service, "NO TOKEN"))
            continue

        try:
            test_fn(token)
            results.append((service, "PASS"))
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append((service, f"FAIL: {e}"))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for service, status in results:
        print(f"  [{status}] {service}")


if __name__ == "__main__":
    main()
