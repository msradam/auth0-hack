"""
Amanat - Chainlit web UI with Auth0 authentication.

Run with: chainlit run app.py
"""

import base64
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

import chainlit as cl
import plotly.graph_objects as go
from chainlit import User

from amanat.tools.scanner import execute_tool
from amanat.agent import (
    SYSTEM_PROMPT, _build_system_prompt, create_agent,
    set_access_token, REMEDIATION_TOOLS,
)
from amanat.auth import Auth0TokenVault


# Patch Auth0 OAuth provider to request JWT + refresh token for Token Vault
from chainlit.oauth_providers import Auth0OAuthProvider

_original_auth0_init = Auth0OAuthProvider.__init__
_original_auth0_get_token = Auth0OAuthProvider.get_token

def _patched_auth0_init(self):
    _original_auth0_init(self)
    self.authorize_params["audience"] = os.environ.get(
        "AUTH0_AUDIENCE_OVERRIDE", "https://amanat.local/api"
    )
    self.authorize_params["scope"] = "openid profile email offline_access"

async def _patched_auth0_get_token(self, code: str, url: str):
    """Return access_token but stash refresh_token for Token Vault."""
    json_content = await self.get_raw_token_response(code, url)
    token = json_content.get("access_token", "")
    # Stash the full response so oauth_callback can grab the refresh token
    Auth0OAuthProvider._last_token_response = json_content
    if not token:
        from starlette.exceptions import HTTPException
        raise HTTPException(status_code=400, detail="Access token missing")
    return token

Auth0OAuthProvider.__init__ = _patched_auth0_init
Auth0OAuthProvider.get_token = _patched_auth0_get_token

# CRITICAL: The providers list in chainlit.oauth_providers is populated at import
# time, so the Auth0 instance was created with the ORIGINAL __init__. We must
# replace it with a new instance that uses our patched __init__.
from chainlit.oauth_providers import providers
for i, p in enumerate(providers):
    if getattr(p, "id", None) == "auth0":
        providers[i] = Auth0OAuthProvider()
        break


# --- Audit logging (encrypted at rest) ---
AUDIT_DIR = Path("audit-logs")
AUDIT_DIR.mkdir(exist_ok=True)

# Fixed salt for deterministic key derivation from CHAINLIT_AUTH_SECRET
_AUDIT_SALT = b"amanat-audit-log-encryption-v1"


def _get_fernet() -> Fernet:
    """Derive a Fernet key from CHAINLIT_AUTH_SECRET using PBKDF2."""
    secret = os.environ.get("CHAINLIT_AUTH_SECRET", "dev-fallback-secret")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_AUDIT_SALT,
        iterations=480_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return Fernet(key)


def _audit_log(session_id: str, event: str, data: dict | None = None):
    """Append an encrypted audit event to the session log file."""
    log_file = AUDIT_DIR / f"{session_id}.jsonl.enc"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **(data or {}),
    }
    fernet = _get_fernet()
    encrypted_line = fernet.encrypt(json.dumps(entry).encode()).decode()
    with open(log_file, "a") as f:
        f.write(encrypted_line + "\n")


def decrypt_audit_log(path: str | Path) -> list[dict]:
    """Decrypt all entries in an encrypted audit log file."""
    fernet = _get_fernet()
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                plaintext = fernet.decrypt(line.encode()).decode()
                entries.append(json.loads(plaintext))
    return entries

# --- Connected Accounts routes (for Token Vault) ---
# Token Vault requires the user to link external accounts individually.
# /connect/{service} initiates the OAuth consent flow for each service.
# After consent, the callback page captures the connect_code and completes the link.

from starlette.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.routing import Route
from chainlit.server import app as chainlit_app
import httpx as _httpx
import secrets as _secrets
from amanat.auth import CONNECTIONS

DOMAIN = os.environ.get("AUTH0_DOMAIN", "")
_CLIENT_ID = os.environ.get("AUTH0_CLIENT_ID", "")
_CLIENT_SECRET = os.environ.get("AUTH0_CLIENT_SECRET", "")

# In-memory store for pending Connected Accounts sessions
_connect_sessions: dict[str, dict] = {}

# Map service names to display info
_SERVICE_DISPLAY = {
    "onedrive": {"name": "OneDrive", "icon": "📁"},
    "outlook": {"name": "Outlook", "icon": "📧"},
    "slack": {"name": "Slack", "icon": "💬"},
    "github": {"name": "GitHub", "icon": "🐙"},
}


