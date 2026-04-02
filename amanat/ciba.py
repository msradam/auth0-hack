"""
CIBA (Client-Initiated Backchannel Authentication) for Amanat.

When the agent attempts a high-stakes action (deleting sensitive files,
revoking sharing on protected data), this module pauses execution and
sends an out-of-band approval request to the user via Auth0 Guardian
push notification or email.

The user sees a binding message describing exactly what the agent wants
to do. They approve or deny. Only on approval does the action proceed.

This is distinct from the in-UI confirmation dialog — CIBA is an
independent authentication event on a separate device/channel, providing
a real cryptographic authorization gate rather than just a UX gate.
"""

import asyncio
import json
import os
import time

import httpx


# High-stakes files by category — these trigger CIBA instead of simple confirm
CIBA_TRIGGERS = {
    "gbv": "GBV incident data",
    "biometric": "biometric enrollment data",
    "medical": "medical records",
    "protection": "protection-sensitive data",
}

# File name patterns that require CIBA
CIBA_FILE_PATTERNS = [
    "gbv",
    "biometric",
    "incident",
    "medical",
    "protection",
]


def requires_ciba(file_name: str, file_id: str = "") -> tuple[bool, str]:
    """
    Determine if an action on this file requires CIBA authorization.
    Returns (requires_ciba, data_category_description).
    """
    name_lower = file_name.lower()
    for pattern, description in zip(CIBA_FILE_PATTERNS, CIBA_TRIGGERS.values()):
        if pattern in name_lower:
            return True, description
    return False, ""


async def initiate_ciba(
    user_id: str,
    binding_message: str,
    domain: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    requested_expiry: int = 300,
) -> dict:
    """
    Initiate a CIBA authorization request.

    Args:
        user_id: Auth0 user ID (e.g. "auth0|abc123")
        binding_message: Human-readable message shown to the user.
                         Max 64 chars. Describes exactly what will happen.
        domain: Auth0 domain (defaults to AUTH0_DOMAIN env var)
        client_id: Auth0 client ID (defaults to AUTH0_CLIENT_ID env var)
        client_secret: Auth0 client secret (defaults to AUTH0_CLIENT_SECRET env var)
        requested_expiry: Seconds before request expires.
                          ≤300 = Guardian push notification
                          >300 = email (up to 259200 = 3 days)

    Returns:
        {"auth_req_id": "...", "expires_in": 300, "interval": 5}

    Raises:
        httpx.HTTPStatusError if the request fails
    """
    domain = domain or os.environ.get("AUTH0_DOMAIN", "")
    client_id = client_id or os.environ.get("AUTH0_CLIENT_ID", "")
    client_secret = client_secret or os.environ.get("AUTH0_CLIENT_SECRET", "")

    login_hint = json.dumps({
        "format": "iss_sub",
        "iss": f"https://{domain}/",
        "sub": user_id,
    })

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://{domain}/bc-authorize",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "login_hint": login_hint,
                "binding_message": binding_message[:64],
                "scope": "openid",
                "requested_expiry": requested_expiry,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def poll_ciba_token(
    auth_req_id: str,
    interval: int = 5,
    timeout: int = 300,
    domain: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> dict:
    """
    Poll Auth0 until the user approves or denies the CIBA request.

    Args:
        auth_req_id: The auth_req_id from initiate_ciba()
        interval: Polling interval in seconds (use the value from initiate_ciba response)
        timeout: Max seconds to wait (should match requested_expiry)

    Returns:
        Token response dict on approval

    Raises:
        PermissionError: if user denies
        TimeoutError: if request expires
        RuntimeError: on unexpected errors
    """
    domain = domain or os.environ.get("AUTH0_DOMAIN", "")
    client_id = client_id or os.environ.get("AUTH0_CLIENT_ID", "")
    client_secret = client_secret or os.environ.get("AUTH0_CLIENT_SECRET", "")

    deadline = time.time() + timeout

    async with httpx.AsyncClient() as client:
        while time.time() < deadline:
            resp = await client.post(
                f"https://{domain}/oauth/token",
                data={
                    "grant_type": "urn:openid:params:grant-type:ciba",
                    "auth_req_id": auth_req_id,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            data = resp.json()

            if "access_token" in data:
                return data

            error = data.get("error")
            if error == "authorization_pending":
                await asyncio.sleep(interval)
            elif error == "slow_down":
                retry_after = int(resp.headers.get("retry-after", interval + 5))
                await asyncio.sleep(retry_after)
            elif error == "access_denied":
                raise PermissionError("User denied the authorization request")
            elif error == "expired_token":
                raise TimeoutError("CIBA request expired before user responded")
            else:
                raise RuntimeError(
                    f"CIBA error: {error} — {data.get('error_description', 'unknown')}"
                )

    raise TimeoutError("CIBA polling timed out")


async def request_ciba_authorization(
    user_id: str,
    action_description: str,
    file_name: str,
    data_category: str,
) -> bool:
    """
    Full CIBA flow: initiate → poll → return True if approved.

    This is the high-level function called from app.py before
    executing high-stakes agent actions.

    Args:
        user_id: Auth0 user ID from the session
        action_description: e.g. "delete", "revoke sharing on"
        file_name: The file being acted on
        data_category: e.g. "GBV incident data", "biometric enrollment data"

    Returns:
        True if approved

    Raises:
        PermissionError if denied
        TimeoutError if expired
        RuntimeError on CIBA not configured
    """
    binding_message = f"Approve: {action_description} {file_name[:30]}"

    try:
        ciba_resp = await initiate_ciba(
            user_id=user_id,
            binding_message=binding_message,
            requested_expiry=300,  # 5 min — push notification
        )
    except httpx.HTTPStatusError as e:
        error_body = e.response.json() if e.response else {}
        error_code = error_body.get("error", "unknown")
        if error_code in ("unauthorized_client", "invalid_request"):
            # CIBA not configured on this tenant/app — fall back gracefully
            raise RuntimeError(
                f"CIBA not enabled on this Auth0 app (error: {error_code}). "
                "Enable CIBA grant type in your Auth0 application settings."
            )
        raise

    auth_req_id = ciba_resp["auth_req_id"]
    poll_interval = ciba_resp.get("interval", 5)
    expires_in = ciba_resp.get("expires_in", 300)

    await poll_ciba_token(
        auth_req_id=auth_req_id,
        interval=poll_interval,
        timeout=expires_in,
    )
    return True
