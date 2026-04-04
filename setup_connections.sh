#!/bin/bash
# Setup Auth0 Token Vault connections for Amanat
# Usage: ./setup_connections.sh
#
# Creates/updates Auth0 social connections with your OAuth credentials
# and enables Token Vault (Connected Accounts) on each.

set -e

DOMAIN="dev-rh7gd2vkcftbwj61.us.auth0.com"
APP_CLIENT_ID="GkiGaUlAjxZPkDmAVAgeotzKYypLdA40"

echo "=== Amanat — Auth0 Token Vault Connection Setup ==="
echo ""

# --- GitHub ---
echo "1/3 GITHUB"
echo "  Create an OAuth App at: https://github.com/settings/applications/new"
echo "  Homepage URL: https://$DOMAIN"
echo "  Callback URL: https://$DOMAIN/login/callback"
echo ""
read -p "  GitHub Client ID: " GITHUB_CLIENT_ID
read -p "  GitHub Client Secret: " GITHUB_CLIENT_SECRET

if [ -n "$GITHUB_CLIENT_ID" ]; then
  # Check if connection exists
  EXISTING=$(auth0 api get "connections?strategy=github" 2>/dev/null | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d[0]['id'] if d else '')" 2>/dev/null)

  if [ -n "$EXISTING" ]; then
    echo "  Updating existing GitHub connection ($EXISTING)..."
    auth0 api patch "connections/$EXISTING" --data "{
      \"options\": {\"client_id\": \"$GITHUB_CLIENT_ID\", \"client_secret\": \"$GITHUB_CLIENT_SECRET\"},
      \"enabled_clients\": [\"$APP_CLIENT_ID\"],
      \"connected_accounts\": {\"active\": true}
    }" > /dev/null 2>&1
  else
    echo "  Creating GitHub connection..."
    auth0 api post "connections" --data "{
      \"name\": \"github\",
      \"strategy\": \"github\",
      \"options\": {\"client_id\": \"$GITHUB_CLIENT_ID\", \"client_secret\": \"$GITHUB_CLIENT_SECRET\"},
      \"enabled_clients\": [\"$APP_CLIENT_ID\"],
      \"connected_accounts\": {\"active\": true}
    }" > /dev/null 2>&1
  fi
  echo "  ✓ GitHub connection configured with Token Vault"
else
  echo "  Skipped."
fi

echo ""

# --- Google (update existing) ---
echo "2/3 GOOGLE"
echo "  Create OAuth credentials at: https://console.cloud.google.com/apis/credentials"
echo "  Enable APIs: Drive API, Gmail API"
echo "  App type: Web application"
echo "  Authorized JS origin: https://$DOMAIN"
echo "  Authorized redirect: https://$DOMAIN/login/callback"
echo ""
read -p "  Google Client ID: " GOOGLE_CLIENT_ID
read -p "  Google Client Secret: " GOOGLE_CLIENT_SECRET

if [ -n "$GOOGLE_CLIENT_ID" ]; then
  echo "  Updating Google connection..."
  auth0 api patch "connections/con_sF0r3kyaEavASKjF" --data "{
    \"options\": {
      \"client_id\": \"$GOOGLE_CLIENT_ID\",
      \"client_secret\": \"$GOOGLE_CLIENT_SECRET\",
      \"email\": true,
      \"profile\": true,
      \"scope\": [\"email\", \"profile\", \"https://www.googleapis.com/auth/drive.readonly\", \"https://www.googleapis.com/auth/gmail.readonly\"]
    },
    \"enabled_clients\": [\"$APP_CLIENT_ID\"],
    \"connected_accounts\": {\"active\": true}
  }" > /dev/null 2>&1
  echo "  ✓ Google connection configured with Drive + Gmail scopes + Token Vault"
else
  echo "  Skipped."
fi

echo ""

# --- Slack ---
echo "3/3 SLACK"
echo "  Create a Slack App at: https://api.slack.com/apps?new_app=1"
echo "  OAuth scopes: channels:read, channels:history, users:read"
echo "  Redirect URL: https://$DOMAIN/login/callback"
echo ""
read -p "  Slack Client ID: " SLACK_CLIENT_ID
read -p "  Slack Client Secret: " SLACK_CLIENT_SECRET

if [ -n "$SLACK_CLIENT_ID" ]; then
  EXISTING=$(auth0 api get "connections?strategy=slack" 2>/dev/null | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d[0]['id'] if d else '')" 2>/dev/null)

  if [ -n "$EXISTING" ]; then
    echo "  Updating existing Slack connection ($EXISTING)..."
    auth0 api patch "connections/$EXISTING" --data "{
      \"options\": {\"client_id\": \"$SLACK_CLIENT_ID\", \"client_secret\": \"$SLACK_CLIENT_SECRET\", \"scope\": [\"channels:read\", \"channels:history\", \"users:read\"]},
      \"enabled_clients\": [\"$APP_CLIENT_ID\"],
      \"connected_accounts\": {\"active\": true}
    }" > /dev/null 2>&1
  else
    echo "  Creating Slack connection..."
    auth0 api post "connections" --data "{
      \"name\": \"sign-in-with-slack\",
      \"strategy\": \"slack\",
      \"options\": {\"client_id\": \"$SLACK_CLIENT_ID\", \"client_secret\": \"$SLACK_CLIENT_SECRET\", \"scope\": [\"channels:read\", \"channels:history\", \"users:read\"]},
      \"enabled_clients\": [\"$APP_CLIENT_ID\"],
      \"connected_accounts\": {\"active\": true}
    }" > /dev/null 2>&1
  fi
  echo "  ✓ Slack connection configured with Token Vault"
else
  echo "  Skipped."
fi

echo ""
echo "=== Done ==="
echo "All configured connections will use Token Vault for secure token exchange."
echo "Restart Chainlit and re-login to consent to the new scopes."
