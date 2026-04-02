"""
Amanat - Chainlit web UI with Auth0 authentication.

Run with: chainlit run app.py
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import chainlit as cl
import plotly.graph_objects as go
from chainlit import User
from openai import OpenAI

from amanat.knowledge.policies import get_documents_for_prompt, search_policies
from amanat.tools.scanner import execute_tool
from amanat.tools.bee_tools import get_openai_tools_schema
from amanat.agent import SYSTEM_PROMPT, AGENT_ROLE, AGENT_INSTRUCTIONS, _get_extra_instructions
from amanat.auth import Auth0TokenVault

# Build OpenAI-format tool list from BeeAI tool definitions
TOOLS = get_openai_tools_schema()


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


MODEL = "granite4-micro"
client = OpenAI(base_url="http://localhost:8080/v1", api_key="llama")

# --- Audit logging ---
AUDIT_DIR = Path("audit-logs")
AUDIT_DIR.mkdir(exist_ok=True)


def _audit_log(session_id: str, event: str, data: dict | None = None):
    """Append a timestamped audit event to the session log file."""
    log_file = AUDIT_DIR / f"{session_id}.jsonl"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **(data or {}),
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

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

# Insert custom routes at the top of the app so they resolve before Chainlit's catch-all
chainlit_app.routes.insert(0, Route("/connect/{service}", connect_service, methods=["GET"]))
chainlit_app.routes.insert(1, Route("/auth/connected-accounts/callback", connected_accounts_callback, methods=["GET"]))
chainlit_app.routes.insert(2, Route("/auth/connected-accounts/complete", connected_accounts_complete, methods=["POST"]))

# Use demo mode when no Auth0 OAuth env vars are set
DEMO_MODE = not os.environ.get("OAUTH_AUTH0_CLIENT_ID")

# Tools that require user confirmation before execution
REMEDIATION_TOOLS = {"revoke_sharing", "download_file", "delete_file"}


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
    return [
        cl.ChatProfile(
            name="Scan & Investigate",
            markdown_description="**Read-only audit.** Scan files, messages, and emails for data protection issues.",
            icon="/public/icons/scan.svg",
            starters=[
                cl.Starter(
                    label="Full data governance scan",
                    message="Scan my OneDrive files for data protection issues, then check Slack for leaked displaced person data, and scan Outlook for sensitive emails sent to external recipients.",
                    icon="/public/icons/scan.svg",
                ),
                cl.Starter(
                    label="Scan Slack for PII leaks",
                    message="Search Slack channels for messages containing displaced person names, case numbers, GPS coordinates, or medical information shared in public channels.",
                    icon="/public/icons/message.svg",
                ),
                cl.Starter(
                    label="Scan emails for external PII",
                    message="Search Outlook for emails containing displaced person data that were sent to external recipients or donor partners.",
                    icon="/public/icons/message.svg",
                ),
                cl.Starter(
                    label="Check data retention compliance",
                    message="Which files have exceeded their data retention period? Check for PII older than 12 months and special category data older than 6 months.",
                    icon="/public/icons/policy.svg",
                ),
            ],
        ),
        cl.ChatProfile(
            name="Remediate",
            markdown_description="**Scan + act.** Detect risks then fix them — revoke sharing, redact PII, download locally.",
            icon="/public/icons/shield.svg",
            starters=[
                cl.Starter(
                    label="Full scan and remediation",
                    message="Scan all files for sensitive data, then help me fix any issues you find — revoke oversharing, redact PII from files, and download critical data locally.",
                    icon="/public/icons/scan.svg",
                ),
                cl.Starter(
                    label="Lock down public files",
                    message="Find all publicly shared files containing PII and revoke their public links immediately.",
                    icon="/public/icons/shield.svg",
                ),
                cl.Starter(
                    label="Redact file for safe sharing",
                    message="I need to share the Upheaval displaced registry (doc-001) with the Hateno Development Fund. Redact all PII first so it's safe to share.",
                    icon="/public/icons/shield.svg",
                ),
                cl.Starter(
                    label="Evacuate sensitive data",
                    message="Download all sensitive files locally and remove them from OneDrive.",
                    icon="/public/icons/message.svg",
                ),
            ],
        ),
        cl.ChatProfile(
            name="Compliance",
            markdown_description="**Policy & compliance.** Generate DPIAs, check consent, ask policy questions.",
            icon="/public/icons/policy.svg",
            starters=[
                cl.Starter(
                    label="Generate a DPIA",
                    message="Generate a Data Protection Impact Assessment for our biometric enrollment program that collects fingerprints and iris scans for supply distribution verification at Lookout Landing.",
                    icon="/public/icons/policy.svg",
                ),
                cl.Starter(
                    label="Check consent documentation",
                    message="Check the consent status for our displaced persons registry (doc-001) and biometric enrollment log (doc-005). Are we compliant?",
                    icon="/public/icons/policy.svg",
                ),
                cl.Starter(
                    label="GDPR compliance assessment",
                    message="Are we GDPR and ICRC Handbook compliant in how we store and share displaced person case files? What needs to change?",
                    icon="/public/icons/policy.svg",
                ),
                cl.Starter(
                    label="Data sharing with donors",
                    message="What are the rules for sharing displaced person data with donors like the Hateno Development Fund? How do we share program data without exposing PII?",
                    icon="/public/icons/scan.svg",
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
    vault = Auth0TokenVault(demo_mode=DEMO_MODE)

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

        # Check which services are connected via Token Vault
        connected = []
        not_connected = []
        for service, config in CONNECTIONS.items():
            try:
                vault.exchange_token(service)
                display = _SERVICE_DISPLAY.get(service, {})
                connected.append(f"{display.get('icon', '•')} **{display.get('name', service)}** — connected")
            except Exception:
                display = _SERVICE_DISPLAY.get(service, {})
                not_connected.append(service)

        # Build status message
        consent = vault.get_consent_summary()
        status_lines = [f"Authenticated as **{consent['user']}** ({consent['email']})"]
        status_lines.append("")

        if connected:
            status_lines.append("**Connected services:**")
            status_lines.extend(connected)

        if not_connected:
            status_lines.append("")
            status_lines.append("**Available to connect:**")
            for svc in not_connected:
                display = _SERVICE_DISPLAY.get(svc, {})
                status_lines.append(
                    f"{display.get('icon', '•')} {display.get('name', svc)} — "
                    f"[Connect {display.get('name', svc)}](/connect/{svc})"
                )

        status_lines.append("")
        status_lines.append("All analysis runs locally via IBM Granite 4 Micro. Your data never leaves this machine.")

        await cl.Message(
            content="\n".join(status_lines),
            author="Amanat",
        ).send()
    else:
        vault.create_session(user_id="demo", email="demo", name="Demo User")

        # In demo mode, show quick-action buttons
        actions = [
            cl.Action(name="quick_action", payload={"action": "full_scan"}, label="Scan All Services"),
            cl.Action(name="quick_action", payload={"action": "scan_onedrive"}, label="Scan OneDrive"),
            cl.Action(name="quick_action", payload={"action": "scan_slack"}, label="Scan Slack"),
            cl.Action(name="quick_action", payload={"action": "scan_outlook"}, label="Scan Outlook"),
            cl.Action(name="quick_action", payload={"action": "retention"}, label="Retention Check"),
            cl.Action(name="quick_action", payload={"action": "redact"}, label="Redact for Sharing"),
            cl.Action(name="quick_action", payload={"action": "dpia"}, label="Generate DPIA"),
            cl.Action(name="quick_action", payload={"action": "consent"}, label="Check Consent"),
        ]

        await cl.Message(
            content=(
                "**Amanat** — data governance for humanitarian organizations.\n\n"
                "Choose a quick action below, or type anything to chat freely."
            ),
            author="Amanat",
            actions=actions,
        ).send()

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
        "I need to share the Upheaval displaced registry (doc-001) with the Hateno Development Fund. "
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
    """Handle user messages — run the agent loop with visible tool steps."""
    query = message.content
    session_id = cl.user_session.get("session_id", "unknown")
    profile = cl.user_session.get("chat_profile", "Scan")
    remediate_mode = profile == "Remediate"
    _audit_log(session_id, "user_message", {"query": query, "profile": profile})

    # All tools always available — confirmation prompts gate destructive actions
    active_tools = TOOLS

    # Build system prompt — inject policy documents only for policy questions,
    # not scan queries (keeps prompt short for Granite Micro)
    extra = _get_extra_instructions(query)
    system_prompt = SYSTEM_PROMPT
    if extra:
        system_prompt = system_prompt + "\n\n" + "\n".join(extra)

    # Get conversation history
    history = cl.user_session.get("messages", [])

    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": query},
    ]

    # TaskList for live progress
    task_list = cl.TaskList()
    task_list.status = "Running..."
    await task_list.send()

    # Track all scan results for final visualization
    all_scan_results = []

    # Agent loop
    for iteration in range(10):
        try:
            print(f"[Amanat] LLM call #{iteration}, {len(messages)} messages")
            response = await cl.make_async(lambda: client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=active_tools,
                tool_choice="auto",
                temperature=0,
                max_tokens=2048,
            ))()
        except Exception as e:
            print(f"[Amanat] LLM ERROR: {e}")
            await cl.Message(content=f"Error calling LLM: {e}", author="Amanat").send()
            task_list.status = "Error"
            await task_list.send()
            return

        msg = response.choices[0].message
        print(f"[Amanat] LLM response: finish={response.choices[0].finish_reason}, "
              f"tool_calls={len(msg.tool_calls) if msg.tool_calls else 0}, "
              f"content={msg.content[:100] if msg.content else '(none)'}")

        # No tool calls — final response
        if not msg.tool_calls:
            # Mark task list done
            task_list.status = "Done"
            await task_list.send()

            # Build final message elements
            elements = []

            # Generate risk chart if we have scan results
            if all_scan_results:
                chart = _build_risk_chart(all_scan_results)
                if chart:
                    elements.append(chart)

                df_el = _build_results_table(all_scan_results)
                if df_el:
                    elements.append(df_el)

            final_content = msg.content or "Analysis complete."
            _audit_log(session_id, "agent_response", {
                "response": final_content[:2000],
                "scan_results_count": len(all_scan_results),
            })

            # In Scan mode, offer remediation actions on risky files
            actions = []
            if not remediate_mode:
                risky = [f for f in all_scan_results
                         if f.get("risk_level") == "critical"
                         and f.get("sharing") in ("anyone_with_link", "org_wide")]
                for f in risky[:5]:
                    actions.append(cl.Action(
                        name="suggest_remediate",
                        payload={"file_id": f["file_id"], "name": f["name"]},
                        label=f"Fix: {f['name'][:30]}",
                        description=f"Switch to Remediate mode to fix {f['name']}",
                    ))

            # In Remediate mode, attach action buttons for risky files
            if remediate_mode:
                risky = [f for f in all_scan_results
                         if f.get("risk_level") == "critical"
                         and f.get("sharing") in ("anyone_with_link", "org_wide")]
                for f in risky[:5]:
                    actions.extend([
                        cl.Action(
                            name="action_revoke",
                            payload={"file_id": f["file_id"], "name": f["name"]},
                            label=f"Revoke: {f['name'][:25]}",
                            description=f"Revoke public sharing on {f['name']}",
                        ),
                        cl.Action(
                            name="action_download",
                            payload={"file_id": f["file_id"], "name": f["name"]},
                            label=f"Download: {f['name'][:25]}",
                            description=f"Download {f['name']} locally",
                        ),
                    ])

            final = cl.Message(
                content=final_content,
                author="Amanat",
                elements=elements,
                actions=actions,
            )
            await final.send()

            # Save full conversation (including tool calls) to history
            # so follow-up messages like "go ahead and delete" have context
            new_messages = [m for m in messages[1:] if m not in history]  # skip system prompt
            history.extend(new_messages)
            cl.user_session.set("messages", history[-30:])
            cl.user_session.set("scan_results", all_scan_results)
            return

        # Process tool calls with visible steps + task list
        messages.append(msg.model_dump())

        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            try:
                fn_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            # Get Token Vault access token for live API calls
            vault = cl.user_session.get("vault")
            access_token = None
            if vault and not vault.demo_mode:
                service = fn_args.get("service", "")
                # Map service names to Token Vault connection names
                token_service = {
                    "onedrive": "onedrive",
                    "slack": "slack",
                    "outlook": "outlook",
                    "gmail": "outlook",  # Gmail queries route to Outlook/Graph
                }.get(service)
                if token_service:
                    try:
                        token_info = vault.get_token(token_service)
                        access_token = token_info.access_token
                        print(f"[Amanat] Token for {token_service}: OK ({access_token[:10]}...)")
                    except Exception as e:
                        print(f"[Amanat] Token for {token_service}: FAILED ({e})")
                        pass

            # Confirmation for destructive actions
            if fn_name in REMEDIATION_TOOLS:
                file_id = fn_args.get("file_id", "unknown")
                action_label = {
                    "revoke_sharing": "revoke public sharing on",
                    "download_file": "download",
                    "delete_file": "move to trash",
                }.get(fn_name, fn_name)

                file_name = fn_args.get("name", file_id)
                res = await cl.AskActionMessage(
                    content=f"**Confirm:** {action_label} `{file_name}`?",
                    actions=[
                        cl.Action(name="confirm", payload={"value": "yes"}, label="Yes, proceed"),
                        cl.Action(name="cancel", payload={"value": "no"}, label="Cancel"),
                    ],
                    timeout=120,
                ).send()

                if not res or res.get("payload", {}).get("value") != "yes":
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({"status": "cancelled", "message": "User cancelled this action."}),
                    })
                    continue

            # Add task to task list
            step_name = _friendly_step_name(fn_name, fn_args)
            task = cl.Task(title=step_name, status=cl.TaskStatus.RUNNING)
            await task_list.add_task(task)
            await task_list.send()

            # Show tool call as a collapsible step
            async with cl.Step(name=step_name, type="tool") as step:
                step.input = json.dumps(fn_args, indent=2)
                print(f"[Amanat] Executing {fn_name}({fn_args}) live={access_token is not None}")
                result = execute_tool(fn_name, fn_args, access_token=access_token)
                print(f"[Amanat] Result: {len(result)} chars")
                step.output = _summarize_result(fn_name, result)
                _audit_log(session_id, "tool_call", {
                    "tool": fn_name, "args": fn_args,
                    "live": access_token is not None,
                    "result_len": len(result),
                    "result_text": result.split("\n---JSON---")[0][:500],
                })

            # Track scan results for visualization (parse JSON from tool output)
            if fn_name == "scan_files" and "---JSON---" in result:
                try:
                    json_part = result.split("---JSON---", 1)[1].strip()
                    result_data = json.loads(json_part)
                    if "results" in result_data:
                        all_scan_results.extend(result_data["results"])
                except (json.JSONDecodeError, IndexError):
                    pass

            # Mark task done
            task.status = cl.TaskStatus.DONE
            await task_list.send()

            # Send only the text portion to the LLM (strip JSON to keep context small)
            llm_content = result.split("\n---JSON---")[0] if "---JSON---" in result else result
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": llm_content,
            })

    task_list.status = "Done"
    await task_list.send()
    await cl.Message(content="Reached maximum analysis depth.", author="Amanat").send()


# --- Action callbacks ---

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
