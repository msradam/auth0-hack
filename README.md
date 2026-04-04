# Amanat — Humanitarian Data Governance Agent

**Your data is our amanat.** A privacy-first AI agent that helps humanitarian NGOs find and fix sensitive data exposure across cloud services.

Built for the [Auth0 "Authorized to Act" Hackathon](https://auth0.devpost.com/).

---

## The Problem

Humanitarian organizations handle some of the most sensitive data in the world: refugee case files, GBV incident reports, medical records of displaced persons. A data breach doesn't just violate privacy — it can lead to targeting, forced return, or arbitrary detention.

Yet field teams routinely store this data on cloud services with default sharing settings. Files containing beneficiary names, GPS coordinates, and medical conditions sit on OneDrive with "anyone with the link" access. Case numbers appear in Slack channels. The organizations that need the strongest data governance have the fewest resources to implement it.

## How It Works

1. **Authenticate** via Auth0 Universal Login
2. **Connect services** via Auth0 Token Vault (OneDrive, Outlook, Slack) — one OAuth flow per service, all tokens managed by Auth0
3. **Scan** — the agent calls Microsoft Graph, Slack API, and runs deterministic regex PII detection on file content
4. **Analyze** — findings are compared against GDPR, ICRC Handbook, IASC, and Sphere Standards
5. **Remediate** — revoke oversharing, redact PII, delete files; destructive actions on high-sensitivity files trigger an in-UI confirmation dialog

```
User: Scan my OneDrive for sensitive data

Amanat: [scans 7 files] Found GBV_Incident_Reports_2026.csv shared with
        "anyone with the link" — CRITICAL risk. Contains beneficiary names,
        case IDs, GPS coordinates. Per ICRC Rule 6, data in conflict-affected
        areas requires encryption and restricted access. Want me to revoke
        sharing?

User: Yes, revoke it.

Amanat: ⚠️ This file contains GBV data. Confirm remediation?
        [Approve] [Deny]
        ✓ Confirmed. Sharing revoked. Audit entry written.
```

## Auth0 Features Used

### Token Vault (Connected Accounts)
The core integration. Users authenticate once via Auth0, then connect each external service through a [Connected Accounts](https://auth0.com/docs/secure/tokens/token-vault) OAuth flow. Amanat exchanges Auth0 refresh tokens for service-specific access tokens via federated token exchange — the agent calls Microsoft Graph and Slack APIs on behalf of the user without ever storing raw service credentials.

- Grant type: `urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token`
- My Account API with MRRT for per-service consent
- Per-service scoping (`Files.ReadWrite` for OneDrive, `Mail.Read` for Outlook, `search:read` for Slack)
- Token expiry detection with automatic re-exchange

### Remediation Confirmation
Destructive actions on sensitive files (GBV reports, biometric data) trigger an in-UI confirmation dialog. The agent pauses and waits for explicit user approval before proceeding. Pattern-matched: any file matching `gbv`, `biometric`, `incident`, `medical`, `protection`. MFA via Auth0 Guardian protects the login session itself.

### Auth0 Universal Login + JWT
Standard Auth0 web app login with refresh tokens and `offline_access` scope for persistent sessions.

## Architecture

```
                         Auth0
                      ┌──────────────────────────┐
                       │  Universal Login          │
            ┌─────────►│  Token Vault              │
            │          └────────────┬─────────────┘
            │                       │ federated access tokens
┌───────────┴───┐      ┌───────────▼──────────────┐      ┌─────────────────┐
│   Chainlit    │◄────►│        Amanat             │◄────►│  IBM Granite 4  │
│   Web UI      │      │                           │      │  Micro (local)  │
│               │      │  Strands Agents SDK       │      │  llama-server   │
│  • Chat       │      │  auth.py  — Token Vault   │      │  port 8080      │
│  • Steps      │      │  agent.py — Strands agent │      └─────────────────┘
│  • Charts     │      │  tools/   — scan/remediate│
└───────────────┘      └──────────┬────────────────┘
                                  │ Microsoft Graph / Slack / Outlook APIs
                           ┌──────┼──────┐
                           ▼      ▼      ▼
                       OneDrive Outlook Slack
```

**Key design decisions:**

- **Local LLM only**: IBM Granite 4 Micro runs via llama-server (llama.cpp). Beneficiary data is analyzed entirely on the user's machine — it never reaches a cloud LLM API.
- **Hybrid PII detection**: Two-layer approach inspired by the RECAP paper (2025). Regex catches structural patterns (phone, email, case IDs, GPS). Granite 4 Micro catches contextual/multilingual PII (names in any script, implicit identifiers like "the 15-year-old in Vakwa Shelter").
- **Policy grounding**: BM25 retrieval over 1,059 chunks extracted from actual ICRC Handbook, IASC Guidance, GDPR, and Sphere Handbook PDFs. Granite answers policy questions using the native `<documents>` RAG format.
- **Docling document parsing**: Real-world documents (PDF, DOCX, PPTX, XLSX) can be uploaded and scanned via IBM's Docling library. The granite-docling-258M VLM pipeline provides enhanced table/OCR extraction.
- **Audit trail**: Every scan and remediation writes a timestamped JSONL entry to `audit-logs/{session_id}.jsonl`.

## Demo Scenario

The demo uses a fictional humanitarian scenario: **Post-Cataclysm Waqwaq**. The **Waqwaq Relief Authority (WRA)** is responding to a displacement crisis caused by "the Cataclysm" — Kanbaloh hosts an IDP hub, Sofala Village is being reconstructed, a Vakwa Shelter serves evacuees. Waqwaq is a legendary archipelago from medieval Arabic geographical literature, referenced by al-Idrisi and other cartographers.

This follows established practice in humanitarian training: DHIS2 uses fictional countries for training data, Sphere exercises use invented scenarios, and the CDC used zombie apocalypse scenarios for emergency preparedness education. The fictional setting lets us demonstrate real data governance patterns (GBV files, biometric enrollment logs, protection assessments) without using real-world sensitive data.

Demo files in `demo-data/drive/`:
- `Cataclysm_Displaced_Registry_2026.csv` — 15 beneficiaries, names/case IDs/medical history
- `GBV_Incident_Reports_2026.csv` — shared publicly, CRITICAL risk
- `Biometric_Enrollment_Log.csv` — fingerprint/iris scan records, special category data
- `Field_Team_Contacts.csv` — staff PII
- `Donor_Report_Q1_2026.txt` — donor communications

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- [llama.cpp](https://github.com/ggerganov/llama.cpp) with a Granite 4 Micro GGUF model
- Auth0 account (free tier works)

### Install

```bash
git clone https://github.com/msradam/auth0-hack
cd auth0-hack
uv sync
```

### Start the LLM

Download a Granite 4 Micro GGUF (e.g. from Hugging Face) and start llama-server:

```bash
llama-server \
  --model /path/to/granite-4-micro.gguf \
  --port 8080 \
  --ctx-size 8192
```

The app expects an OpenAI-compatible API at `http://localhost:8080/v1`.

### Auth0 Configuration

1. Create an Auth0 **Regular Web Application**
2. Add callback URL: `http://localhost:8000/auth/oauth/auth0/callback`
3. Enable social connections with Token Vault:
   - Microsoft (for OneDrive + Outlook) — needs `microsoft-graph` connection
   - Slack — needs a Slack app with `channels:read`, `channels:history`, `search:read` (user token)
4. Create a **Custom API** with audience `https://amanat.local/api`
5. Enable **Token Vault**:
   - Create My Account API (`https://{domain}/me/`) with `read:connected_accounts` and `create:connected_account_tokens` scopes
   - Create a client grant with `subject_type: user`
   - Enable MRRT on the app for My Account API
### Environment

```bash
cp .env.example .env
```

Fill in `.env`:

```bash
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret

OAUTH_AUTH0_CLIENT_ID=your-client-id        # same as above
OAUTH_AUTH0_CLIENT_SECRET=your-client-secret
OAUTH_AUTH0_DOMAIN=your-tenant.us.auth0.com

AUTH0_AUDIENCE_OVERRIDE=https://amanat.local/api

OPENAI_API_BASE=http://localhost:8080/v1
OPENAI_API_KEY=llama

CHAINLIT_AUTH_SECRET=your-random-secret     # generate with: openssl rand -hex 32
```

### Run

```bash
uv run chainlit run app.py
```

Open `http://localhost:8000`. Log in via Auth0, connect OneDrive, and start scanning.

## Demo Flow

1. Log in with Auth0 (email/password or Microsoft OAuth)
2. Click **Connect OneDrive** → completes Token Vault Connected Accounts flow
3. Ask: *"Scan all files for sensitive data"*
4. Review findings — risk chart, PII types, policy citations
5. Ask: *"Revoke sharing on the GBV file"*
6. Confirmation dialog appears → approve → sharing revoked
7. Audit log written to `audit-logs/`

## Project Structure

```
amanat/
  agent.py           # System prompt, Strands agent, tool definitions
  auth.py            # Auth0 Token Vault — token exchange, expiry, revocation
  cli.py             # CLI interface
  knowledge/
    policies.py      # Policy documents + BM25 RAG over 1,059 PDF-extracted chunks
    rules.py         # Governance rules engine
    policy_chunks.json  # Preprocessed ICRC/IASC/GDPR/Sphere text chunks
  tools/
    scanner.py       # Tool dispatcher + hybrid PII detection (regex + LLM)
    docling_tool.py  # Docling document parsing (PDF/DOCX/PPTX/XLSX)
    onedrive.py      # Microsoft Graph API (scan, share, revoke, redact, delete)
    slack.py         # Slack API (search, scan channels, post alerts)
    outlook.py       # Outlook / Graph Mail API (search, send alerts)
app.py               # Chainlit web UI — OAuth, Strands hooks, confirmation gate, audit logging
demo-data/           # Waqwaq scenario demo files
tests/               # Unit tests
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Auth | Auth0 Universal Login, Token Vault |
| LLM | IBM Granite 4 Micro (llama-server, local) |
| Agent framework | Strands Agents SDK |
| Document parsing | IBM Docling (granite-docling-258M VLM) |
| Web UI | Chainlit |
| APIs | Microsoft Graph, Slack Web API |
| Language | Python 3.13, httpx, pydantic, pandas, plotly |

## The Name

*Amanat* (Arabic/Urdu/Bengali: trust, stewardship) — the concept that what is entrusted to you must be protected and returned faithfully. In humanitarian work, beneficiary data is an amanat.

## License

MIT
