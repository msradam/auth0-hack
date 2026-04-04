# Amanat: Privacy-First Data Governance Agent for Humanitarian NGOs

Author: Adam Munawar Rahman, April 2026

Amanat scans an NGO's connected cloud services (OneDrive, Slack, Outlook) for sensitive beneficiary data that may be overshared, improperly stored, or exposed, then helps fix it. All analysis runs locally via IBM Granite 4 Micro. Beneficiary data never leaves the user's machine.

*Amanat* (Arabic/Urdu/Bengali: trust, stewardship), the concept that what is entrusted to you must be protected and returned faithfully.

---

## Inspiration

In 2021, UNHCR collected biometric data (fingerprints and iris scans) from 830,000 Rohingya refugees in Bangladesh. The refugees were told registration was required to receive food. What they weren't told was that their data would be shared with the Myanmar government, the very regime they had fled. Some discovered their names on Myanmar's repatriation lists. Biometric data is immutable. Once shared, it can never be taken back (Human Rights Watch, 2021).

This wasn't a hack. It was a governance failure.

The UNHCR-Bangladesh exercise violated the agency's own data protection policy, which requires UNHCR to tell people in a language and manner they understand why their data is being collected and whether it will be transferred to another entity. Of 24 refugees interviewed by HRW, all but one said they were not informed of potential data sharing with Myanmar. UNHCR did not carry out a data impact assessment, breaching its own policies (HRW, 2021).

The pattern repeats. In 2016, the UN's Office of Internal Oversight Services found that three of five UNHCR missions investigated had shared refugees' personal data with host governments without assessing the data protection offered by those governments or establishing transfer agreements (OIOS, 2016). In 2022, the Red Cross Family Links Network suffered a data breach affecting vulnerable populations (ICRC, 2022).

Humanitarian organizations handle some of the most sensitive data in the world: refugee case files, GBV incident reports, biometric enrollment logs, medical records of displaced persons. Yet field teams routinely store this data on cloud services with default sharing settings. A GBV report shared with "anyone with the link." Case numbers posted in public Slack channels. Beneficiary names and HIV status in a donor report email.

> "The Data of the Most Vulnerable People is the Least Protected" — Human Rights Watch, 2023

The ICRC published a 400-page Handbook on Data Protection in Humanitarian Action (2nd ed., 2020). The IASC published Operational Guidance on Data Responsibility (2023). The Sphere Standards include Protection Principles for sensitive information handling. But there is no tool that actually enforces these standards across the cloud services field teams use daily. The policy layer exists. The enforcement layer does not.

Amanat fills this gap.

## What It Does

Amanat is an AI agent that connects to an NGO's cloud services via Auth0 Token Vault, scans for sensitive data exposure, evaluates findings against humanitarian data protection standards, and takes remediation actions. All beneficiary data stays local.

### Capabilities

| Capability | Description |
|-----------|-------------|
| **Multi-service scanning** | Recursively crawls OneDrive folders, searches Slack messages and file attachments, scans Outlook emails |
| **Hybrid PII detection** | Two-layer approach: deterministic regex for structural patterns + Granite 4 Micro for contextual/multilingual extraction |
| **Policy grounding** | RAG pipeline with BM25 retrieval over 1,059 chunks extracted from actual ICRC Handbook, IASC Guidance, GDPR, and Sphere Handbook PDFs |
| **Remediation** | Revoke sharing links, redact PII for safe sharing, download before delete, generate DPIAs, check consent documentation |
| **Remediation confirmation** | Destructive actions on sensitive files trigger an in-UI confirmation dialog; the agent pauses and waits for explicit user approval before proceeding |
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

The demo uses a fictional humanitarian scenario: Post-Cataclysm Waqwaq. The Waqwaq Relief Authority (WRA) is responding to a displacement crisis on a fictional Indian Ocean archipelago inspired by Waqwaq, a legendary island from medieval Arabic geographical literature referenced by al-Idrisi (1154), Buzurg ibn Shahriyar (953), and Ibn al-Wardi (1348).

The approach follows established practice in humanitarian training: DHIS2 uses fictional countries for training data, Sphere exercises use invented scenarios, and the CDC used zombie apocalypse scenarios for emergency preparedness education. The fictional setting demonstrates real data governance patterns without using real-world sensitive data.

Demo files across OneDrive (`/WRA Operations/`):