async def connect_service(request):
    """Start Connected Accounts flow to link any service via Token Vault."""
    service = request.path_params.get("service", "")
    conn_config = CONNECTIONS.get(service)
    if not conn_config:
        return JSONResponse({"error": f"Unknown service: {service}"}, 400)

    # In DEMO_TOOLS mode, simulate the connect flow with a success page
    if DEMO_TOOLS:
        display = _SERVICE_DISPLAY.get(service, {})
        name = display.get("name", service)
        base_url = str(request.base_url).rstrip("/")
        html = f"""<!DOCTYPE html>
<html><head><style>
body {{ background: #0e1629; color: #c8d4e0; font-family: 'Noto Sans', sans-serif;
       display: flex; align-items: center; justify-content: center; height: 100vh; }}
.card {{ text-align: center; padding: 40px; }}
h2 {{ color: #14A89B; }}
a {{ color: #14A89B; text-decoration: none; font-weight: 600; }}
</style></head><body>
<div class="card">
<h2>{display.get('icon', '')} {name} Connected</h2>
<p>Service linked via Auth0 Token Vault (demo mode).</p>
<p>Scopes: <code>{', '.join(conn_config.get('scopes', []))}</code></p>
<p><a href="{base_url}">Return to Amanat</a></p>
</div></body></html>"""
        return HTMLResponse(html)

    # Read the refresh token from the last login
    try:
        with open("/tmp/amanat_tokens.txt") as f:
            content = f.read()
        rt = content.split("refresh_token: ", 1)[1].strip() if "refresh_token: " in content else ""
        if not rt or len(rt) < 10:
            return JSONResponse({"error": "No refresh token. Log in first."}, 400)
    except FileNotFoundError:
        return JSONResponse({"error": "No login tokens found. Log in first."}, 400)

    # Get My Account API token via MRRT
    async with _httpx.AsyncClient() as hc:
        resp = await hc.post(f"https://{DOMAIN}/oauth/token", data={
            "grant_type": "refresh_token",
            "client_id": _CLIENT_ID,
            "client_secret": _CLIENT_SECRET,
            "refresh_token": rt,
            "audience": f"https://{DOMAIN}/me/",
            "scope": "create:me:connected_accounts read:me:connected_accounts",
        })
        if resp.status_code != 200:
            return JSONResponse({"error": "MRRT exchange failed", "detail": resp.json()}, 400)
        my_token = resp.json()["access_token"]

        # Initiate Connected Accounts
        state = _secrets.token_urlsafe(32)
        base_url = str(request.base_url).rstrip("/")
        resp2 = await hc.post(
            f"https://{DOMAIN}/me/v1/connected-accounts/connect",
            headers={"Authorization": f"Bearer {my_token}", "Content-Type": "application/json"},
            json={
                "connection": conn_config["connection"],
                "redirect_uri": f"{base_url}/auth/connected-accounts/callback",
                "state": state,
                "scopes": conn_config["scopes"],
            },
        )
        if resp2.status_code not in (200, 201):
            return JSONResponse({"error": "Connect initiation failed", "detail": resp2.json()}, 400)

        data = resp2.json()
        _connect_sessions[state] = {
            "auth_session": data["auth_session"],
            "my_account_token": my_token,
            "redirect_uri": f"{base_url}/auth/connected-accounts/callback",
            "service": service,
        }

        ticket = data.get("connect_params", {}).get("ticket", "")
        connect_uri = data.get("connect_uri", "")
        return RedirectResponse(f"{connect_uri}?ticket={ticket}")


async def connected_accounts_callback(request):
    """
    Handle the Connected Accounts callback.
    The connect_code comes in the URL fragment (#connect_code=...) which the
    browser doesn't send to the server. So we serve a tiny HTML page with JS
    that reads the fragment and POSTs it back.
    """
    # Check if this is the completion POST (from our JS)
    # or the initial redirect (serve the HTML page)
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head><title>Connecting OneDrive...</title>
    <style>
      body { font-family: system-ui; display: flex; justify-content: center;
             align-items: center; height: 100vh; margin: 0; background: #0a0a0a; color: #e0e0e0; }
      .card { text-align: center; padding: 2rem; border-radius: 12px;
              background: #1a1a1a; border: 1px solid #333; max-width: 500px; }
      .spinner { animation: spin 1s linear infinite; font-size: 2rem; }
      @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      .success { color: #4caf50; }
      .error { color: #f44336; }
    </style>
    </head>
    <body>
    <div class="card">
      <div id="status"><span class="spinner">&#9696;</span><br><br>Linking service to Token Vault...</div>
    </div>
    <script>
    (async () => {
      const hash = window.location.hash.substring(1);
      const query = window.location.search.substring(1);
      const all = hash + '&' + query;
      const params = new URLSearchParams(all);

      const connectCode = params.get('connect_code') || params.get('code');
      const state = params.get('state');

      if (!connectCode) {
        document.getElementById('status').innerHTML =
          '<span class="error">No connect_code found in callback.</span>' +
          '<br><br>Fragment: ' + (hash || 'empty') +
          '<br>Query: ' + (query || 'empty');
        return;
      }

      try {
        const resp = await fetch('/auth/connected-accounts/complete', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ connect_code: connectCode, state: state }),
        });
        const data = await resp.json();
        if (data.success) {
          const svc = data.service || 'Service';
          document.getElementById('status').innerHTML =
            '<span class="success">&#10003; ' + svc + ' connected via Token Vault!</span>' +
            '<br><br>Return to Amanat to start scanning.' +
            '<br><br><a href="/" style="color:#90caf9;">Back to Amanat</a>';
        } else {
          document.getElementById('status').innerHTML =
            '<span class="error">Connection failed</span><br><br>' +
            JSON.stringify(data, null, 2);
        }
      } catch (e) {
        document.getElementById('status').innerHTML =
          '<span class="error">Error: ' + e.message + '</span>';
      }
    })();
    </script>
    </body>
    </html>
    """)


async def connected_accounts_complete(request):
    """Complete the Connected Accounts flow with the connect_code from JS."""
    body = await request.json()
    connect_code = body.get("connect_code", "")
    state = body.get("state", "")

    # Find the matching session
    session = None
    if state and state in _connect_sessions:
        session = _connect_sessions.pop(state)
    elif _connect_sessions:
        # Fall back to the most recent session if state doesn't match
        _, session = _connect_sessions.popitem()

    if not session:
        return JSONResponse({"success": False, "error": "No pending connect session found"})

    async with _httpx.AsyncClient() as hc:
        resp = await hc.post(
            f"https://{DOMAIN}/me/v1/connected-accounts/complete",
            headers={
                "Authorization": f"Bearer {session['my_account_token']}",
                "Content-Type": "application/json",
            },
            json={
                "auth_session": session["auth_session"],
                "connect_code": connect_code,
                "redirect_uri": session["redirect_uri"],
            },
        )

    svc_display = _SERVICE_DISPLAY.get(session.get("service", ""), {}).get("name", "Service")
    if resp.status_code in (200, 201):
        return JSONResponse({"success": True, "service": svc_display, "detail": resp.json()})
    else:
        return JSONResponse({"success": False, "service": svc_display, "error": resp.json()})

async def disconnect_service(request):
    """Revoke a connected service from the user's Token Vault session."""
    service = request.path_params.get("service", "")
    if not service:
        return JSONResponse({"error": "Missing service"}, 400)

    # Remove from the in-memory vault session
    # (Token Vault itself revokes on next exchange attempt)
    display = _SERVICE_DISPLAY.get(service, {}).get("name", service)
    return JSONResponse({
        "success": True,
        "message": f"{display} disconnected. Reconnect via /connect/{service}.",
        "service": service,
    })


# Insert custom routes at the top of the app so they resolve before Chainlit's catch-all
chainlit_app.routes.insert(0, Route("/connect/{service}", connect_service, methods=["GET"]))
chainlit_app.routes.insert(1, Route("/auth/connected-accounts/callback", connected_accounts_callback, methods=["GET"]))
chainlit_app.routes.insert(2, Route("/auth/connected-accounts/complete", connected_accounts_complete, methods=["POST"]))
chainlit_app.routes.insert(3, Route("/disconnect/{service}", disconnect_service, methods=["GET"]))

# DEMO_MODE: no Auth0 at all (local dev without credentials)
# DEMO_TOOLS: Auth0 login works, but tools use synthetic data (for deployed demo)
DEMO_MODE = not os.environ.get("OAUTH_AUTH0_CLIENT_ID")
DEMO_TOOLS = os.environ.get("DEMO_TOOLS", "").lower() in ("true", "1", "yes")

# REMEDIATION_TOOLS imported from amanat.agent


@cl.oauth_callback
async def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: dict[str, str],
    default_user: User,
    id_token: Optional[str] = None,
) -> Optional[User]:
    """Handle Auth0 OAuth callback. Store the token for Token Vault exchange."""
    default_user.metadata["auth0_token"] = token
    default_user.metadata["raw_user_data"] = raw_user_data
    # Grab refresh token stashed by our patched get_token (needed for Token Vault)
    last_resp = getattr(Auth0OAuthProvider, "_last_token_response", {})
    default_user.metadata["refresh_token"] = last_resp.get("refresh_token", "")
    # Persist refresh token for Connected Accounts routes (they run outside Chainlit session)
    rt = last_resp.get("refresh_token", "")
    if rt:
        with open("/tmp/amanat_tokens.txt", "w") as f:
            f.write(f"refresh_token: {rt}\n")
    return default_user



