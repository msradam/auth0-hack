"""
Install the Slack bot and get bot + user tokens.

This runs a tiny local server to handle the OAuth v2 callback,
exchanges the code for tokens, and saves the bot token to .env.

Steps:
1. Adds http://localhost:9999/callback as a redirect URL to the Slack app
2. Opens the browser to Slack's OAuth v2 authorize page
3. User approves → Slack redirects to localhost:9999/callback with a code
4. Script exchanges the code for bot + user tokens
5. Saves SLACK_BOT_TOKEN to .env

Run: uv run python scripts/install_slack_bot.py
"""

import http.server
import json
import os
import ssl
import threading
import urllib.parse
import webbrowser

import httpx
from dotenv import load_dotenv

load_dotenv()

SLACK_CLIENT_ID = "10791063504227.10795392286950"
SLACK_CLIENT_SECRET = "ff1bd40be6b328d07762adab7065669c"
REDIRECT_URI = "https://localhost:9999/callback"

BOT_SCOPES = "channels:read,channels:history,chat:write"
USER_SCOPES = "channels:read,channels:history,search:read,chat:write,files:write"

_result = {}


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" not in params:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No code received")
            return

        code = params["code"][0]
        print(f"\nGot authorization code: {code[:20]}...")

        # Exchange code for tokens
        r = httpx.post("https://slack.com/api/oauth.v2.access", data={
            "client_id": SLACK_CLIENT_ID,
            "client_secret": SLACK_CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        })
        data = r.json()

        if data.get("ok"):
            _result.update(data)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Slack bot installed! You can close this tab.</h2>")
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<h2>Error: {data.get('error')}</h2><pre>{json.dumps(data, indent=2)}</pre>".encode())

        # Shutdown server after handling
        threading.Thread(target=self.server.shutdown).start()

    def log_message(self, format, *args):
        pass  # Suppress request logging


def main():
    print("First, add this redirect URL to your Slack app:")
    print(f"  {REDIRECT_URI}")
    print()
    print("Go to: https://api.slack.com/apps/A0APDBJ8ETY/oauth")
    print("Under 'Redirect URLs', click 'Add New Redirect URL', paste the URL above, click 'Save URLs'")
    print()
    input("Press Enter once you've added the redirect URL...")

    # Start local HTTPS server (self-signed cert — browser will warn, click through)
    server = http.server.HTTPServer(("localhost", 9999), CallbackHandler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain("/tmp/slack_cert.pem", "/tmp/slack_key.pem")
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()

    # Open browser to Slack OAuth
    auth_url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={SLACK_CLIENT_ID}"
        f"&scope={BOT_SCOPES}"
        f"&user_scope={USER_SCOPES}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
    )
    print(f"\nOpening browser for Slack authorization...")
    webbrowser.open(auth_url)

    # Wait for callback
    server_thread.join(timeout=120)

    if not _result:
        print("\nTimeout — no callback received.")
        return

    print("\n=== Installation successful ===")

    bot_token = _result.get("access_token", "")
    bot_refresh = _result.get("refresh_token", "")
    user_token = _result.get("authed_user", {}).get("access_token", "")
    user_refresh = _result.get("authed_user", {}).get("refresh_token", "")

    print(f"Bot token:     {bot_token[:25]}...")
    print(f"Bot refresh:   {bot_refresh[:25]}..." if bot_refresh else "Bot refresh:   (none — static token)")
    print(f"User token:    {user_token[:25]}..." if user_token else "User token:    (none)")
    print(f"Team:          {_result.get('team', {}).get('name', 'unknown')}")
    print(f"Bot user ID:   {_result.get('bot_user_id', 'unknown')}")
    print(f"Scopes:        {_result.get('scope', 'unknown')}")

    # Save bot token to .env
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    env_path = os.path.abspath(env_path)

    # Read existing .env
    if os.path.exists(env_path):
        with open(env_path) as f:
            env_content = f.read()
    else:
        env_content = ""

    # Add or update SLACK_BOT_TOKEN
    token_to_save = bot_token
    if "SLACK_BOT_TOKEN" in env_content:
        lines = env_content.splitlines()
        lines = [l if not l.startswith("SLACK_BOT_TOKEN") else f"SLACK_BOT_TOKEN={token_to_save}" for l in lines]
        env_content = "\n".join(lines) + "\n"
    else:
        env_content += f"\n# Slack Bot Token (for posting notifications)\nSLACK_BOT_TOKEN={token_to_save}\n"

    # Also save refresh token if present (for token rotation)
    if bot_refresh:
        if "SLACK_BOT_REFRESH_TOKEN" in env_content:
            lines = env_content.splitlines()
            lines = [l if not l.startswith("SLACK_BOT_REFRESH_TOKEN") else f"SLACK_BOT_REFRESH_TOKEN={bot_refresh}" for l in lines]
            env_content = "\n".join(lines) + "\n"
        else:
            env_content += f"SLACK_BOT_REFRESH_TOKEN={bot_refresh}\n"

    with open(env_path, "w") as f:
        f.write(env_content)

    print(f"\nSaved to {env_path}")
    print("Done.")


if __name__ == "__main__":
    main()