| Folder | Files | Violations |
|--------|-------|------------|
| `/Beneficiary Records/` | Cataclysm_Displaced_Registry_2026.csv | PII: names, case IDs, medical history, GPS |
| `/Protection/` | GBV_Incident_Reports_2026.csv, GBV scanned PDF | **PUBLIC sharing — CRITICAL** |
| `/Biometric Data/` | Enrollment log, consent form, verification log | **PUBLIC sharing — CRITICAL**; special category data |
| `/Field Operations/` | Staff contacts, site register | Staff PII |
| `/Donor Relations/` | Donor report | Cross-references beneficiary case IDs |
| `/Scanned Documents/` | Registration form (image-only PDF) | Requires Docling OCR to extract PII |

## How We Built It

### Auth0 Integration

#### Token Vault (Connected Accounts)

The core integration. Users authenticate once via Auth0 Universal Login, then connect each external service through individual Connected Accounts OAuth flows. Amanat exchanges Auth0 refresh tokens for service-specific access tokens via federated token exchange:

```
POST /oauth/token
grant_type=urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token
subject_token={refresh_token}
subject_token_type=urn:ietf:params:oauth:token-type:refresh_token
requested_token_type=http://auth0.com/oauth/token-type/federated-connection-access-token
connection=microsoft-graph
```

The agent calls Microsoft Graph and Slack APIs on behalf of the user without ever storing raw service credentials. Token expiry is tracked via `TokenInfo.is_expired()` with a 60-second buffer, triggering automatic re-exchange.

Per-service scoping:

| Service | Connection | Scopes |
|---------|-----------|--------|
| OneDrive | `microsoft-graph` | `Files.Read`, `Files.ReadWrite`, `offline_access` |
| Outlook | `microsoft-graph` | `Mail.Read`, `Mail.Send`, `offline_access` |
| Slack (read) | `sign-in-with-slack` | `channels:read`, `channels:history`, `search:read` |
| Slack (write) | Bot token | `chat:write` (separate credential, posts as "Amanat") |

#### Remediation Confirmation

When the agent detects a destructive action on a file matching sensitive patterns (`gbv`, `biometric`, `incident`, `medical`, `protection`), it triggers an in-UI confirmation dialog. The agent pauses and waits for explicit user approval before proceeding. This ensures a chatbot doesn't delete a GBV file just because someone typed "yes" in the conversation -- the user must explicitly confirm the specific destructive action. MFA via Auth0 Guardian protects the login session itself.

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

3. **Retrieval**: BM25 (Best Match 25) ranking over chunk text. BM25 handles term frequency, inverse document frequency, and document length normalization, outperforming keyword matching for policy documents where the same concept appears in different terminology

4. **Injection**: Top 5 chunks formatted in Granite 4's native `<documents>` RAG format:

```
<documents>
{"doc_id": 42, "title": "8.2.1 LEGAL BASES FOR PERSONAL DATA PROCESSING",
 "source": "ICRC Handbook", "text": "Humanitarian Organizations may process..."}
</documents>
```

Example: the query "Can we share biometric data with host governments?" retrieves ICRC Handbook Chapter 4.2 (International Data Sharing), Chapter 8.2.1 (Legal Bases for Biometric Processing), and Chapter 8.2.4 (Data Minimization), the same sections a data protection officer would consult.

### IBM Granite 4 Micro

Granite 4.0 Micro is a 3B-parameter hybrid Mamba-Transformer model designed for edge deployment (IBM, 2025). Key properties for our use case:

- **70% less memory** than comparable transformer-only models due to Mamba-2 linear attention layers
- **Native function calling** with structured JSON output. The agent loop is driven by Strands Agents SDK, which provides native tool-call lifecycle hooks (BeforeToolCallEvent, AfterToolCallEvent) for Chainlit UI integration and confirmation dialog interception.
- **Multilingual**: English, Arabic, French, Spanish, Japanese, Korean, Chinese, and 5 other languages, which is critical for humanitarian contexts
- **128K validated context** with 512K training length, sufficient for large policy documents and scan results
- Runs locally via llama-server (llama.cpp) on consumer hardware. No GPU required.

### IBM Docling + granite-docling-258M

Field documents are often scanned: printed intake forms, hand-filled registration sheets, faxed protection assessments. These arrive as image-only PDFs with no embedded text layer.

Docling's standard pipeline handles embedded-text documents (CSV, DOCX, XLSX). For image-only PDFs, the granite-docling-258M VLM pipeline provides OCR with table structure recognition (0.96 TEDS score). On Apple Silicon, the MLX backend accelerates inference.

Integration: when the OneDrive scanner downloads a binary document format (PDF, DOCX, PPTX, XLSX), it automatically routes through Docling for text extraction before PII detection. The routing is transparent to the user and the agent.

### Security Hardening