@cl.set_chat_profiles
async def set_chat_profiles(current_user: cl.User | None = None):
    if DEMO_TOOLS:
        # Deployed demo: starters that work with synthetic data
        return [
            cl.ChatProfile(
                name="Scan & Investigate",
                markdown_description="Scan files, messages, and emails for data protection issues.",
                icon="/public/icons/scan.svg",
                starters=[
                    cl.Starter(
                        label="Scan files for PII exposure",
                        message="Scan all files for sensitive data exposure, PII, oversharing, and policy violations.",
                        icon="/public/icons/scan.svg",
                    ),
                    cl.Starter(
                        label="Check messages for leaked data",
                        message="Search messages for any content containing beneficiary names, case numbers, or medical information in public channels.",
                        icon="/public/icons/message.svg",
                    ),
                    cl.Starter(
                        label="Check data retention compliance",
                        message="Which files have exceeded their data retention period? Flag any PII older than 12 months and special category data older than 6 months.",
                        icon="/public/icons/policy.svg",
                    ),
                    cl.Starter(
                        label="What is Amanat?",
                        message="What can you help me with?",
                        icon="/public/icons/shield.svg",
                    ),
                ],
            ),
            cl.ChatProfile(
                name="Compliance",
                markdown_description="Generate DPIAs, check consent, ask policy questions.",
                icon="/public/icons/policy.svg",
                starters=[
                    cl.Starter(
                        label="Generate a DPIA for biometric enrollment",
                        message="We're starting a biometric enrollment program that collects fingerprints and iris scans for aid distribution. Generate a DPIA for this.",
                        icon="/public/icons/policy.svg",
                    ),
                    cl.Starter(
                        label="ICRC rules on data sharing",
                        message="What does the ICRC Handbook say about sharing displaced person data with host governments? Do we need consent?",
                        icon="/public/icons/policy.svg",
                    ),
                    cl.Starter(
                        label="Check consent documentation",
                        message="Check the consent documentation status for our displaced persons registry and biometric enrollment log. Are we compliant with ICRC requirements?",
                        icon="/public/icons/policy.svg",
                    ),
                    cl.Starter(
                        label="Rules for sharing data with donors",
                        message="What are the rules for sharing displaced person data with donors like the Ambara Development Fund? What does GDPR say about this?",
                        icon="/public/icons/policy.svg",
                    ),
                ],
            ),
        ]

    # Live mode: full profiles with connect services and remediation
    return [
        cl.ChatProfile(
            name="Scan & Investigate",
            markdown_description="Scan files, messages, and emails for data protection issues.",
            icon="/public/icons/scan.svg",
            starters=[
                cl.Starter(
                    label="Connect services",
                    message="connect services",
                    icon="/public/icons/shield.svg",
                ),
                cl.Starter(
                    label="Scan OneDrive for PII exposure",
                    message="I'm worried our field team has been sharing beneficiary data too openly. Can you scan our OneDrive for any files with PII that are publicly accessible?",
                    icon="/public/icons/scan.svg",
                ),
                cl.Starter(
                    label="Check Slack for leaked data",
                    message="Search Slack for any messages containing beneficiary names, case numbers, or medical information in public channels.",
                    icon="/public/icons/message.svg",
                ),
                cl.Starter(
                    label="Check data retention",
                    message="Which of our files have exceeded their data retention period? Flag any PII older than 12 months and special category data older than 6 months.",
                    icon="/public/icons/policy.svg",
                ),
            ],
        ),
        cl.ChatProfile(
            name="Remediate",
            markdown_description="Find risks and fix them. Revoke sharing, redact PII, download locally.",
            icon="/public/icons/shield.svg",
            starters=[
                cl.Starter(
                    label="Lock down public files",
                    message="Find all publicly shared files containing PII and revoke their sharing links.",
                    icon="/public/icons/shield.svg",
                ),
                cl.Starter(
                    label="Prepare file for donor sharing",
                    message="The Ambara Development Fund is requesting our displaced persons registry for their quarterly audit. Can you check what PII is in it and redact it for safe sharing?",
                    icon="/public/icons/shield.svg",
                ),
                cl.Starter(
                    label="Alert Slack about PII leak",
                    message="Post a data protection alert to the #field-updates channel warning the team about PII we found in their messages.",
                    icon="/public/icons/message.svg",
                ),
                cl.Starter(
                    label="Download sensitive files locally",
                    message="Download all sensitive files from OneDrive to local storage so we have a backup before making changes.",
                    icon="/public/icons/message.svg",
                ),
            ],
        ),
        cl.ChatProfile(
            name="Compliance",
            markdown_description="Generate DPIAs, check consent, ask policy questions.",
            icon="/public/icons/policy.svg",
            starters=[
                cl.Starter(
                    label="Generate a DPIA for biometric enrollment",
                    message="We're starting a biometric enrollment program at Kanbaloh that collects fingerprints and iris scans for aid distribution. Generate a DPIA for this.",
                    icon="/public/icons/policy.svg",
                ),
                cl.Starter(
                    label="ICRC rules on data sharing",
                    message="What does the ICRC Handbook say about sharing displaced person data with host governments? Do we need consent?",
                    icon="/public/icons/policy.svg",
                ),
                cl.Starter(
                    label="Check consent documentation",
                    message="Check the consent documentation status for our displaced persons registry and biometric enrollment log. Are we compliant with ICRC requirements?",
                    icon="/public/icons/policy.svg",
                ),
                cl.Starter(
                    label="Rules for sharing data with donors",
                    message="What are the rules for sharing displaced person data with donors like the Ambara Development Fund? What does GDPR say about this?",
                    icon="/public/icons/policy.svg",
                ),
            ],
        ),
    ]


