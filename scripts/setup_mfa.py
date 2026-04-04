"""
Enable Guardian push notifications and set MFA policy to always-on.

Run from repo root:
    uv run python scripts/setup_mfa.py
"""

import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()

DOMAIN = os.environ["AUTH0_DOMAIN"]
CLIENT_ID = os.environ["AUTH0_CLIENT_ID"]
CLIENT_SECRET = os.environ["AUTH0_CLIENT_SECRET"]


def get_mgmt_token() -> str:
    resp = httpx.post(
        f"https://{DOMAIN}/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "audience": f"https://{DOMAIN}/api/v2/",
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def api(method: str, path: str, token: str, **kwargs):
    resp = httpx.request(
        method,
        f"https://{DOMAIN}/api/v2/{path}",
        headers={"Authorization": f"Bearer {token}"},
        **kwargs,
    )
    return resp


def main():
    print(f"Connecting to {DOMAIN}...")
    token = get_mgmt_token()
    print("Got management token.\n")

    # 1. Enable Guardian push notifications
    r = api("PUT", "guardian/factors/push-notification", token, json={"enabled": True})
    if r.status_code in (200, 201):
        print("Guardian push notifications: ENABLED")
    else:
        print(f"Guardian push: {r.status_code} {r.text}")

    # 2. Check current MFA policy
    r = api("GET", "guardian/policies", token)
    print(f"Current MFA policy: {r.json()}")

    # 3. Set MFA policy to always-on for all applications
    r = api("PUT", "guardian/policies", token, json=["all-applications"])
    if r.status_code in (200, 201):
        print(f"MFA policy set to: {r.json()}")
    else:
        print(f"MFA policy update: {r.status_code} {r.text}")

    print("\nDone. Now log into Amanat in your browser — Auth0 will prompt")
    print("for MFA enrollment and show a QR code to scan with Guardian.")


if __name__ == "__main__":
    main()