| Control | Implementation |
|---------|---------------|
| Local LLM | Granite 4 Micro via llama-server. No cloud API calls. Beneficiary data stays on-machine. |
| PII redaction from LLM context | Tool results are passed through `redact_pii_in_text()` before returning to the agent. Granite sees `[NAME REDACTED]`, never raw beneficiary data. |
| Encrypted audit logs | Fernet symmetric encryption, key derived via PBKDF2 (SHA256, 480K iterations) from `CHAINLIT_AUTH_SECRET` |
| Token isolation | Auth0 Token Vault manages service credentials. Amanat never stores raw OAuth tokens. |
| Download before delete | Every `delete_file` action automatically downloads a local copy first |
| Session wipe | Scan results, conversation history, and Token Vault session cleared on chat end |
| Credential separation | Slack reading uses user token (via Token Vault); Slack writing uses bot token (separate credential) |
| Confirmation gate | Destructive actions on sensitive files require explicit user approval via in-UI confirmation dialog |

### Agent Architecture

```
                         Auth0
                      ┌──────────────────────────┐
                      │  Universal Login         │
            ┌────────►│  Token Vault             │
            │         └────────────┬─────────────┘
            │                      │ federated access tokens
┌───────────┴───┐     ┌───────────▼───────────────┐     ┌────────────────┐
│   Chainlit    │◄───►│        Amanat             │◄───►│  IBM Granite 4 │
│   Web UI      │     │                           │     │  Micro (local) │
│               │     │  Strands Agents SDK       │     │  llama-server  │
│  • OAuth      │     │  ┌─ Regex PII detector    │     │  port 8080     │
│  • Steps      │     │  ├─ LLM PII detector      │     └────────────────┘
│  • Charts     │     │  ├─ Policy RAG (BM25)     │
│  • Actions    │     │  ├─ Rules engine          │     ┌─────────────────┐
│  • Confirm    │     │  └─ Docling OCR           │◄───►│  IBM Docling    │
└───────────────┘     └───────────┬───────────────┘     │  granite-258M   │
                                  │                     └─────────────────┘
                           ┌──────┼──────┐
                           ▼      ▼      ▼
                       OneDrive Outlook Slack
```

## Challenges We Ran Into

**Slack OAuth v2 + Auth0 generic oauth2 strategy**: Slack's v2 OAuth uses `user_scope` as a separate parameter from `scope`, but Auth0's generic oauth2 connection strategy only sends `scope` in the authorization URL. We could not get write scopes (`chat:write`, `files:write`) through Token Vault regardless of the connection configuration.

Solution: separate read and write credentials. Token Vault handles read operations (scanning messages via user token). A separate Slack bot token handles write operations (posting data protection alerts). In practice, the separation is architecturally correct: data protection alerts should come from the bot identity, not impersonate the user.

**Token rotation and cache staleness**: Slack's token rotation meant Token Vault would return revoked tokens after we invalidated them during debugging. The stored Connected Account had to be deleted via the Management API (`DELETE /api/v2/users/{id}/connected-accounts/{cac_id}`) and refresh tokens flushed (`DELETE /api/v2/users/{id}/refresh-tokens`) to force a full re-authentication.

**BeeAI to Strands migration**: We initially used BeeAI Framework's `ReActAgent`, which implements text-based ReAct parsing where the model must output structured `Thought:` / `Action:` / `Observation:` lines. Granite via llama-server uses the OpenAI function-calling protocol (tool calls in the response message, not text prefixes). We ultimately migrated to Strands Agents SDK, which provides `BeforeToolCallEvent` hooks for confirmation dialog interception and Chainlit UI integration. The error message (`LinePrefixParserError: Nothing valid has been parsed yet!`) was clear once we understood the distinction.

**Granite Micro and vague queries**: A 3B parameter model requires explicit tool-routing instructions. "Scan everything" would sometimes fail to call the right tools or call the wrong ones. We added explicit routing rules to the system prompt (`scan_files` for OneDrive, `search_messages` for Slack/Outlook) and query expansion for common shorthand ("check all my files" → detailed scan instruction).

**PII detection for non-Latin scripts**: The initial regex pattern `\b[A-Z][a-z]+ [A-Z][a-z]+\b` catches English-style names but misses Arabic names (محمد), Bengali names (মোহাম্মদ), and Burmese names, the very populations humanitarian organizations serve. Research into the RECAP paper (2025) led us to implement the hybrid regex + LLM architecture, where the LLM handles multilingual and contextual PII that regex cannot express.

## Accomplishments That We're Proud Of