@cl.on_chat_start
async def on_start():
    """Set up the session and show service connection status with quick actions."""
    session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("messages", [])
    cl.user_session.set("scan_results", [])
    _audit_log(session_id, "session_start", {"demo_mode": DEMO_MODE})

    # Initialize Token Vault
    # DEMO_TOOLS: Auth0 login works but tools use synthetic data
    vault = Auth0TokenVault(demo_mode=DEMO_MODE or DEMO_TOOLS)

    user = cl.user_session.get("user")
    if user and not DEMO_MODE:
        auth0_token = user.metadata.get("auth0_token", "")
        refresh_token = user.metadata.get("refresh_token", "")
        raw = user.metadata.get("raw_user_data", {})
        vault.create_session(
            user_id=user.identifier,
            email=user.identifier,
            name=raw.get("name", user.identifier),
            auth0_token=auth0_token,
            refresh_token=refresh_token,
        )

        # Don't check Token Vault here — it creates a conversation and kills
        # the starters screen. Tokens are checked on-demand when tools need them.
        cl.user_session.set("connected_services", [])
        cl.user_session.set("not_connected", list(CONNECTIONS.keys()))
        # No message sent — starters screen shows cleanly.
    else:
        vault.create_session(user_id="demo", email="demo", name="Demo User")
        # Don't send a message — let starters show.

    cl.user_session.set("vault", vault)


# Quick-action button messages
_QUICK_ACTION_MESSAGES = {
    "full_scan": (
        "Scan my OneDrive files for data protection issues, then search Slack for "
        "leaked displaced person data, and check Outlook for sensitive emails sent externally."
    ),
    "scan_onedrive": "Scan my OneDrive files for sensitive data exposure, oversharing, and policy violations.",
    "scan_slack": (
        "Search Slack channels for messages containing displaced person names, case numbers, "
        "GPS coordinates, or medical information shared in public channels."
    ),
    "scan_outlook": (
        "Search Outlook for emails containing displaced person data that were sent to "
        "external recipients or donor partners."
    ),
    "retention": (
        "Check which files have exceeded their data retention period. Flag PII older "
        "than 12 months and special category data older than 6 months."
    ),
    "redact": (
        "I need to share the Cataclysm displaced registry (doc-001) with the Ambara Development Fund. "
        "Detect all PII and create a redacted version that's safe to share."
    ),
    "dpia": (
        "Generate a Data Protection Impact Assessment for our biometric enrollment "
        "program that collects fingerprints and iris scans for supply distribution verification."
    ),
    "consent": "Check the consent documentation status for doc-001 and doc-005. Are we compliant?",
}


@cl.action_callback("quick_action")
async def on_quick_action(action: cl.Action):
    """Handle quick-action button clicks by injecting the corresponding message."""
    action_key = action.payload.get("action", "")
    message_text = _QUICK_ACTION_MESSAGES.get(action_key, "")
    if message_text:
        msg = cl.Message(content=message_text, author="User")
        await msg.send()
        await on_message(msg)


