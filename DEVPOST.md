# Amanat: Privacy-First Data Governance Agent for Humanitarian NGOs

Author: Adam Munawar Rahman, April 2026

Amanat connects to your OneDrive, Slack, and Outlook through Auth0 Token Vault, scans for sensitive beneficiary data that's been overshared or exposed, and helps fix it. Token Vault handles multi-service credential management so the agent acts across all three without storing raw tokens. IBM Granite 4 Micro runs the analysis locally, so beneficiary data never leaves the device. For organizations handling refugee case files and GBV reports, you need both of those things or the tool is unusable.

*Amanat* (Arabic: trust, stewardship), the concept that what is entrusted to you must be protected and returned faithfully.

---

## Demo Video

The 3-minute demo video shows Amanat running locally against my personal Microsoft 365 and Slack accounts, connected via Auth0 Token Vault. The OneDrive folders, Outlook inbox, and Slack workspace shown in the video are real accounts populated with synthetic humanitarian data from the Waqwaq scenario. All scans, remediations, CIBA step-up auth, and alerts execute live against the Microsoft Graph and Slack APIs. The video is sped up in places to fit the 3-minute window.

## Screenshots

**Slack scan: PII detected across public channels, alerts posted automatically**

![Slack scan finds beneficiary names, case numbers, GPS coordinates, and medical data in three public channels. Alerts posted to each channel. File attachment scanned and flagged.](https://raw.githubusercontent.com/msradam/amanat/main/assets/screenshots/03_slack_scan_summary.png)

**Redaction: 47 PII instances removed, clean copy uploaded to OneDrive**

![Agent redacts all PII from the displaced persons registry and uploads REDACTED_Cataclysm_Displaced_Registry_2026.csv to the same OneDrive folder. Original file untouched. Slack notification sent.](https://raw.githubusercontent.com/msradam/amanat/main/assets/screenshots/05_redaction_result.png)

**Policy RAG: ICRC Handbook cited on biometric data retention**

![Agent retrieves ICRC rules on special-category data retention, determines the biometric enrollment log violates the 6-month retention window, recommends deletion.](https://raw.githubusercontent.com/msradam/amanat/main/assets/screenshots/08_policy_rag_icrc.png)

**CIBA step-up auth: Guardian push notification for destructive actions**

![Agent sends Guardian push via CIBA before revoking sharing. Shows auth_req_id, binding message, and CIBA token on approval.](https://raw.githubusercontent.com/msradam/amanat/main/assets/screenshots/ciba1.png)

## Published App

The published app at https://msradam-amanat.hf.space uses IBM watsonx.ai to host the same Granite 4 model that runs locally via llama-server in the video demo. watsonx is used here for deployment convenience (GPU inference without self-hosting), but the architecture is identical: Strands agent with tool calling, same system prompt, same 14 tools. Auth0 login works. Tools return synthetic demo data (the full experience requires the user's own OneDrive, Slack, and Outlook connected via Token Vault). All synthetic data is [open and auditable in the repo](https://github.com/msradam/amanat/tree/main/demo-data/drive). To run locally against live services, clone the repo and follow the setup instructions in the README.

## Auth0 Features Used

| Feature | How Amanat Uses It |
|---------|-------------------|
| **Universal Login** | Single sign-on with Guardian MFA push notifications |
| **Token Vault (Connected Accounts)** | Federated token exchange for OneDrive, Slack, Outlook. Per-service scoping. MRRT across My Account API and all providers |
| **CIBA (Backchannel Authentication)** | Guardian push to user's phone before revoking sharing or deleting files. `POST /bc-authorize` with binding message. Agent polls until approved |
| **Guardian MFA** | Push notifications for both login MFA and CIBA step-up auth on destructive actions |

---

## Inspiration

In 2021, UNHCR collected biometric data (fingerprints and iris scans) from 830,000 Rohingya refugees in Bangladesh. The refugees were told registration was required to receive food. What they weren't told was that their data would be shared with the Myanmar government, the very regime they had fled. Some discovered their names on Myanmar's repatriation lists. Biometric data is immutable. Once shared, it can never be taken back (Human Rights Watch, 2021).

Nobody hacked UNHCR. The data was shared through internal processes, on shared drives, with default settings that nobody reviewed. A governance failure.

UNHCR's own data protection policy requires telling people, in a language they understand, why their data is being collected and whether it will be transferred. Of 24 refugees HRW interviewed, all but one said they were never informed of potential data sharing with Myanmar. UNHCR never carried out a data impact assessment, breaching its own rules (HRW, 2021).

This keeps happening. In 2016, the UN's Office of Internal Oversight Services found that three of five UNHCR missions they investigated had shared refugees' personal data with host governments without assessing data protection or establishing transfer agreements (OIOS, 2016). In January 2022, attackers exploited an unpatched vulnerability to access personal data of 515,000 people in the ICRC's Restoring Family Links programme, which helps people separated from families by conflict, migration, and disaster. The attackers were inside for 70 days before anyone noticed. The programme had to be shut down entirely (ICRC, 2022).

Humanitarian organizations handle refugee case files, GBV incident reports, biometric enrollment logs, medical records of displaced persons. And field teams routinely store this data on cloud services with default sharing settings. A GBV report shared with "anyone with the link." Case numbers posted in public Slack channels. Beneficiary names and HIV status in a donor report email.

> "The Data of the Most Vulnerable People is the Least Protected" — Human Rights Watch, 2023

The ICRC published a 400-page Handbook on Data Protection in Humanitarian Action. The IASC published Operational Guidance on Data Responsibility (2023). The Sphere Standards include Protection Principles for sensitive information handling. The policy documents exist. Nobody has built software that enforces them.

The tools humanitarian organizations actually use (KoBoToolbox for data collection, DHIS2 for health data, Microsoft 365 for everything else) have baseline security (encryption in transit, optional encryption at rest, basic RBAC) but no automated data classification, no sensitivity detection, no cross-platform governance, no policy enforcement. A CyberPeace Institute study found that 41% of NGOs had been attacked in the past three years, only 4% had actionable cybersecurity policies, and 56% had no cybersecurity budget at all (CyberPeace, 2024). A Dalberg/ICRC joint study found fewer than half of humanitarian organizations had data protection policies meeting international standards (ICRC Handbook, 2020).

I built Amanat to fill that gap.

## What It Does

You log in through Auth0, connect your OneDrive, Slack, and Outlook via Token Vault, and tell the agent what to look for. It scans your files, messages, and emails for PII, checks what's publicly shared, cites the relevant ICRC or GDPR section, and can revoke sharing links or redact files on the spot.

### Why These Three Services

UNHCR deployed Microsoft 365 across its field operations, making OneDrive and Outlook the default file storage and email for the world's largest refugee agency. WFP, UNICEF, and dozens of implementing partners followed. Slack (and increasingly Teams) became the coordination layer. The NetHope consortium, which provides IT infrastructure for 60+ major international NGOs, has documented the shift to cloud messaging platforms across the sector. Sensitive data flows across all three every day, and nothing watches the gap between them. Amanat connects to all three via Token Vault because that's where the data actually is.

### Capabilities

| Capability | Description |
|-----------|-------------|
| **Multi-service scanning** | Recursively crawls OneDrive folders, searches Slack messages and file attachments, scans Outlook emails |
| **Hybrid PII detection** | Two-layer approach: deterministic regex for structural patterns + Granite 4 Micro for contextual/multilingual extraction |
| **Policy grounding** | RAG pipeline with BM25 retrieval over 1,059 chunks extracted from actual ICRC Handbook, IASC Guidance, GDPR, and Sphere Handbook PDFs |
| **Remediation** | Revoke sharing links, redact PII for safe sharing, download before delete, generate DPIAs, check consent documentation |
| **CIBA step-up auth** | Destructive actions trigger a Guardian push notification via CIBA; user approves on their phone before the agent proceeds. Falls back to in-UI dialog if Guardian unavailable |
| **Document parsing** | Upload scanned PDFs/DOCX/XLSX; Docling with granite-docling-258M VLM extracts text via OCR, then scans for PII |
| **Slack alerting** | Posts data protection warnings to channels where PII leaks are detected |
| **Encrypted audit trail** | Every scan and remediation action logged, encrypted at rest with Fernet/PBKDF2 |

### Tools

14 functions the agent can call:

| Tool | Purpose | Example Query |
|------|---------|---------------|
| `scan_files` | Scan OneDrive files for PII and sharing violations | "Scan my files for sensitive data" |
| `search_messages` | Search Slack/Outlook for PII in messages | "Search Slack for case numbers" |
| `detect_pii` | Deep PII scan on a specific file | "What PII is in the displaced registry?" |
| `check_sharing` | Check who has access to a file | "Who can see the GBV reports?" |
| `revoke_sharing` | Remove public/link-based sharing | "Lock down the biometric files" |
| `redact_file` | Redact PII and upload clean copy to OneDrive | "Redact the registry and upload the safe version" |
| `download_file` | Download to local storage | "Download the GBV reports locally" |
| `delete_file` | Move to trash (with pre-delete download) | "Remove the biometric data from cloud" |
| `retention_scan` | Check for retention policy violations | "Which files have exceeded retention?" |
| `generate_dpia` | Generate Data Protection Impact Assessment | "DPIA for our biometric enrollment" |
| `check_consent` | Verify consent documentation | "Is our consent compliant?" |
| `notify_channel` | Post data protection alert to Slack | "Warn the team about the PII leak" |
| `send_email` | Send data protection alert email | "Email the sender about the violation" |
| `parse_document` | OCR and scan uploaded documents | *Drag-and-drop a scanned PDF* |

### Demo Scenario

The demo uses a fictional humanitarian scenario: Post-Cataclysm Waqwaq. The Waqwaq Relief Authority (WRA) responds to a displacement crisis on a fictional archipelago. The setting is fictional but the data governance patterns are real. All synthetic demo data is committed to the GitHub repo at [`demo-data/drive/`](https://github.com/msradam/amanat/tree/main/demo-data/drive), organized into the same folder structure used on OneDrive.

Demo files across OneDrive (`/WRA Operations/`):

| Folder | Files | Violations |
|--------|-------|------------|
| `/Beneficiary Records/` | Cataclysm_Displaced_Registry_2026.csv | PII: names, case IDs, medical history, GPS |
| `/Protection/` | GBV_Incident_Reports_2026.csv, GBV scanned PDF | **PUBLIC sharing — CRITICAL** |
| `/Biometric Data/` | Enrollment log, consent form, verification log | **PUBLIC sharing — CRITICAL**; special category data |
| `/Field Operations/` | Staff contacts, site register | Staff PII |
| `/Donor Relations/` | Donor report | Cross-references beneficiary case IDs |
| `/Scanned Documents/` | Registration form (image-only PDF) | Requires Docling OCR to extract PII |

## How I Built It

Full technical breakdown in [ARCHITECTURE.md](https://github.com/msradam/amanat/blob/main/ARCHITECTURE.md). Key sections below.

### Auth0 Integration

#### Token Vault (Connected Accounts)

The user authenticates once via Auth0 Universal Login, then connects each service separately through Connected Accounts. Each connection is its own OAuth consent screen, so the user sees exactly which permissions they're granting, and can disconnect any service without affecting the others. Amanat exchanges Auth0 refresh tokens for service-specific access tokens via federated token exchange:

```
POST /oauth/token
grant_type=urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token
subject_token={refresh_token}
subject_token_type=urn:ietf:params:oauth:token-type:refresh_token
requested_token_type=http://auth0.com/oauth/token-type/federated-connection-access-token
connection=microsoft-graph
```

The agent calls Microsoft Graph and Slack APIs on behalf of the user without ever storing raw service credentials. Token expiry is tracked via `TokenInfo.is_expired()` with a 60-second buffer, triggering automatic re-exchange. A single Multi-Resource Refresh Token (MRRT) works across both the My Account API and all connected services, so one refresh token handles service discovery and token exchange for every provider.

Per-service scoping:

| Service | Connection | Scopes |
|---------|-----------|--------|
| OneDrive + Outlook | `microsoft-graph` | `Files.Read`, `Files.ReadWrite`, `Mail.Read`, `Mail.Send`, `offline_access` |
| Slack (read) | `sign-in-with-slack` | `channels:read`, `channels:history`, `search:read` |
| Slack (write) | Bot token | `chat:write` (separate credential, posts as "Amanat") |

I chose Refresh Token Exchange over Privileged Worker Exchange deliberately: Amanat always acts with the user present in the chat session, never async. The user watches each tool call happen, sees the results, and approves destructive actions in real time. A Privileged Worker flow (where the backend acts without a user session) would be appropriate for scheduled compliance scans, but for an interactive agent handling GBV files, I wanted the human in the loop at all times.

#### Remediation Confirmation (CIBA)

Any call to `revoke_sharing` or `delete_file` triggers a step-up authentication via CIBA (Client-Initiated Backchannel Authentication). The agent sends a Guardian push notification to the user's phone with a binding message describing the specific action (e.g. "Amanat: revoke sharing GBV_Incident_Reports"). The agent pauses and polls until the user approves or denies on their phone. If CIBA is unavailable (user not enrolled in Guardian), it falls back to an in-UI Approve/Deny dialog. Without this, a chatbot could delete a GBV file because someone typed "yes" in the conversation. The user has to explicitly confirm the specific action on a separate device. MFA via Auth0 Guardian protects both the login session and individual destructive actions.

### Hybrid PII Detection (RECAP-Inspired)

PII detection follows the two-layer hybrid architecture described in "An Evaluation Study of Hybrid Methods for Multilingual PII Detection" (2025). The study found hybrid approaches outperform fine-tuned NER by 82% and zero-shot LLMs by 17% in weighted F1-score.

```
Layer 1: Regex (deterministic)     → structural PII: phone numbers, emails,
                                     case IDs (WAQ-26CNNNNN), GPS coordinates,
                                     medical terms, ethnic identifiers
                                     Fast, zero false negatives on known patterns.

Layer 2: Granite 4 Micro (LLM)    → contextual PII: names in any script,
                                     implicit identifiers ("the 15-year-old
                                     in Vakwa Shelter"), age+location combos
                                     that identify specific individuals.
                                     Catches what regex cannot.
```

Results on test data:

| Method | PII Types Found | Time |
|--------|----------------|------|
| Regex only | 6 (name, phone, email, case ID, medical, GPS) | 0.00s |
| Hybrid (regex + LLM) | 9 (+location_identifier, age_identifier, implicit_id) | 8.32s |

The LLM layer caught "15-year-old girl in Vakwa Shelter Section 2" as an implicit identifier: age + gender + specific shelter location identifies a person without naming them. Regex cannot express this.

### Policy RAG Pipeline

Policy grounding uses real documents, not paraphrases:

1. **Source PDFs** (17.3 MB): ICRC Handbook on Data Protection in Humanitarian Action, IASC Operational Guidance on Data Responsibility (2023), GDPR Full Text (Regulation EU 2016/679), Sphere Handbook (4th ed., 2018)

2. **Preprocessing**: IBM Docling parses PDFs into structured markdown, splits by section headings, filters for data-protection-relevant content → 1,059 chunks, 1.1M chars

3. **Retrieval**: BM25 ranking over chunk text.

4. **Injection**: Top 5 chunks formatted in Granite 4's native `<documents>` RAG format. The query "Can we share biometric data with host governments?" retrieves ICRC Handbook Chapter 4.2, 8.2.1, and 8.2.4, the same sections a data protection officer would consult.

### IBM Granite 4 Micro

Granite 4.0 Micro is a 3B-parameter dense transformer model released under Apache 2.0 (IBM, 2025). It is the first open-source LLM family to achieve ISO 42001 certification, the international standard for AI management systems covering accountability, explainability, and data privacy. Key properties for this use case:

- **Apache 2.0 license**: no licensing barriers for humanitarian organizations, no usage restrictions, no royalties. Any NGO can deploy it freely.
- **Small footprint**: 3B parameters run in ~4GB RAM via llama.cpp quantization. Deployable on a laptop in a field office. No GPU, no cloud, no internet required.
- **Native function calling** with structured JSON output via Strands Agents SDK.
- **Multilingual**: English, Arabic, French, Spanish, Japanese, Korean, Chinese, and 5 other languages.
- **128K context window**, sufficient for large policy documents and scan results.
- **Published training data sources** and cryptographically signed model checkpoints.

This matters because ICRC data protection rules (Articles 23-24) impose strict conditions on transferring personal data to third-party processors. Any recipient must contractually prove adequacy and purpose limitation. Sending beneficiary data to a commercial LLM API (OpenAI, Anthropic, Google) creates a third-party processing relationship that is difficult to justify under ICRC rules. A local model eliminates the question entirely: the data never leaves the device.

### IBM Docling + granite-docling-258M

Docling (MIT license, hosted by LF AI & Data Foundation) and its companion model granite-docling-258M (Apache 2.0) handle document parsing. Field documents are often scanned: printed intake forms, hand-filled registration sheets, faxed protection assessments. These arrive as image-only PDFs with no embedded text layer.

For image-only PDFs, the granite-docling-258M VLM pipeline provides OCR with table structure recognition. When the OneDrive scanner downloads a PDF/DOCX/XLSX, it routes through Docling for text extraction before PII detection.

### Security Hardening

| Control | Implementation |
|---------|---------------|
| Local LLM | Granite 4 Micro via llama-server. No cloud API calls. Beneficiary data stays on-machine. |
| PII redaction | `redact_pii_in_text()` replaces PII with category labels during file redaction and Slack scanning. Tool results truncated to 4000 chars before agent context. |
| Encrypted audit logs | Fernet symmetric encryption, key derived via PBKDF2 (SHA256, 480K iterations) from `CHAINLIT_AUTH_SECRET` |
| Token isolation | Auth0 Token Vault manages service credentials. Amanat never stores raw OAuth tokens. |
| Download before delete | Every `delete_file` action automatically downloads a local copy first |
| Session wipe | Scan results, conversation history, and Token Vault session cleared on chat end |
| Credential separation | Slack reading uses user token (via Token Vault); Slack writing uses bot token (separate credential) |
| CIBA step-up auth | `revoke_sharing` and `delete_file` trigger Guardian push via CIBA (`POST /bc-authorize`). User approves on phone. Falls back to in-UI dialog |

### Agent Architecture

**Runtime pipeline:**

User Query → Chainlit Web UI → Strands Agent (Granite 4 Micro, local) → Tool Selection → API Calls via Token Vault → Result + Charts

**Components:**

| Layer | Component | Role |
|-------|-----------|------|
| **UI** | Chainlit | OAuth login, chat, tool steps, confirmation dialogs, charts |
| **Auth** | Auth0 Universal Login + Token Vault + CIBA + Guardian MFA | Identity, federated token exchange, per-service consent, step-up auth for destructive actions |
| **Agent** | Strands Agents SDK | Function-calling loop with BeforeToolCall/AfterToolCall hooks |
| **LLM** | IBM Granite 4 Micro via llama-server (local, port 8080) | Tool routing, contextual PII detection, policy analysis |
| **PII** | Regex (structural) + Granite Micro (contextual) | Hybrid two-layer detection |
| **Policy** | BM25 over 1,059 Docling-extracted chunks | RAG grounding from ICRC/IASC/GDPR/Sphere PDFs |
| **OCR** | IBM Docling + granite-docling-258M | Scanned PDF/DOCX text extraction |
| **APIs** | Microsoft Graph, Slack Web API | OneDrive files, Outlook email, Slack messages |

### UI Design

Chat interface over dashboard. Field workers in humanitarian operations don't have time to learn a new tool with 15 tabs. They need to say "scan the Protection folder" and see what comes back. Starter buttons provide guided discovery for users who don't know what to ask, organized by task: scanning, compliance, remediation. A task panel tracks every agent action in real time so the user always knows what's happening. Each tool call shows as a collapsible Step in the chat with the full input and output accessible, so the user can see exactly which API the agent called, what arguments it passed, and what came back. Scan results render as interactive Plotly charts for quick triage: risk distribution by file, PII types found, sharing status breakdown. The CIBA push for destructive actions is a UX decision as much as a security one. A protection officer approving deletion of a GBV file should do it on a separate device with a clear binding message, not by clicking a button in the same window where the chatbot just said "do you want me to delete this?"

## Challenges I Ran Into

**Slack OAuth v2 + Auth0 generic oauth2 strategy**: Slack's v2 OAuth uses `user_scope` as a separate parameter from `scope`, but Auth0's generic oauth2 connection strategy only sends `scope` in the authorization URL. I could not get write scopes (`chat:write`, `files:write`) through Token Vault regardless of the connection configuration.

Solution: separate read and write credentials. Token Vault handles read operations (scanning messages via user token). A separate Slack bot token handles write operations (posting data protection alerts). Turns out the separation is actually the right architecture anyway. Data protection alerts should come from the bot identity, not impersonate the user.

**Token rotation and cache staleness**: Slack's token rotation meant Token Vault would return revoked tokens after I invalidated them during debugging. The stored Connected Account had to be deleted via the Management API (`DELETE /api/v2/users/{id}/connected-accounts/{cac_id}`) and refresh tokens flushed (`DELETE /api/v2/users/{id}/refresh-tokens`) to force a full re-authentication.

**Granite Micro and vague queries**: A 3B parameter model requires explicit tool-routing instructions. "Scan everything" would sometimes fail to call the right tools or call the wrong ones. I added explicit routing rules to the system prompt (`scan_files` for OneDrive, `search_messages` for Slack/Outlook) and query expansion for common shorthand ("check all my files" → detailed scan instruction).

**PII detection for non-Latin scripts**: The initial regex pattern `\b[A-Z][a-z]+ [A-Z][a-z]+\b` catches English-style names but misses Arabic names (محمد), Bengali names (মোহাম্মদ), and Burmese names, exactly the populations humanitarian organizations serve. Reading "An Evaluation Study of Hybrid Methods for Multilingual PII Detection" (2025) led me to implement the hybrid regex + LLM architecture, where the LLM handles multilingual and contextual PII that regex cannot express.

## Accomplishments I'm Proud Of

**The Rohingya scenario could have been caught by this tool.** If UNHCR field staff had something like Amanat scanning their shared drives, it would have flagged the biometric enrollment data as publicly accessible special-category data, cited ICRC Handbook Chapter 8 and GDPR Article 9, and required explicit confirmation before any sharing changes. The demo shows exactly this with the Waqwaq scenario.

**Fully local, fully open-source AI.** No beneficiary data ever touches a cloud LLM API. The entire stack is Apache 2.0 or MIT licensed: Granite 4 Micro (Apache 2.0, ISO 42001 certified), Docling (MIT), llama.cpp (MIT), Strands SDK (Apache 2.0). An NGO can deploy this without a single vendor dependency, licensing fee, or data processing agreement. I built a Containerfile that packages everything for offline field deployment.

**PII never reaches the LLM.** Tool results are truncated and stripped before being returned to the agent context. The `redact_pii_in_text()` function is used during file redaction and Slack scanning workflows to replace PII with category labels like `[NAME REDACTED]` and `[CASE# REDACTED]`. The unredacted scan details only show up in the Chainlit UI steps, visible to the authenticated user.

**Real policy grounding.** I downloaded the actual ICRC Handbook (400+ pages), IASC Operational Guidance, GDPR full text, and Sphere Handbook as PDFs. Docling extracted 1,059 text chunks. BM25 retrieves the relevant sections at query time. The agent cites "ICRC Handbook Chapter 8.2.1" because it read Chapter 8.2.1, not because it hallucinated a citation.

**Research-backed PII detection.** The hybrid detection architecture is grounded in "An Evaluation Study of Hybrid Methods for Multilingual PII Detection" (2025), which demonstrated that combining regex with LLM-based extraction outperforms either approach alone. My implementation catches implicit identifiers like "the 15-year-old girl in Vakwa Shelter" that regex cannot detect.

**40/40 agent queries pass.** A test harness (`scripts/test_40_queries.py`) runs 40 queries across 8 categories. Each query is classified as PASS, PARTIAL, or FAIL based on whether the agent called the right tool and returned relevant content. Sample results:

| Query | Category | Time |
|-------|----------|------|
| "Scan my OneDrive for any files with PII that are publicly accessible." | scan-onedrive | 34s |
| "Search Slack for messages containing beneficiary names or medical information in public channels." | scan-slack | 56s |
| "Search Outlook for emails containing displaced person data sent to external recipients." | scan-outlook | 42s |
| "What does the ICRC Handbook say about sharing displaced person data with host governments?" | policy/RAG | 57s |
| "Generate a DPIA for our biometric enrollment program that collects fingerprints and iris scans." | compliance | 50s |
| "Revoke public sharing on the GBV incident reports." | remediation | 37s |
| "What can you help me with?" | edge case | 49s |
| "ابحث عن أي ملفات تحتوي على بيانات شخصية مشاركة بشكل عام" | multilingual (Arabic) | 5s |

All 40 passed: OneDrive scan (8/8), Slack scan (4/4), Outlook scan (3/3), policy/RAG (8/8), compliance (5/5), remediation (5/5), edge cases (4/4), multilingual (3/3: Arabic, French, Spanish). Full results in `test_results.jsonl`.

## What I Learned

**Token Vault is the right abstraction for multi-service agents.** One authentication event, per-service scoped tokens, automatic refresh, user-controlled consent. Users connect and disconnect services individually. The agent never stores raw credentials. Token expiry handled transparently. Every AI agent that touches multiple services on behalf of a user should work this way.

**Small models are sufficient when tools are deterministic.** Granite 4 Micro (3B params) reliably handles tool routing, policy analysis, and report generation. The thing I kept running into: if you ask the LLM to detect PII directly, it hallucinates. Deterministic regex for structural patterns, LLM only for contextual extraction where it actually adds value. Let the LLM reason about findings, let the scanner produce them.

**Humanitarian data governance is a software problem, not a policy problem.** The ICRC published a handbook. The IASC published operational guidance. The Sphere Standards include protection principles. All the policy documents are there. Nobody has built software that enforces them across the cloud services field teams actually use.

**Hybrid approaches beat pure approaches.** PII detection (regex + LLM beats either alone) and policy retrieval (BM25 + document preprocessing beats keyword search) both pointed the same direction. Combining specialized approaches kept outperforming any single method at every layer.

**Agent authorization needs a consent model on top of the auth model.** The hard question wasn't "how do I get a token." It was "when should the agent be allowed to act?" Scanning is read-only, fine. Revoking a sharing link on a GBV file has real consequences. I landed on CIBA: the agent sends a Guardian push notification to the user's phone describing the exact action. The user approves or denies on a separate device. Clicking "yes" in a chat window isn't enough when the action affects real files containing real people's data.

## Why This Matters Beyond the Demo

Enterprise DLP tools (Varonis, Microsoft Purview, Symantec DLP) cost $5,000 to $50,000 per year and require dedicated security teams to configure. They're built for corporations, not field offices where 56% of NGOs have no cybersecurity budget and a third have no IT support at all (CyberPeace, 2024). Amanat is free, open-source, runs on a laptop, and is grounded in the specific policy frameworks humanitarian organizations already follow (ICRC, IASC, Sphere, GDPR). The entire stack is containerizable for offline deployment in connectivity-constrained environments, which is exactly where humanitarian field teams operate.

UNHCR runs Microsoft 365 across field locations. WFP's SCOPE system holds data on 90 million beneficiaries. These organizations use OneDrive, Outlook, and Slack daily. But none of these platforms have built-in humanitarian data governance. No automated sensitivity detection, no policy enforcement against ICRC rules, no cross-service visibility into what's been shared and with whom. Amanat sits on top of these existing services via Token Vault and adds the governance layer that's missing.

Amanat acts on real files across real services with real consequences. Token Vault is what makes that possible without the agent ever holding raw credentials.

## What's Next for Amanat

**Near-term:**
- Voice input via local Whisper for field workers with limited literacy
- GPS module integration for location-aware policy checks
- Real-time Slack monitoring via Events API, flagging PII the moment it's posted
- Extended multilingual PII patterns for Arabic, French, Spanish, Swahili

**Medium-term:**
- Role-based access via Auth0 RBAC so protection officers see GBV files and field coordinators don't
- Semantic embedding search for policies (replacing BM25 with vector retrieval)
- HDX (Humanitarian Data Exchange) integration for cross-organization data governance

**Long-term:**
- Federated deployment where multiple field offices run local Amanat instances. Central HQ gets aggregated compliance dashboards (violation counts, remediation rates) but never raw PII.
- Differential privacy for donor-facing statistics
- Hardware security modules for biometric data encryption keys
- Ruggedized container deployments for conflict zone field offices

## Scope and Limitations

I joined this hackathon late and built Amanat to demonstrate what Token Vault-powered data governance looks like end-to-end. The core loop works: authenticate via Auth0, connect services via Token Vault, scan across OneDrive/Slack/Outlook, detect PII, cite policy, and remediate with confirmation. Granite 4 Micro was chosen specifically because it scales to the infrastructure humanitarian organizations actually have. A laptop in a field office, no GPU, no cloud dependency, no data leaving the device. That's the deployment model.

The Auth0 integration is functional but not yet production-hardened. Token handoff between the Chainlit session and Connected Accounts routes uses a temporary file rather than a proper session store. The `send_email` tool sends as the logged-in user via Graph API (`POST /me/sendMail`) rather than a dedicated service mailbox, which was simpler to implement with Token Vault's user token but wouldn't be appropriate for production alerts. Session management plumbing, not architectural problems. A production version would add persistent storage, Auth0 RBAC, a dedicated alert mailbox, real-time Slack monitoring, and field testing with protection officers.

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Authentication | Auth0 Universal Login | User login |
| Token management | Auth0 Token Vault | Federated token exchange for OneDrive, Slack, Outlook |
| Step-up auth | Auth0 CIBA + Guardian push notifications | Destructive actions require approval on a separate device via `POST /bc-authorize` |
| LLM | IBM Granite 4 Micro (3B) via llama-server | Agent reasoning, contextual PII detection, report generation |
| Agent framework | Strands Agents SDK | Function-calling agent loop with retry logic |
| Document parsing | IBM Docling + granite-docling-258M | OCR for scanned PDFs, text extraction from Office docs |
| Policy retrieval | BM25 (rank_bm25) over Docling-extracted chunks | RAG grounding from real ICRC/IASC/GDPR/Sphere PDFs |
| PII detection | Regex (structural) + Granite Micro (contextual) | Hybrid RECAP-inspired two-layer detection |
| Web UI | Chainlit | Chat interface with OAuth, steps, charts, actions |
| APIs | Microsoft Graph, Slack Web API | OneDrive/Outlook file access, Slack message scanning |
| Security | Fernet/PBKDF2 encryption, PII redaction, session wipe | Defense-in-depth for beneficiary data |
| Language | Python 3.13, httpx, pydantic, pandas, plotly | Core runtime |

## References

Human Rights Watch. (2021). UN Shared Rohingya Data Without Informed Consent. https://www.hrw.org/news/2021/06/15/un-shared-rohingya-data-without-informed-consent

Human Rights Watch. (2023). The Data of the Most Vulnerable People is the Least Protected. https://www.hrw.org/news/2023/07/11/data-most-vulnerable-people-least-protected

ICRC. (2020). Handbook on Data Protection in Humanitarian Action. https://www.icrc.org/en/data-protection-humanitarian-action-handbook

ICRC. (2022). Cyber attack on ICRC: What we know. https://www.icrc.org/en/document/cyber-attack-icrc-what-we-know

IASC. (2023). Operational Guidance on Data Responsibility in Humanitarian Action. https://interagencystandingcommittee.org/operational-response/iasc-operational-guidance-data-responsibility-humanitarian-action

IBM. (2025). Granite 4.0: Hyper-efficient, High Performance Hybrid Models for Enterprise. https://www.ibm.com/granite

Sphere Association. (2018). The Sphere Handbook (4th ed.). https://spherestandards.org/handbook/

An Evaluation Study of Hybrid Methods for Multilingual PII Detection. (2025). https://arxiv.org/html/2510.07551v1

The New Humanitarian. (2021). Rohingya data protection and the UN's betrayal. https://www.thenewhumanitarian.org/opinion/2021/6/21/rohingya-data-protection-and-UN-betrayal

CyberPeace Institute. (2024). NGOs at Risk in International Geneva. https://geneva.cyberpeace.ngo/

Dalberg/ICRC. (2020). Referenced in ICRC Handbook on Data Protection in Humanitarian Action, 2nd edition.

Logo: "Cheerful File" icon by Kokota (The Noun Project), CC BY 3.0.

---

## Bonus Blog Post: Three Days, Three Token Vault Breakthroughs, One `invalid_auth` That Changed Everything

I joined this hackathon late with an idea I'd been sitting on since my time at UNICEF Innovation: humanitarian organizations need automated data governance, but the tools don't exist and the data is too sensitive to send to cloud APIs. IBM releasing Granite 4 Micro under Apache 2.0 with ISO 42001 certification made the local LLM piece viable. Auth0 Token Vault made the multi-service credential piece viable. The timing lined up.

**Day 1: The `invalid_auth` moment.** I had a single `access_token` variable. Every tool got the same token. OneDrive scans worked. Slack scans returned `invalid_auth`. I spent an hour staring at the Slack API docs before I realized: I was sending a Microsoft Graph token to the Slack API. Token Vault already scopes tokens per connection. I built a `_service_tokens` dictionary: `{"onedrive": "...", "slack": "...", "outlook": "..."}`. Each tool picks its own. The OneDrive token physically cannot touch the Slack API. For an agent handling refugee biometric data, this is the kind of isolation that matters.

**Day 2: Slack fought back.** Slack's v2 OAuth uses `user_scope` as a separate parameter from `scope`. Auth0's generic oauth2 connection only sends `scope`. I could not get `chat:write` through Token Vault no matter what I configured. I was ready to drop Slack entirely. Then I realized: data protection alerts should come from a bot, not impersonate the user. I set up a separate bot token for write operations. Token Vault handles reads. The bot handles writes. The bug became the architecture.

**Day 3: CIBA.** The original plan was an in-UI "Approve/Deny" button for destructive actions. It worked, but it felt wrong. A protection officer shouldn't approve deletion of a GBV file by clicking a button in the same chat window. I configured CIBA with Guardian push notifications. Now the agent sends a push to the user's phone with a binding message: "Amanat: revoke sharing GBV_Incident_Reports." The user approves on a separate device. The `auth_req_id` and CIBA token are displayed in the chat as proof. This is what step-up auth should look like for AI agents.

**What I'd tell the next person building a multi-service agent:** Token Vault handles the OAuth lifecycle you don't want to build. The MRRT pattern (one refresh token, multiple audiences) means you can discover connected services and exchange tokens with a single credential. CIBA gives you proper step-up auth without building your own approval flow. And if your agent handles data that can't leave the device, pair Token Vault with a local model like Granite. Token Vault manages the credentials so the agent can act across services. The local model ensures the data itself stays put. I spent my time on PII detection and policy RAG instead of writing a token database or worrying about data exfiltration. That was the right trade.

## Built With

- auth0-token-vault
- auth0-ciba
- auth0-guardian
- strands-agents-sdk
- chainlit
- docling
- granite-4-micro
- granite-docling-258m
- llama-cpp
- python
- rank-bm25

## Try It Out

- [GitHub Repo](https://github.com/msradam/amanat)
- [Architecture Doc](https://github.com/msradam/amanat/blob/main/ARCHITECTURE.md)
- [Synthetic Demo Data](https://github.com/msradam/amanat/tree/main/demo-data/drive)