**The Rohingya scenario could have been prevented by this tool.** If UNHCR field staff had Amanat scanning their shared drives, it would have flagged the biometric enrollment data as publicly accessible special-category data, cited ICRC Handbook Chapter 8 and GDPR Article 9, and required explicit confirmation before any destructive remediation. The demo shows this with the Waqwaq scenario.

**Fully local AI.** No beneficiary data ever touches a cloud LLM API. Granite 4 Micro runs on a laptop via llama-server. The entire stack (LLM, document parser, PII detector, policy database) is containerizable for offline field deployment. We built a Containerfile that proves it.

**PII never reaches the LLM.** Tool results are redacted before being returned to the agent. Granite sees `[NAME REDACTED]` and `[CASE# REDACTED]`, never raw beneficiary data. The unredacted data is only shown in the Chainlit UI steps, visible to the authenticated user. A defense-in-depth measure against prompt injection and model memorization.

**Real policy grounding.** We downloaded the actual ICRC Handbook (400+ pages), IASC Operational Guidance, GDPR full text, and Sphere Handbook as PDFs. Docling extracted 1,059 text chunks. BM25 retrieves the relevant sections at query time. The agent cites "ICRC Handbook Chapter 8.2.1" because it read Chapter 8.2.1, not because it hallucinated a citation.

**Research-backed PII detection.** The hybrid detection architecture is grounded in the RECAP paper (2025), which demonstrated that combining regex with LLM-based extraction outperforms either approach alone. Our implementation catches implicit identifiers like "the 15-year-old girl in Vakwa Shelter" that regex cannot detect.

**49/50 agent queries pass.** Tested 50 diverse queries across 5 categories: scan (15/15), policy/RAG (10/10), compliance (8/8), remediation (6/7), edge cases (10/10). One failure from a context window overflow on a multi-file remediation. 43 unit tests pass.

## What We Learned

**Auth0 Token Vault is the right abstraction for multi-service AI agents.** The federated token exchange pattern (one authentication event, per-service scoped tokens, automatic refresh, user-controlled consent) maps directly to what an agentic system requires. Users connect and disconnect services individually. The agent never stores raw credentials. Token expiry is handled transparently. All AI agents should handle multi-service access this way.

**Small models are sufficient when tools are deterministic.** Granite 4 Micro (3B params) reliably handles tool routing, policy analysis, and report generation. The key architectural insight: don't ask the LLM to detect PII (it will hallucinate). Use deterministic regex for structural patterns and the LLM only for contextual extraction where it adds value. The LLM reasons about findings; the scanner produces them.

**Humanitarian data governance is a software gap, not a policy gap.** The ICRC published a handbook. The IASC published operational guidance. The Sphere Standards include protection principles. The policies exist. What doesn't exist is software that enforces them across the cloud services field teams actually use. Amanat attempts to bridge that gap.

**Hybrid approaches beat pure approaches.** PII detection (regex + LLM beats either alone) and policy retrieval (BM25 + document preprocessing beats keyword search) both showed the same result. At every layer, combining specialized approaches outperformed any single method.

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

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Authentication | Auth0 Universal Login | User login |
| Token management | Auth0 Token Vault | Federated token exchange for OneDrive, Slack, Outlook |
| Remediation confirmation | In-UI confirmation dialog | Explicit approval for destructive actions on sensitive files |
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

ICRC. (2020). Handbook on Data Protection in Humanitarian Action (2nd ed.). https://www.icrc.org/en/data-protection-humanitarian-action-handbook

ICRC. (2022). Cyber attack on ICRC: What we know. https://www.icrc.org/en/document/cyber-attack-icrc-what-we-know

IASC. (2023). Operational Guidance on Data Responsibility in Humanitarian Action. https://interagencystandingcommittee.org/operational-response/iasc-operational-guidance-data-responsibility-humanitarian-action

IBM. (2025). Granite 4.0: Hyper-efficient, High Performance Hybrid Models for Enterprise. https://www.ibm.com/new/announcements/ibm-granite-4-0

Sphere Association. (2018). The Sphere Handbook (4th ed.). https://spherestandards.org/handbook/

An Evaluation Study of Hybrid Methods for Multilingual PII Detection. (2025). https://arxiv.org/html/2510.07551v1

The New Humanitarian. (2021). Rohingya data protection and the UN's betrayal. https://www.thenewhumanitarian.org/opinion/2021/6/21/rohingya-data-protection-and-UN-betrayal

## Built With

- auth0-token-vault
- strands-agents-sdk
- chainlit
- docling
- granite-4-micro
- granite-docling-258m
- llama-cpp
- python
- rank-bm25

## Try It Out

- [GitHub Repo](https://github.com/msradam/auth0-hack)