@cl.on_message
async def on_message(message: cl.Message):
    """Handle user messages with Strands agent + Chainlit tool call visibility."""
    from strands.hooks.events import BeforeToolCallEvent, AfterToolCallEvent

    query = message.content
    session_id = cl.user_session.get("session_id", "unknown")
    profile = cl.user_session.get("chat_profile", "Scan")
    remediate_mode = profile == "Remediate"

    # Handle "connect services" command
    if query.strip().lower() in ("connect services", "connect", "connect my services"):
        if DEMO_TOOLS:
            lines = [
                "**Connect your cloud services** (demo mode):\n",
                '📁 <a href="/connect/onedrive" style="color:#14A89B;font-weight:600">Connect Microsoft</a> (OneDrive + Outlook)',
                '💬 <a href="/connect/slack" style="color:#14A89B;font-weight:600">Connect Slack</a>',
                "\nServices use synthetic humanitarian data in demo mode.",
            ]
            await cl.Message(content="\n".join(lines), author="Amanat").send()
        else:
            lines = [
                "**Connect your cloud services:**\n",
                '📁 <a href="/connect/onedrive" style="color:#14A89B;font-weight:600">Connect Microsoft</a> (OneDrive + Outlook)',
                '💬 <a href="/connect/slack" style="color:#14A89B;font-weight:600">Connect Slack</a>',
                "\nAfter connecting, start a **New Chat** to begin scanning.",
            ]
            await cl.Message(content="\n".join(lines), author="Amanat").send()
        return

    # Expand vague queries for Granite Micro
    _QUERY_EXPANSIONS = {
        "check all my files": "Scan all OneDrive files for sensitive data exposure, PII, oversharing, and policy violations.",
        "audit everything": "Scan OneDrive files for PII and sharing violations, then search Slack for leaked beneficiary data, then search Outlook for sensitive emails sent externally.",
        "is our data safe?": "Scan OneDrive for publicly shared files containing PII, then check Slack for leaked case numbers or medical data in public channels.",
        "any problems?": "Scan OneDrive for data protection issues. Check for PII in publicly shared files, oversharing violations, and retention policy breaches.",
        "what do you see?": "Scan OneDrive for all files and report any data governance issues. Check for PII exposure, sharing violations, or retention problems.",
        "scan everything": "Scan OneDrive files for PII and sharing violations, then search Slack for leaked beneficiary data, then search Outlook for sensitive emails.",
        "run a full audit": "Scan OneDrive files for PII and sharing violations, then search Slack for leaked beneficiary data, then search Outlook for sensitive emails sent externally.",
        "scan outlook": "Search Outlook emails for messages containing beneficiary names, case numbers, or medical information. Check for PII sent to external recipients.",
        "check outlook": "Search Outlook emails for messages containing beneficiary names, case numbers, or medical information. Check for PII sent to external recipients.",
        "check emails": "Search Outlook emails for messages containing beneficiary names, case numbers, or medical information. Check for PII sent to external recipients.",
        "scan slack": "Search Slack for messages containing beneficiary names, case numbers, or medical information in public channels.",
        "check slack": "Search Slack for messages containing beneficiary names, case numbers, or medical information in public channels.",
    }
    query_lower = query.strip().lower().rstrip("?!.")
    if query_lower in _QUERY_EXPANSIONS:
        query = _QUERY_EXPANSIONS[query_lower]

    _audit_log(session_id, "user_message", {"query": query, "profile": profile})

    # Get Token Vault access tokens — each service has its own token.
    # Store all available tokens so the scanner can pick the right one per service.
    vault = cl.user_session.get("vault")
    access_token = None
    _service_tokens: dict[str, str] = {}
    if vault and not vault.demo_mode:
        for svc in ("onedrive", "slack", "outlook"):
            try:
                token_info = vault.get_token(svc)
                _service_tokens[svc] = token_info.access_token
            except Exception:
                pass
        # Use OneDrive token as default (most tools need it)
        access_token = _service_tokens.get("onedrive") or _service_tokens.get("outlook")

        # If no token available, check if the query needs a service and prompt to connect
        if not access_token and not _service_tokens:
            q_lower = query.lower()
            needed = []
            if any(w in q_lower for w in ("onedrive", "file", "scan", "drive", "gbv", "biometric", "document")):
                needed.append(("Microsoft (OneDrive + Outlook)", "/connect/onedrive"))
            if any(w in q_lower for w in ("slack", "channel", "message")):
                needed.append(("Slack", "/connect/slack"))
            if any(w in q_lower for w in ("outlook", "email", "mail")):
                needed.append(("Microsoft (OneDrive + Outlook)", "/connect/onedrive"))

            if needed:
                # Deduplicate
                seen = set()
                unique = []
                for name, url in needed:
                    if name not in seen:
                        seen.add(name)
                        unique.append((name, url))

                links = "  ".join(
                    f'<a href="{url}" style="display:inline-block;padding:6px 16px;background:#14A89B;color:#fff;border-radius:6px;text-decoration:none;font-weight:600">{name}</a>'
                    for name, url in unique
                )
                await cl.Message(
                    content=f"You need to connect a service first to run this query.\n\n{links}\n\nAfter connecting, start a new chat and try again.",
                    author="Amanat",
                ).send()
                return

    # Handle file uploads (drag-and-drop PDFs for Docling parsing)
    if message.elements:
        for el in message.elements:
            if hasattr(el, "path") and el.path:
                query += f"\n\nUploaded file at: {el.path}"

    # Build system prompt with RAG documents for policy questions
    system_prompt = _build_system_prompt(query)

    # Check if provider supports tool calling
    _provider_supports_tools = "openrouter" not in os.environ.get("OPENAI_API_BASE", "")

    # If provider doesn't support tools (e.g. OpenRouter deployed demo),
    # pre-execute relevant tools and inject results into the prompt
    if not _provider_supports_tools and (DEMO_TOOLS or DEMO_MODE):
        q_lower = query.lower()
        tool_results = []
        if any(w in q_lower for w in ("scan", "onedrive", "file", "check", "gbv", "biometric", "audit")):
            tool_results.append(execute_tool("scan_files", {"service": "onedrive"}, access_token=None))
        if any(w in q_lower for w in ("slack", "channel", "message")):
            tool_results.append(execute_tool("search_messages", {"service": "slack", "query": "beneficiary OR case OR medical"}, access_token=None))
        if any(w in q_lower for w in ("outlook", "email", "mail")):
            tool_results.append(execute_tool("search_messages", {"service": "outlook", "query": "beneficiary OR case"}, access_token=None))
        if any(w in q_lower for w in ("retention", "expired", "old")):
            tool_results.append(execute_tool("retention_scan", {"service": "onedrive"}, access_token=None))
        if any(w in q_lower for w in ("dpia", "impact assessment")):
            tool_results.append(execute_tool("generate_dpia", {"activity": "humanitarian data processing", "data_types": "personal_identifier,special_category_data,biometric_data", "purpose": "beneficiary assistance"}, access_token=None))
        if any(w in q_lower for w in ("consent", "compliant")):
            tool_results.append(execute_tool("check_consent", {"file_id": "doc-001", "service": "onedrive"}, access_token=None))

        if tool_results:
            # Strip JSON, truncate, inject into prompt
            results_text = "\n\n".join(
                r.split("\n---JSON---")[0][:2000] if "---JSON---" in r else r[:2000]
                for r in tool_results
            )
            system_prompt += f"\n\nTool results from scanning the user's services:\n\n{results_text}\n\nAnalyze these results and respond to the user's query."

    # Create Strands agent
    agent = create_agent(system_prompt=system_prompt, access_token=access_token,
                         service_tokens=_service_tokens, demo_tools=DEMO_TOOLS)

    # TaskList for live progress
    task_list = cl.TaskList()
    task_list.status = "Running..."
    await task_list.send()

    # Track scan results for visualization
    all_scan_results = []
    # Track open steps so we can close them in after_tool
    _open_steps: dict[str, cl.Step] = {}

    # --- Strands hooks for Chainlit visibility ---

    # Capture the main event loop for cross-thread async calls
    import asyncio
    _main_loop = asyncio.get_event_loop()

    def _run_async(coro):
        """Run an async coroutine from Strands' sync thread."""
        future = asyncio.run_coroutine_threadsafe(coro, _main_loop)
        return future.result(timeout=130)

    def before_tool(event: BeforeToolCallEvent):
        """Show each tool call as a Chainlit step + confirmation gate."""
        tool_name = event.tool_use.get("name", "unknown")
        tool_args = event.tool_use.get("input", {})
        tool_id = event.tool_use.get("toolUseId", "")

        step_name = _friendly_step_name(tool_name, tool_args)

        # Create Chainlit step
        async def _show_step():
            step = cl.Step(name=step_name, type="tool")
            step.input = json.dumps(tool_args, indent=2)
            await step.send()
            _open_steps[tool_id] = step
            task = cl.Task(title=step_name, status=cl.TaskStatus.RUNNING)
            await task_list.add_task(task)
            await task_list.send()

        try:
            _run_async(_show_step())
        except Exception:
            pass

        # Confirmation gate: always ask before revoke/delete
        if tool_name in ("delete_file", "revoke_sharing"):
            file_id = tool_args.get("file_id", "unknown")
            action_label = tool_name.replace("_", " ")

            async def _ask():
                res = await cl.AskActionMessage(
                    content=f"**Confirm:** {action_label} `{file_id[:40]}`?",
                    actions=[
                        cl.Action(name="confirm", payload={"value": "yes"}, label="Approve"),
                        cl.Action(name="cancel", payload={"value": "no"}, label="Deny"),
                    ],
                    timeout=120,
                ).send()
                return res and res.get("payload", {}).get("value") == "yes"

            try:
                approved = _run_async(_ask())
            except Exception:
                approved = True

            if not approved:
                _audit_log(session_id, "remediation_denied", {"tool": tool_name, "file_id": file_id})
                event.tool_use["input"] = {}
                return

            _audit_log(session_id, "remediation_approved", {"tool": tool_name, "file_id": file_id})

            # Download before delete
            if tool_name == "delete_file" and access_token:
                for fid in file_id.split(","):
                    fid = fid.strip()
                    if fid:
                        service = tool_args.get("service", "onedrive")
                        execute_tool("download_file", {"file_id": fid, "service": service},
                                     access_token=access_token)

        _audit_log(session_id, "tool_call_start", {
            "tool": tool_name, "args": tool_args,
        })

    def after_tool(event: AfterToolCallEvent):
        """Close Chainlit step, extract scan results for charts."""
        tool_name = event.tool_use.get("name", "unknown")
        tool_id = event.tool_use.get("toolUseId", "")
        result = event.result

        # Extract text from result
        result_text = ""
        if isinstance(result, dict):
            content = result.get("content", [])
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    result_text += block["text"]

        # Track scan results for visualization
        if tool_name == "scan_files" and "---JSON---" in result_text:
            try:
                json_part = result_text.split("---JSON---", 1)[1].strip()
                result_data = json.loads(json_part)
                if "results" in result_data:
                    all_scan_results.extend(result_data["results"])
            except (json.JSONDecodeError, IndexError):
                pass

        # Close Chainlit step
        async def _close_step():
            step = _open_steps.pop(tool_id, None)
            if step:
                step.output = _summarize_result(tool_name, result_text)
                await step.update()
            if task_list.tasks:
                task_list.tasks[-1].status = cl.TaskStatus.DONE
                await task_list.send()

        try:
            _run_async(_close_step())
        except Exception:
            pass

        _audit_log(session_id, "tool_call_end", {
            "tool": tool_name,
            "result_len": len(result_text),
            "result_preview": result_text[:300],
        })

    # Register hooks
    agent.hooks.add_callback(BeforeToolCallEvent, before_tool)
    agent.hooks.add_callback(AfterToolCallEvent, after_tool)

    # Run agent (Strands agent is synchronous, wrap for async Chainlit)
    try:
        result = await cl.make_async(lambda: agent(query))()

        # Extract final answer
        final_content = "Analysis complete."
        msg = result.message
        if msg:
            if isinstance(msg, str):
                final_content = msg
            elif isinstance(msg, dict) and msg.get("content"):
                content = msg["content"]
                if isinstance(content, str):
                    final_content = content
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and "text" in block:
                            final_content = block["text"]
                            break
                        elif isinstance(block, str):
                            final_content = block
                            break

    except Exception as e:
        final_content = f"Error: {e}"
        print(f"[Amanat] Error: {e}")
        import traceback
        traceback.print_exc()

    # Mark task list done
    task_list.status = "Done"
    await task_list.send()

    # Build final message with visualizations
    elements = []
    if all_scan_results:
        chart = _build_risk_chart(all_scan_results)
        if chart:
            elements.append(chart)
        df_el = _build_results_table(all_scan_results)
        if df_el:
            elements.append(df_el)

    _audit_log(session_id, "agent_response", {
        "response": final_content[:2000],
        "scan_results_count": len(all_scan_results),
    })

    # Build action buttons for risky files
    actions = []
    risky = [f for f in all_scan_results
             if f.get("risk_level") == "critical"
             and f.get("sharing") in ("anyone_with_link", "org_wide")]
    if not remediate_mode:
        for f in risky[:5]:
            actions.append(cl.Action(
                name="suggest_remediate",
                payload={"file_id": f["file_id"], "name": f["name"]},
                label=f"Fix: {f['name'][:30]}",
            ))
    else:
        for f in risky[:5]:
            actions.extend([
                cl.Action(
                    name="action_revoke",
                    payload={"file_id": f["file_id"], "name": f["name"]},
                    label=f"Revoke: {f['name'][:25]}",
                ),
                cl.Action(
                    name="action_download",
                    payload={"file_id": f["file_id"], "name": f["name"]},
                    label=f"Download: {f['name'][:25]}",
                ),
            ])

    await cl.Message(
        content=final_content,
        author="Amanat",
        elements=elements,
        actions=actions,
    ).send()

    cl.user_session.set("scan_results", all_scan_results)


