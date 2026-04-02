# Amanat

**Your data is our amanat.** Privacy-first data governance agent for humanitarian NGOs.

Amanat scans cloud services (OneDrive, Outlook, Slack) for sensitive beneficiary data that may be overshared, improperly stored, or exposed -- then helps you fix it. All analysis runs locally via IBM Granite 4 Micro. Beneficiary data never leaves your machine.

Built for the [Auth0 "Authorized to Act" Hackathon](https://auth0.devpost.com/).

## The Problem

Humanitarian organizations handle some of the most sensitive data in the world: refugee case files, GBV incident reports, medical records of displaced persons, protection assessments. A data breach doesn't just violate privacy -- it can lead to targeting, forced return, arbitrary detention, or loss of life.

Yet field teams routinely store this data on cloud services with default sharing settings. Files containing beneficiary names, GPS coordinates, and medical conditions sit on OneDrive with "anyone with the link" access. Case numbers appear in Slack channels. The organizations that need the strongest data governance have the fewest resources to implement it.

## How It Works

1. **Authenticate** via Auth0 (supports Microsoft, Google, email/password)
2. **Connect services** individually through Auth0 Token Vault (OneDrive, Outlook, Slack, GitHub)
3. **Scan** connected services for sensitive data exposure
4. **Analyze** findings against GDPR, ICRC, IASC, and Sphere humanitarian data protection standards
5. **Remediate** -- revoke oversharing, download locally, or delete from cloud (with confirmation)

```
User: Scan my OneDrive for sensitive data
Amanat: [scans 7 files] Found GBV_Incident_Reports_2026.xlsx shared with
        "anyone with the link" -- CRITICAL risk. Contains beneficiary names,
        case IDs, GPS coordinates. Per ICRC Rule 6, data in conflict-affected
        areas requires encryption and restricted access.
User: Delete it.
Amanat: [confirms] File moved to trash. Audit report generated.
```

## Auth0 Integration

Amanat uses several Auth0 features:

### Token Vault (Connected Accounts)
The core integration. Users authenticate once via Auth0, then connect external services individually through the [Connected Accounts](https://auth0.com/docs/secure/tokens/token-vault) flow. Amanat exchanges Auth0 refresh tokens for service-specific access tokens via Token Vault's federated token exchange, so the agent can call Microsoft Graph, Slack, etc. on behalf of the user without ever seeing their raw credentials.

- Grant type: `urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token`
- My Account API with MRRT for per-service consent
- Per-service scoping (OneDrive gets `Files.ReadWrite`, Outlook gets `Mail.Read`)

### Authentication
- Auth0 Universal Login with multiple identity providers
- JWT access tokens with custom API audience
- Refresh tokens with `offline_access` scope for persistent sessions

## Architecture

```
                          Auth0
                       ┌──────────┐
                       │ Universal│
            ┌─────────►│  Login   │
            │          └────┬─────┘
            │               │ JWT + refresh token
            │          ┌────▼─────┐
            │          │  Token   │◄──── Connected Accounts flow
            │          │  Vault   │      (per-service consent)
            │          └────┬─────┘
            │               │ federated access tokens
┌───────────┴───┐      ┌───▼──────────────┐      ┌─────────────┐
│   Chainlit    │◄────►│     Amanat       │◄────►│ IBM Granite │
│   Web UI      │      │  Agent Core      │      │  4 Micro    │
│               │      │                  │      │  (local)    │
└───────────────┘      │  - Scanner       │      └─────────────┘
                       │  - Policy engine │
                       │  - Remediation   │
                       └───┬──────────────┘
                           │ Microsoft Graph / Slack / Gmail APIs
                    ┌──────┼──────┐
                    ▼      ▼      ▼
                OneDrive Outlook Slack
```

**Key design decisions:**
- **Local LLM**: IBM Granite 4 Micro runs via Ollama. Sensitive beneficiary data is analyzed entirely on the user's machine -- it never hits a cloud API.
- **Policy grounding**: The agent's responses are grounded in 20 verbatim policy documents from GDPR, ICRC Handbook, IASC Operational Guidance, and Sphere Standards using `<documents>` RAG injection.
- **Confirmation gates**: All destructive actions (revoke sharing, delete files) require explicit user confirmation.
- **Audit trail**: Every scan and remediation generates a timestamped report.

## Policy Knowledge Base

Amanat grounds its analysis in 20 real policy documents:

| Source | Documents |
|--------|-----------|
| **GDPR** | Articles 5, 6(1)(e), 9, 9(2)(c)/(h), 32, 44 |
| **ICRC Handbook** (2nd ed., 2020) | Consent validity (Ch. 3), Data security (S. 2.8), Data retention (S. 2.7) |
| **ICRC Rules** (2020) | Rules 1, 3, 6, 8; Article 23 (Data transfers) |
| **IASC Operational Guidance** (2023) | Principles 2, 5; All 12 data responsibility principles |
| **Sphere Handbook** (4th ed., 2018) | Protection Principle 1 (sensitive information) |
| **Other** | Do No Digital Harm (Privacy International/ICRC), Informed consent in humanitarian contexts |

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.ai) with `granite4:micro-h` model
- Auth0 account (free tier works)

### Install

```bash
git clone <repo-url>
cd amanat
uv sync
```

### Auth0 Configuration

1. Create an Auth0 application (Regular Web Application)
2. Add callback URL: `http://localhost:8000/auth/oauth/auth0/callback`
3. Enable a social connection (e.g., Microsoft with `microsoft-graph`)
4. Create a Custom API with audience `https://amanat.local/api`
5. Enable Token Vault:
   - Create My Account API (`https://{domain}/me/`) with `connected_accounts` scopes
   - Create a client grant with `subject_type: user`
   - Enable MRRT on the app for My Account API

### Environment

```bash
cp .env.example .env
# Fill in your Auth0 credentials:
# AUTH0_DOMAIN=your-tenant.us.auth0.com
# AUTH0_CLIENT_ID=...
# AUTH0_CLIENT_SECRET=...
# OAUTH_AUTH0_CLIENT_ID=...     (same as AUTH0_CLIENT_ID)
# OAUTH_AUTH0_CLIENT_SECRET=... (same as AUTH0_CLIENT_SECRET)
# OAUTH_AUTH0_DOMAIN=...        (same as AUTH0_DOMAIN)
# AUTH0_AUDIENCE_OVERRIDE=https://amanat.local/api
```

### Run

```bash
# Start Granite locally
ollama pull granite4:micro-h

# Start Amanat
uv run chainlit run app.py
```

Open `http://localhost:8000`. Log in via Auth0, connect your OneDrive, and start scanning.

## Demo Flow

1. Log in with Auth0 (email/password or Microsoft)
2. Click "Connect OneDrive" to link via Token Vault
3. Select **Scan** profile: "Scan all files for sensitive data"
4. Review findings with risk chart and policy citations
5. Switch to **Remediate** profile: "Delete GBV_Incident_Reports_2026"
6. Confirm deletion -- agent moves file to trash with audit report

## Project Structure

```
amanat/
  __init__.py
  agent.py          # Core agent loop, system prompt, tool definitions
  auth.py           # Auth0 Token Vault integration
  cli.py            # CLI interface (alternative to web UI)
  knowledge/
    policies.py     # 20 verbatim policy documents (GDPR, ICRC, IASC, Sphere)
  tools/
    scanner.py      # Tool execution dispatcher
    onedrive.py     # Microsoft Graph API (scan, share, delete)
    google_drive.py # Google Drive API integration
app.py              # Chainlit web UI with Auth0 OAuth + Connected Accounts
chainlit.md         # Welcome message
pyproject.toml      # Dependencies
```

## Tech Stack

- **Auth0**: Authentication, Token Vault, Connected Accounts, JWT
- **IBM Granite 4 Micro**: Local LLM for analysis (via Ollama, OpenAI-compatible API)
- **Chainlit**: Conversational UI with OAuth, tool steps, Plotly charts
- **Microsoft Graph API**: OneDrive file scanning, sharing management, deletion
- **Python**: httpx, openai, pandas, plotly, pydantic

## Name

*Amanat* (Arabic/Urdu/Bengali: trust, stewardship) -- the concept that what is entrusted to you must be protected and returned faithfully. In humanitarian work, beneficiary data is an amanat.

## License

MIT