# --- Action callbacks ---

@cl.action_callback("connect_service_action")
async def on_connect_service(action: cl.Action):
    """Handle connect service button click — redirect to Token Vault OAuth flow."""
    service = action.payload["service"]
    display = _SERVICE_DISPLAY.get(service, {})
    name = display.get("name", service)
    await cl.Message(
        content=f"{display.get('icon', '•')} Opening **{name}** connection flow... [Click here if not redirected](/connect/{service})",
        author="Amanat",
    ).send()


@cl.action_callback("disconnect_service")
async def on_disconnect(action: cl.Action):
    """Handle disconnect service button click."""
    service = action.payload["service"]
    display = _SERVICE_DISPLAY.get(service, {})
    name = display.get("name", service)

    vault = cl.user_session.get("vault")
    if vault:
        vault.revoke_service(service)

    await cl.Message(
        content=f"{display.get('icon', '•')} **{name}** disconnected. [Reconnect](/connect/{service})",
        author="Amanat",
    ).send()


@cl.action_callback("action_revoke")
async def on_revoke(action: cl.Action):
    """Handle revoke sharing button click."""
    file_id = action.payload["file_id"]
    name = action.payload["name"]

    res = await cl.AskActionMessage(
        content=f"**Confirm:** Revoke all public/link sharing on **{name}**?",
        actions=[
            cl.Action(name="confirm", payload={"value": "yes"}, label="Yes, revoke"),
            cl.Action(name="cancel", payload={"value": "no"}, label="Cancel"),
        ],
        timeout=120,
    ).send()

    if not res or res.get("payload", {}).get("value") != "yes":
        await cl.Message(content=f"Cancelled revoking sharing on {name}.", author="Amanat").send()
        return

    vault = cl.user_session.get("vault")
    access_token = None
    if vault and not vault.demo_mode:
        try:
            token_info = vault.get_token("onedrive")
            access_token = token_info.access_token
        except Exception:
            pass

    async with cl.Step(name=f"Revoking sharing on {name}", type="tool") as step:
        result = execute_tool("revoke_sharing", {"file_id": file_id, "service": "onedrive"}, access_token=access_token)
        step.output = result

    try:
        data = json.loads(result)
        msg = data.get("message", result)
    except json.JSONDecodeError:
        msg = result

    await cl.Message(content=f"**{name}**: {msg}", author="Amanat").send()


@cl.action_callback("action_download")
async def on_download(action: cl.Action):
    """Handle download file button click."""
    file_id = action.payload["file_id"]
    name = action.payload["name"]

    vault = cl.user_session.get("vault")
    access_token = None
    if vault and not vault.demo_mode:
        try:
            token_info = vault.get_token("onedrive")
            access_token = token_info.access_token
        except Exception:
            pass

    async with cl.Step(name=f"Downloading {name}", type="tool") as step:
        result = execute_tool("download_file", {"file_id": file_id, "service": "onedrive"}, access_token=access_token)
        step.output = result

    try:
        data = json.loads(result)
        msg = data.get("message", result)
    except json.JSONDecodeError:
        msg = result

    await cl.Message(content=f"**{name}**: {msg}", author="Amanat").send()


@cl.action_callback("suggest_remediate")
async def on_suggest_remediate(action: cl.Action):
    """Nudge user to switch to Remediate profile."""
    name = action.payload["name"]
    await cl.Message(
        content=f"To fix **{name}**, start a new chat in **Remediate** mode (use the profile switcher at the top).",
        author="Amanat",
    ).send()


# --- Session cleanup ---

@cl.on_chat_end
async def on_end():
    """Clear sensitive data from the session when the chat ends."""
    cl.user_session.set("scan_results", [])
    cl.user_session.set("messages", [])
    vault = cl.user_session.get("vault")
    if vault:
        vault._session = None


# --- Visualization helpers ---

def _build_risk_chart(scan_results: list[dict]) -> cl.Plotly | None:
    """Build a Plotly risk summary chart from scan results."""
    if not scan_results:
        return None

    names = [r.get("name", "?")[:25] for r in scan_results]
    risk_levels = [r.get("risk_level", "info") for r in scan_results]
    sharing = [r.get("sharing", "unknown").replace("_", " ") for r in scan_results]

    # Color by risk
    colors = []
    for r in risk_levels:
        if r == "critical":
            colors.append("#ef4444")
        elif r == "warning":
            colors.append("#eab308")
        else:
            colors.append("#22c55e")

    # Risk score for bar height
    risk_score = {"critical": 3, "warning": 2, "info": 1}
    scores = [risk_score.get(r, 0) for r in risk_levels]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=names,
        y=scores,
        marker_color=colors,
        text=[f"{r}<br>{s}" for r, s in zip(risk_levels, sharing)],
        textposition="auto",
        hovertemplate="<b>%{x}</b><br>Risk: %{text}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Risk Summary", font=dict(size=16)),
        yaxis=dict(
            tickvals=[1, 2, 3],
            ticktext=["Info", "Warning", "Critical"],
            title="Risk Level",
        ),
        xaxis=dict(title="", tickangle=-30),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e8edf2"),
        height=350,
        margin=dict(b=100, t=50),
        showlegend=False,
    )

    return cl.Plotly(name="risk_summary", figure=fig, display="inline", size="large")


def _build_results_table(scan_results: list[dict]) -> cl.Dataframe | None:
    """Build a dataframe element from scan results."""
    if not scan_results:
        return None

    import pandas as pd

    rows = []
    for r in scan_results:
        rows.append({
            "File": r.get("name", "?"),
            "Risk": r.get("risk_level", "?").upper(),
            "Sharing": r.get("sharing", "?").replace("_", " "),
            "PII": "Yes" if r.get("pii_detected") else "No",
            "Categories": ", ".join(r.get("pii_categories", [])),
            "Owner": r.get("owner", "?"),
        })

    df = pd.DataFrame(rows)
    return cl.Dataframe(name="scan_results", data=df, display="inline", size="large")


# --- Tool display helpers ---

def _friendly_step_name(fn_name: str, args: dict) -> str:
    """Human-readable step names for the UI."""
    labels = {
        "scan_files": f"Scanning {args.get('service', 'files')}",
        "check_sharing": f"Checking sharing on {args.get('file_id', 'file')}",
        "detect_pii": f"Detecting PII in {args.get('file_id', 'file')}",
        "search_messages": f"Searching {args.get('service', 'messages')} for \"{args.get('query', '')}\"",
        "revoke_sharing": f"Revoking public sharing on {args.get('file_id', 'file')}",
        "download_file": f"Downloading {args.get('file_id', 'file')} locally",
        "delete_file": f"Deleting {args.get('file_id', 'file')} from cloud",
        "redact_file": f"Redacting PII from {args.get('file_id', 'file')}",
        "retention_scan": f"Scanning for retention violations",
        "generate_dpia": f"Generating DPIA for {args.get('activity', 'activity')[:40]}",
        "check_consent": f"Checking consent for {args.get('file_id', 'file')}",
    }
    return labels.get(fn_name, fn_name)


def _summarize_result(fn_name: str, result: str) -> str:
    """Create a concise summary of tool results for the step display."""
    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        return result[:500]

    if fn_name == "scan_files":
        total = data.get("files_scanned", 0)
        with_pii = data.get("files_with_pii", 0)
        files = data.get("results", [])
        lines = [f"Scanned **{total}** files, **{with_pii}** contain PII\n"]
        for f in files:
            risk = f.get("risk_level", "unknown")
            icon = {"critical": "\U0001f534", "warning": "\U0001f7e1", "info": "\U0001f7e2"}.get(risk, "\u26aa")
            sharing = f.get("sharing", "unknown").replace("_", " ")
            lines.append(f"{icon} **{f['name']}** — {risk} risk, shared: {sharing}")
        return "\n".join(lines)

    elif fn_name == "check_sharing":
        scope = data.get("sharing_scope", "unknown").replace("_", " ")
        risk = data.get("sharing_risk", "unknown")
        issue = data.get("issue", "No issues detected")
        return f"**Sharing:** {scope} ({risk} risk)\n\n{issue}"

    elif fn_name == "detect_pii":
        findings = data.get("pii_findings", [])
        if not findings:
            return "No PII detected"
        lines = [f"Found **{len(findings)}** types of sensitive data:\n"]
        for f in findings:
            lines.append(f"- **{f['type']}**: {f['count']} instances ({f['severity']})")
        return "\n".join(lines)

    elif fn_name == "search_messages":
        msgs = data.get("results", [])
        if not msgs:
            return "No sensitive messages found"
        lines = [f"Found **{len(msgs)}** messages with sensitive content:\n"]
        for m in msgs:
            channel = m.get("channel", m.get("subject", "unknown"))
            pii = ", ".join(m.get("pii_types", []))
            lines.append(f"- **{channel}**: {pii}")
        return "\n".join(lines)

    elif fn_name in ("revoke_sharing", "download_file", "delete_file"):
        status = data.get("status", "unknown")
        message = data.get("message", "")
        icon = "\u2705" if status == "success" else "\u274c"
        return f"{icon} {message}"

    return json.dumps(data, indent=2)[:500]
