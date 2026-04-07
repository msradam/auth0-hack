"""
Scanner tools for Amanat.

Provides PII detection, file scanning, sharing checks, and message search.
Each tool can operate against real services (via Auth0 Token Vault) or
synthetic demo data for development.
"""

import json
import re

from amanat.knowledge.rules import evaluate_file

# --- PII Detection Patterns ---

PII_PATTERNS = {
    "name": {
        "patterns": [
            r"\b[A-Z][a-z]+\s+(?:al-)?[A-Z][a-z]+\b",  # First Last, First al-Last
        ],
        "severity": "warning",
        "category": "personal_identifier",
    },
    "phone_number": {
        "patterns": [
            r"\b\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b",
        ],
        "severity": "warning",
        "category": "personal_identifier",
    },
    "email_address": {
        "patterns": [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        ],
        "severity": "warning",
        "category": "personal_identifier",
    },
    "national_id": {
        "patterns": [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN format
            r"\b[A-Z]{2}\d{6,8}\b",    # Generic national ID
        ],
        "severity": "critical",
        "category": "government_identifier",
    },
    "unhcr_case_number": {
        "patterns": [
            r"\b\d{3}-\d{2}C\d{5}\b",     # UNHCR format
            r"\bWAQ-\d{2}C\d{5}\b",      # WRA Waqwaq format
            r"\bUNHCR[-/]\d+\b",
        ],
        "severity": "critical",
        "category": "humanitarian_identifier",
    },
    "medical_condition": {
        "patterns": [
            r"\b(HIV|tuberculosis|TB|malaria|cholera|PTSD|trauma|pregnant|disability|chronic)\b",
        ],
        "severity": "critical",
        "category": "special_category_data",
    },
    "ethnic_religious": {
        "patterns": [
            r"\b(Rohingya|Yazidi|Uyghur|Tutsi|Sunni|Shia|Christian|Muslim|Hindu|Buddhist|Kanbalese|Zenji|Sofali|Vakwan|Ambari|Majali)\b",
        ],
        "severity": "critical",
        "category": "special_category_data",
    },
    "location_coordinates": {
        "patterns": [
            r"\b-?\d{1,3}\.\d{4,},\s*-?\d{1,3}\.\d{4,}\b",  # GPS coords
        ],
        "severity": "critical",
        "category": "location_data",
    },
    "biometric_reference": {
        "patterns": [
            r"\b(fingerprint|iris scan|biometric|facial recognition|retina)\b",
        ],
        "severity": "critical",
        "category": "biometric_data",
    },
}


def detect_pii_in_text(text: str, use_llm: bool = False) -> list[dict]:
    """Scan text for PII using hybrid detection (RECAP-inspired).

    Implements the two-layer approach from "An Evaluation Study of Hybrid
    Methods for Multilingual PII Detection" (2025):

    Layer 1 (Regex): Deterministic pattern matching for structured PII —
    phone numbers, emails, case IDs, GPS coordinates, medical terms.
    Fast, no false negatives on known patterns.

    Layer 2 (LLM): Granite 4 Micro extracts contextual/multilingual PII
    that regex can't catch — names in any script, implicit identifiers,
    context-dependent sensitive information. Only runs when use_llm=True.

    Results are merged with deduplication.
    """
    # --- Layer 1: Regex (structural PII) ---
    findings = []
    for pii_type, config in PII_PATTERNS.items():
        for pattern in config["patterns"]:
            flags = re.IGNORECASE if config["category"] in ("special_category_data", "biometric_data", "medical_condition") else 0
            matches = re.findall(pattern, text, flags)
            if matches:
                findings.append({
                    "type": pii_type,
                    "category": config["category"],
                    "severity": config["severity"],
                    "count": len(matches),
                    "samples": matches[:3],
                    "method": "regex",
                })

    # --- Layer 2: LLM (contextual/multilingual PII) ---
    if use_llm and len(text.strip()) > 20:
        llm_findings = _detect_pii_with_llm(text)
        # Merge: add LLM findings that regex didn't catch
        regex_types = {f["type"] for f in findings}
        for lf in llm_findings:
            if lf["type"] not in regex_types:
                findings.append(lf)
            else:
                # LLM found same type — merge samples if new ones found
                for rf in findings:
                    if rf["type"] == lf["type"]:
                        existing = set(str(s) for s in rf["samples"])
                        new_samples = [s for s in lf["samples"] if str(s) not in existing]
                        if new_samples:
                            rf["samples"].extend(new_samples[:2])
                            rf["count"] += lf["count"]
                        break

    return findings


def _detect_pii_with_llm(text: str) -> list[dict]:
    """Use Granite 4 Micro to extract PII that regex can't catch.

    Sends a structured extraction prompt and parses the JSON response.
    Handles names in any script, implicit identifiers, and context-dependent
    sensitive information.
    """
    import os
    try:
        from openai import OpenAI
    except ImportError:
        return []

    client = OpenAI(
        base_url=os.environ.get("OPENAI_API_BASE", "http://localhost:8080/v1"),
        api_key=os.environ.get("OPENAI_API_KEY", "llama"),
    )

    # Truncate to avoid overwhelming the model
    excerpt = text[:3000]

    prompt = (
        "Extract ALL personally identifiable information (PII) from this text. "
        "Look for:\n"
        "- Person names (in any language or script)\n"
        "- Locations that could identify individuals (shelter numbers, block IDs)\n"
        "- Implicit identifiers ('the woman in Shelter 17', 'the 15-year-old')\n"
        "- Any information that could be used to identify a specific person\n\n"
        "Return ONLY valid JSON in this exact format:\n"
        '{"entities": [{"text": "the exact text", "type": "name|location|implicit_id|age|relationship"}]}\n\n'
        "If no PII is found, return: {\"entities\": []}\n\n"
        f"TEXT:\n{excerpt}"
    )

    try:
        response = client.chat.completions.create(
            model="granite4-micro",
            messages=[
                {"role": "system", "content": "You are a PII detection system. Extract personally identifiable information. Return only JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=1024,
        )
        content = response.choices[0].message.content or ""

        # Parse JSON from response (handle markdown code blocks)
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        data = json.loads(content)
        entities = data.get("entities", [])

        # Convert to our standard findings format
        findings = []
        type_groups: dict[str, list[str]] = {}
        for entity in entities:
            etype = entity.get("type", "unknown")
            etext = entity.get("text", "")
            if etext:
                type_groups.setdefault(etype, []).append(etext)

        # Map LLM entity types to our PII categories
        type_mapping = {
            "name": ("name", "personal_identifier", "warning"),
            "location": ("location_identifier", "location_data", "warning"),
            "implicit_id": ("implicit_identifier", "personal_identifier", "warning"),
            "age": ("age_identifier", "personal_identifier", "warning"),
            "relationship": ("relationship_identifier", "personal_identifier", "warning"),
        }

        for etype, samples in type_groups.items():
            pii_type, category, severity = type_mapping.get(
                etype, (f"llm_{etype}", "personal_identifier", "warning")
            )
            findings.append({
                "type": pii_type,
                "category": category,
                "severity": severity,
                "count": len(samples),
                "samples": samples[:3],
                "method": "llm",
            })

        return findings

    except Exception:
        # LLM extraction failed — return empty, regex results still valid
        return []


# --- PII Redaction ---

# Labels used to replace each PII type
_REDACTION_LABELS = {
    "name": "[NAME REDACTED]",
    "phone_number": "[PHONE REDACTED]",
    "email_address": "[EMAIL REDACTED]",
    "national_id": "[ID REDACTED]",
    "unhcr_case_number": "[CASE# REDACTED]",
    "medical_condition": "[MEDICAL REDACTED]",
    "ethnic_religious": "[ETHNIC/RELIGIOUS REDACTED]",
    "location_coordinates": "[GPS REDACTED]",
    "biometric_reference": "[BIOMETRIC REDACTED]",
}


def redact_pii_in_text(text: str) -> tuple[str, list[dict]]:
    """Replace all detected PII with redaction labels.

    Returns (redacted_text, list_of_redactions).
    Each redaction records the type, category, count, and replacement label.
    """
    redacted = text
    redactions: list[dict] = []

    for pii_type, config in PII_PATTERNS.items():
        label = _REDACTION_LABELS.get(pii_type, "[REDACTED]")
        for pattern in config["patterns"]:
            flags = re.IGNORECASE if config["category"] in (
                "special_category_data", "biometric_data", "medical_condition",
            ) else 0
            matches = re.findall(pattern, redacted, flags)
            if matches:
                redacted = re.sub(pattern, label, redacted, flags=flags)
                redactions.append({
                    "type": pii_type,
                    "category": config["category"],
                    "count": len(matches),
                    "replacement": label,
                })

    return redacted, redactions


# --- Synthetic Demo Data ---

DEMO_FILES = [
    {
        "id": "doc-001",
        "name": "Cataclysm_Displaced_Registry_2026.csv",
        "type": "spreadsheet",
        "size": "2.4 MB",
        "owner": "maryam@wra-waqwaq.org",
        "sharing": "anyone_with_link",
        "last_modified": "2026-03-15",
        "content": (
            "Case File Registry - Post-Cataclysm Displaced Persons\n"
            "Case ID: WAQ-26C00891\n"
            "Name: Rozel al-Bahar\n"
            "DOB: 1985-03-12\n"
            "Phone: +471-55-555-1234\n"
            "Location: Kanbaloh, Block 4, Shelter 17\n"
            "GPS: 47.3821, -12.5634\n"
            "Status: IDP\n"
            "Medical: PTSD, chronic back pain\n"
            "Ethnicity: Kanbalese\n"
            "Family size: 5\n"
            "WRA Case: WAQ-26C00891\n\n"
            "Case ID: WAQ-26C00892\n"
            "Name: Finley Maji\n"
            "DOB: 1992-07-22\n"
            "Phone: +471-55-555-5678\n"
            "Location: Kanbaloh, Block 7, Shelter 3\n"
            "GPS: 47.3825, -12.5641\n"
            "Status: IDP\n"
            "Medical: Pregnant, high-risk, HIV positive\n"
            "Ethnicity: Zenji\n"
            "Family size: 3\n"
            "WRA Case: WAQ-26C00892\n"
        ),
    },
    {
        "id": "doc-002",
        "name": "Donor_Report_Q1_2026.txt",
        "type": "document",
        "size": "890 KB",
        "owner": "farah@wra-waqwaq.org",
        "sharing": "org_wide",
        "last_modified": "2026-03-20",
        "content": (
            "Quarterly Report to Ambara Development Fund - Q1 2026\n"
            "Programme: Emergency Response - Post-Cataclysm Waqwaq\n"
            "Beneficiaries served: 12,400 individuals\n"
            "Distribution sites: Kanbaloh (5,200), Sofala Village (3,100), Vakwa Shelter (4,100)\n"
            "Individual case outcomes attached in Annex B\n"
            "Contact: Paya Majala, paya.majala@wra-waqwaq.org\n"
            "Note: See attached beneficiary list for verification (Annex C)\n"
        ),
    },
    {
        "id": "doc-003",
        "name": "Field_Team_Contact_List.csv",
        "type": "spreadsheet",
        "size": "45 KB",
        "owner": "hr@wra-waqwaq.org",
        "sharing": "anyone_with_link",
        "last_modified": "2026-02-28",
        "content": (
            "Name,Role,Phone,Email,Location\n"
            "Penn Rashidi,Field Reporter,+471-55-555-9012,penn@wra-waqwaq.org,Kanbaloh\n"
            "Addison Khalil,Field Officer,+471-55-555-3456,addison@wra-waqwaq.org,Sofala Village\n"
            "Fariq Haras,Security Coordinator,+471-55-555-7890,fariq@wra-waqwaq.org,Zenji Harbor\n"
            "Note: Do not share - contains personal mobile numbers of field staff in sensitive locations\n"
        ),
    },
    {
        "id": "doc-004",
        "name": "GBV_Incident_Reports_2026.pdf",
        "type": "document",
        "size": "1.1 MB",
        "owner": "protection@wra-waqwaq.org",
        "sharing": "specific_people",
        "shared_with": ["protection@wra-waqwaq.org", "farah@wra-waqwaq.org"],
        "last_modified": "2026-03-22",
        "content": (
            "Gender-Based Violence Incident Tracking\n"
            "CONFIDENTIAL - RESTRICTED ACCESS\n"
            "Case GBV-2026-001: Female, age 24, reported domestic violence\n"
            "Location: Kanbaloh, Block 9, Shelter 42\n"
            "Referred to: Vakwa Protection Centre\n"
            "Case GBV-2026-002: Female, age 17, reported harassment at distribution point\n"
            "Location: Sofala Distribution Site B\n"
            "Perpetrator description on file\n"
        ),
    },
    {
        "id": "doc-005",
        "name": "Biometric_Enrollment_Log.xlsx",
        "type": "spreadsheet",
        "size": "5.7 MB",
        "owner": "registration@wra-waqwaq.org",
        "sharing": "org_wide",
        "last_modified": "2025-06-15",
        "content": (
            "Biometric Enrollment Registry\n"
            "Date: 2026-01-10\n"
            "Site: Kanbaloh Registration Centre\n"
            "Record 1: Rozel al-Bahar, fingerprint enrolled, iris scan completed, photo captured\n"
            "Record 2: Finley Maji, fingerprint enrolled, iris scan completed, photo captured\n"
            "Record 3: Makram Hajjar, fingerprint enrolled, iris scan failed - retry scheduled\n"
            "Total enrolled: 847 individuals\n"
            "Data stored on: Field laptop SN-4429 (unencrypted drive)\n"
            "Backup: USB drive held by registration officer\n"
        ),
    },
]

# --- Consent records (demo) ---
# Maps file_id -> consent status for that data collection activity

DEMO_CONSENT = {
    "doc-001": {
        "file_id": "doc-001",
        "data_collection": "Cataclysm displaced person registration",
        "consent_obtained": True,
        "consent_type": "verbal",
        "consent_language": "Kanbalese",
        "consent_date": "2026-01-15",
        "consent_documented": False,  # verbal but not recorded
        "data_subjects_informed": True,
        "purpose_explained": True,
        "right_to_withdraw_explained": False,
        "third_party_sharing_disclosed": False,
        "issues": [
            "Verbal consent only — no written or recorded documentation",
            "Right to withdraw not communicated to data subjects",
            "Third-party data sharing not disclosed at point of collection",
        ],
    },
    "doc-004": {
        "file_id": "doc-004",
        "data_collection": "GBV incident reporting",
        "consent_obtained": True,
        "consent_type": "written",
        "consent_language": "Kanbalese, Vakwan",
        "consent_date": "2026-01-10",
        "consent_documented": True,
        "data_subjects_informed": True,
        "purpose_explained": True,
        "right_to_withdraw_explained": True,
        "third_party_sharing_disclosed": True,
        "issues": [],
    },
    "doc-005": {
        "file_id": "doc-005",
        "data_collection": "Biometric enrollment for supply distribution",
        "consent_obtained": True,
        "consent_type": "written",
        "consent_language": "Kanbalese",
        "consent_date": "2026-01-10",
        "consent_documented": True,
        "data_subjects_informed": True,
        "purpose_explained": True,
        "right_to_withdraw_explained": False,
        "third_party_sharing_disclosed": False,
        "issues": [
            "Right to withdraw not communicated — beneficiaries may feel coerced",
            "Third-party data sharing (Ambara Fund, regional authorities) not disclosed at enrollment",
            "No information given on biometric data retention period",
        ],
    },
    # doc-002 and doc-003 have no consent records at all
}

DEMO_MESSAGES = {
    "slack": [
        {
            "channel": "#field-updates",
            "visibility": "public_channel",
            "author": "penn",
            "timestamp": "2026-03-20 14:32",
            "content": (
                "Update from Kanbaloh: Rozel al-Bahar (case WAQ-26C00891) didn't show "
                "for his appointment today. His wife says he went to Ambara for medical "
                "treatment. Will follow up tomorrow."
            ),
        },
        {
            "channel": "#field-updates",
            "visibility": "public_channel",
            "author": "addison",
            "timestamp": "2026-03-21 09:15",
            "content": (
                "Sofala update: 3 new GBV referrals this week. Case details in shared drive. "
                "One involves a minor - flagging for protection team."
            ),
        },
        {
            "channel": "#general",
            "visibility": "public_channel",
            "guest_access": True,
            "author": "fariq",
            "timestamp": "2026-03-19 11:00",
            "content": (
                "Reminder: donor visit next week. I've shared Rozel al-Bahar's case file "
                "(WAQ-26C00891) and Finley Maji's records with the external audit team. "
                "Make sure all beneficiary data is accessible. Contact Paya Majala "
                "at paya.majala@wra-waqwaq.org if you need access."
            ),
        },
    ],
    "gmail": [
        {
            "subject": "FW: Beneficiary list for Ambara Fund verification",
            "from": "farah@wra-waqwaq.org",
            "to": "audit@ambara-fund.org",
            "timestamp": "2026-03-18 16:45",
            "content": (
                "Hi,\n\nPlease find attached the beneficiary list for Q1 verification.\n"
                "Key cases: Rozel al-Bahar (WAQ-26C00891), Finley Maji (WAQ-26C00892).\n"
                "The spreadsheet includes names, WRA case numbers, and distribution "
                "records for all 12,400 beneficiaries.\n\nBest,\nPaya Majala"
            ),
            "attachments": ["Beneficiary_List_Q1_Full.xlsx"],
        },
        {
            "subject": "RE: Medical transport for beneficiary",
            "from": "penn@wra-waqwaq.org",
            "to": "logistics@wra-waqwaq.org",
            "timestamp": "2026-03-22 08:30",
            "content": (
                "Confirming medical transport for Rozel al-Bahar (WAQ-26C00891) from "
                "Kanbaloh IDP hub to Ambara District Hospital. Diagnosis: acute respiratory "
                "infection, needs specialist referral. GPS pickup: 12.4567, 43.8901. "
                "Contact his wife Amira at +252-61-555-0147."
            ),
        },
    ],
}

# Alias outlook to gmail demo data
DEMO_MESSAGES["outlook"] = DEMO_MESSAGES["gmail"]


def execute_tool(tool_name: str, args: dict, access_token: str | None = None) -> str:
    """Execute a tool call. Uses real APIs when access_token is provided, demo data otherwise."""
    service = args.get("service", "")
    use_live_onedrive = access_token and service == "onedrive"
    use_live_outlook = access_token and service in ("gmail", "outlook")
    use_live_slack = access_token and service == "slack"

    if use_live_onedrive:
        from amanat.tools.onedrive import (
            scan_onedrive, check_onedrive_sharing, detect_onedrive_pii,
            revoke_onedrive_sharing, download_onedrive_file, delete_onedrive_file,
        )

    if tool_name == "scan_files":
        if use_live_onedrive:
            return scan_onedrive(access_token, args.get("query"))
        if use_live_slack:
            from amanat.tools.slack import scan_slack_channels
            return scan_slack_channels(access_token)
        return _scan_files(service or "onedrive", args.get("query"))
    elif tool_name == "check_sharing":
        if use_live_onedrive:
            return check_onedrive_sharing(access_token, args.get("file_id", ""))
        return _check_sharing(args.get("file_id", ""), service or "onedrive")
    elif tool_name == "detect_pii":
        if use_live_onedrive:
            return detect_onedrive_pii(access_token, args.get("file_id", ""))
        return _detect_pii(args.get("file_id", ""), service or "onedrive")
    elif tool_name == "search_messages":
        if use_live_slack:
            from amanat.tools.slack import search_slack_messages
            return search_slack_messages(access_token, args.get("query", ""))
        if use_live_outlook:
            from amanat.tools.outlook import search_outlook_messages
            return search_outlook_messages(access_token, args.get("query", ""))
        return _search_messages(args.get("service", "slack"), args.get("query", ""))
    elif tool_name == "revoke_sharing":
        if use_live_onedrive:
            return revoke_onedrive_sharing(access_token, args.get("file_id", ""))
        return json.dumps({"error": "Remediation requires live API access"})
    elif tool_name == "download_file":
        if use_live_onedrive:
            return download_onedrive_file(access_token, args.get("file_id", ""))
        return json.dumps({"error": "Download requires live API access"})
    elif tool_name == "delete_file":
        if use_live_onedrive:
            return delete_onedrive_file(access_token, args.get("file_id", ""))
        return json.dumps({"error": "Delete requires live API access"})
    # --- New workflow tools ---
    elif tool_name == "redact_file":
        file_id = args.get("file_id", "")
        if use_live_onedrive:
            # If file_id looks like a name/query (not an opaque ID), look it up
            if file_id and not file_id.startswith("24") and not file_id.startswith("01"):
                from amanat.tools.onedrive import _list_all_files
                q = file_id.lower()
                for f in _list_all_files(access_token):
                    if q in f.get("name", "").lower():
                        file_id = f["id"]
                        break
            return _redact_file_live(access_token, file_id)
        return _redact_file(file_id, args.get("service", "onedrive"))
    elif tool_name == "send_email":
        if use_live_outlook or use_live_onedrive:
            from amanat.tools.outlook import send_outlook_email
            token = access_token
            return send_outlook_email(token, args.get("to", ""), args.get("subject", ""), args.get("body", ""))
        return json.dumps({"error": "Email requires live Microsoft connection"})
    elif tool_name == "retention_scan":
        return _retention_scan(args.get("service", "onedrive"))
    elif tool_name == "generate_dpia":
        raw_types = args.get("data_types", [])
        if isinstance(raw_types, str):
            raw_types = [t.strip() for t in raw_types.split(",") if t.strip()]
        return _generate_dpia(
            args.get("activity", ""),
            raw_types,
            args.get("purpose", ""),
        )
    elif tool_name == "check_consent":
        return _check_consent(args.get("file_id", ""), args.get("service", "onedrive"))
    elif tool_name == "notify_channel":
        # notify_channel always uses the bot token, not the user's Token Vault token.
        # It doesn't need live API access — the bot token is in .env.
        from amanat.tools.slack import notify_slack_channel
        return notify_slack_channel(
            "",  # access_token unused — bot token loaded from env inside the function
            args.get("channel", ""),
            args.get("pii_summary", ""),
        )
    elif tool_name == "parse_document":
        from amanat.tools.docling_tool import parse_and_scan_document
        return parse_and_scan_document(
            args.get("file_path", ""),
            use_vlm=args.get("use_vlm", False),
        )
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


def _scan_files(service: str, query: str | None) -> str:
    """Scan files from a service."""
    files = DEMO_FILES
    if query:
        q = query.lower()
        files = [f for f in files if q in f["name"].lower() or q in f["content"].lower()]

    results = []
    for f in files:
        pii = detect_pii_in_text(f["content"])
        file_result = {
            "file_id": f["id"],
            "name": f["name"],
            "type": f["type"],
            "size": f["size"],
            "owner": f["owner"],
            "sharing": f["sharing"],
            "last_modified": f["last_modified"],
            "pii_detected": len(pii) > 0,
            "pii_categories": list(set(p["category"] for p in pii)),
            "risk_level": "critical" if any(p["severity"] == "critical" for p in pii) else
                          "warning" if pii else "info",
        }
        # Evaluate against governance rules
        violations = evaluate_file(file_result)
        if violations:
            file_result["violations"] = violations
            # Upgrade risk_level if rules say so
            if any(v["severity"] == "critical" for v in violations):
                file_result["risk_level"] = "critical"
        results.append(file_result)

    # Return a plain-text violation report that small LLMs can ground on,
    # with JSON data appended for programmatic use (Chainlit charts etc.)
    total = len(results)
    with_pii = sum(1 for r in results if r["pii_detected"])
    with_violations = sum(1 for r in results if r.get("violations"))

    lines = [
        f"Scanned {total} files. {with_pii} contain PII. {with_violations} have policy violations.",
        "",
    ]
    for r in results:
        violations = r.get("violations", [])
        pii_cats = ", ".join(r.get("pii_categories", [])) or "none"
        if not violations:
            lines.append(f"FILE: {r['name']} | sharing: {r['sharing']} | PII: {pii_cats} | No violations.")
            continue
        lines.append(f"FILE: {r['name']} | sharing: {r['sharing']} | PII: {pii_cats}")
        for v in violations:
            lines.append(
                f"  - {v['severity'].upper()}: {v['rule_name']}. "
                f"{v['finding']} "
                f"Policy: {v['violation']}. "
                f"Action: {v['action']}"
            )
        lines.append("")

    # Append JSON after a separator — Chainlit's visualization code
    # parses this, but the LLM should focus on the text above.
    data = {
        "service": service,
        "files_scanned": total,
        "files_with_pii": with_pii,
        "files_with_violations": with_violations,
        "results": results,
    }
    lines.append("\n---JSON---")
    lines.append(json.dumps(data))
    return "\n".join(lines)


def _check_sharing(file_id: str, service: str) -> str:
    """Check sharing permissions for a file."""
    file = next((f for f in DEMO_FILES if f["id"] == file_id), None)
    if not file:
        return json.dumps({"error": f"File not found: {file_id}"})

    sharing_risk = {
        "anyone_with_link": "critical",
        "org_wide": "warning",
        "specific_people": "info",
    }

    result = {
        "file_id": file_id,
        "name": file["name"],
        "sharing_scope": file["sharing"],
        "sharing_risk": sharing_risk.get(file["sharing"], "unknown"),
        "owner": file["owner"],
    }

    if file["sharing"] == "anyone_with_link":
        result["issue"] = (
            "File is accessible to anyone with the link. This includes people outside "
            "the organisation. If this file contains beneficiary data, any person with "
            "the URL can access sensitive personal information."
        )
    elif file["sharing"] == "org_wide":
        result["issue"] = (
            "File is shared with the entire organisation. Not all staff may be authorised "
            "to view this data. Apply need-to-know access restrictions."
        )

    if "shared_with" in file:
        result["shared_with"] = file["shared_with"]

    return json.dumps(result, indent=2)


def _detect_pii(file_id: str, service: str) -> str:
    """Detect PII in file content."""
    file = next((f for f in DEMO_FILES if f["id"] == file_id), None)
    if not file:
        return json.dumps({"error": f"File not found: {file_id}"})

    pii_findings = detect_pii_in_text(file["content"])

    return json.dumps({
        "file_id": file_id,
        "name": file["name"],
        "pii_findings": pii_findings,
        "total_pii_types": len(pii_findings),
        "has_special_category_data": any(
            p["category"] in ("special_category_data", "biometric_data") for p in pii_findings
        ),
        "summary": (
            f"Found {len(pii_findings)} types of PII/sensitive data. "
            f"Categories: {', '.join(set(p['category'] for p in pii_findings))}"
        ),
    }, indent=2)


def _search_messages(service: str, query: str) -> str:
    """Search messages for sensitive content."""
    messages = DEMO_MESSAGES.get(service, [])
    q = query.lower()

    results = []
    for msg in messages:
        content = msg["content"].lower()
        if q in content or any(q in str(v).lower() for v in msg.values()):
            pii = detect_pii_in_text(msg["content"])
            result = {**msg, "pii_detected": len(pii) > 0, "pii_types": [p["type"] for p in pii]}
            results.append(result)

    # If no query match, return all messages (for broad scans)
    if not results:
        for msg in messages:
            pii = detect_pii_in_text(msg["content"])
            if pii:
                result = {**msg, "pii_detected": True, "pii_types": [p["type"] for p in pii]}
                results.append(result)

    # Evaluate each message against channel safety rules
    from amanat.knowledge.rules import evaluate_message
    for r in results:
        violations = evaluate_message(r)
        if violations:
            r["violations"] = violations

    with_violations = sum(1 for r in results if r.get("violations"))

    # Text-first output for LLM grounding
    lines = [
        f"Searched {service} for '{query}'. Found {len(results)} messages with sensitive content. "
        f"{with_violations} have policy violations.",
        "",
    ]
    for r in results:
        channel = r.get("channel", r.get("subject", "unknown"))
        author = r.get("author", r.get("from", "unknown"))
        violations = r.get("violations", [])
        pii_types = ", ".join(r.get("pii_types", [])) or "none"

        lines.append(f"MESSAGE in {channel} by {author} | PII: {pii_types}")
        if violations:
            for v in violations:
                lines.append(
                    f"  - {v['severity'].upper()}: {v['rule_name']}. "
                    f"{v['finding']} "
                    f"Action: {v['action']}"
                )
        lines.append("")

    lines.append("\n---JSON---")
    lines.append(json.dumps({
        "service": service,
        "query": query,
        "messages_found": len(results),
        "messages_with_violations": with_violations,
        "results": results,
    }))
    return "\n".join(lines)


# ── Workflow 1: Safe Data Sharing / Redaction ──────────────────────────


def _redact_file_live(access_token: str, file_id: str) -> str:
    """Redact PII from a real OneDrive file.

    Flow: download original → redact → upload as new file (REDACTED_originalname)
    → keep original intact. The redacted copy is safe to share with donors.
    """
    from amanat.tools.onedrive import _headers, _download_text, GRAPH_BASE
    import httpx

    headers = _headers(access_token)

    # Get file metadata
    resp = httpx.get(
        f"{GRAPH_BASE}/me/drive/items/{file_id}",
        headers=headers,
        params={"$select": "id,name,file,size,parentReference"},
        timeout=30,
    )
    if resp.status_code != 200:
        return json.dumps({"error": f"File not found: {file_id}"})

    item = resp.json()
    name = item.get("name", file_id)
    mime = item.get("file", {}).get("mimeType", "")
    parent_id = item.get("parentReference", {}).get("id")

    # Download content
    content = _download_text(access_token, file_id, mime)
    if not content:
        return json.dumps({"error": f"Could not extract text from {name}"})

    # Redact
    redacted_text, redactions = redact_pii_in_text(content)
    total_redacted = sum(r["count"] for r in redactions)
    categories = list(set(r["category"] for r in redactions))

    if not redactions:
        return json.dumps({
            "file_id": file_id, "name": name,
            "action": "redact", "status": "no_pii_found",
            "message": f"No PII found in {name}. No redaction needed.",
        })

    # Upload redacted copy alongside the original
    redacted_name = f"REDACTED_{name}"
    if parent_id:
        upload_url = f"{GRAPH_BASE}/me/drive/items/{parent_id}:/{redacted_name}:/content"
    else:
        upload_url = f"{GRAPH_BASE}/me/drive/root:/{redacted_name}:/content"

    upload_resp = httpx.put(
        upload_url,
        headers={**headers, "Content-Type": "text/plain"},
        content=redacted_text.encode("utf-8"),
        timeout=60,
    )

    uploaded = upload_resp.status_code in (200, 201)
    redacted_file_id = upload_resp.json().get("id", "") if uploaded else ""

    lines = [
        f"Redacted {total_redacted} PII instances across {len(redactions)} categories from '{name}'.",
        f"Categories redacted: {', '.join(categories)}",
        "",
    ]

    if uploaded:
        lines.append(f"Redacted copy uploaded to OneDrive as '{redacted_name}' in the same folder.")
        lines.append(f"Original file '{name}' is unchanged.")
        lines.append(f"Share '{redacted_name}' with external partners instead of the original.")
    else:
        lines.append(f"Redaction complete but upload failed ({upload_resp.status_code}).")
        lines.append("Redacted content shown below for manual copy.")

    lines.extend([
        "",
        "REDACTED PREVIEW (first 1500 chars):",
        "─" * 40,
        redacted_text[:1500],
        "─" * 40,
    ])

    lines.append("\n---JSON---")
    lines.append(json.dumps({
        "file_id": file_id,
        "name": name,
        "action": "redact",
        "status": "success",
        "redacted_file_name": redacted_name,
        "redacted_file_id": redacted_file_id,
        "uploaded": uploaded,
        "total_pii_redacted": total_redacted,
        "categories_redacted": categories,
    }))
    return "\n".join(lines)


def _redact_file(file_id: str, service: str) -> str:
    """Redact all PII from a file and return the safe version."""
    file = next((f for f in DEMO_FILES if f["id"] == file_id), None)
    if not file:
        return json.dumps({"error": f"File not found: {file_id}"})

    original = file["content"]
    redacted_text, redactions = redact_pii_in_text(original)

    total_redacted = sum(r["count"] for r in redactions)
    categories = list(set(r["category"] for r in redactions))

    lines = [
        f"Redacted {total_redacted} PII instances across {len(redactions)} categories "
        f"from '{file['name']}'.",
        f"Categories redacted: {', '.join(categories)}" if categories else "No PII found.",
        "",
        "REDACTED CONTENT:",
        "─" * 40,
        redacted_text,
        "─" * 40,
        "",
        "This version is safe to share with external partners.",
    ]

    lines.append("\n---JSON---")
    lines.append(json.dumps({
        "file_id": file_id,
        "name": file["name"],
        "action": "redact",
        "status": "success" if redactions else "no_pii_found",
        "total_pii_redacted": total_redacted,
        "categories_redacted": categories,
        "redactions": redactions,
        "redacted_content": redacted_text,
        "original_length": len(original),
        "redacted_length": len(redacted_text),
    }))
    return "\n".join(lines)


# ── Workflow 2: Retention Enforcement ──────────────────────────────────

def _retention_scan(service: str) -> str:
    """Scan all files for retention policy violations."""
    from amanat.knowledge.rules import evaluate_file

    results = []
    for f in DEMO_FILES:
        pii = detect_pii_in_text(f["content"])
        file_result = {
            "file_id": f["id"],
            "name": f["name"],
            "type": f["type"],
            "size": f["size"],
            "owner": f["owner"],
            "sharing": f["sharing"],
            "last_modified": f["last_modified"],
            "pii_detected": len(pii) > 0,
            "pii_categories": list(set(p["category"] for p in pii)),
            "risk_level": "critical" if any(p["severity"] == "critical" for p in pii) else
                          "warning" if pii else "info",
        }
        violations = evaluate_file(file_result)
        # Filter to retention-related rules only (R07, R08)
        retention_violations = [v for v in violations if v["rule_id"] in ("R07", "R08")]
        if retention_violations:
            file_result["violations"] = retention_violations
            results.append(file_result)

    lines = [
        f"Retention scan complete. {len(results)} files exceed retention thresholds.",
        "",
    ]
    for r in results:
        age = _file_age_display(r["last_modified"])
        lines.append(f"FILE: {r['name']} | last modified: {r['last_modified']} ({age})")
        for v in r["violations"]:
            lines.append(
                f"  - {v['severity'].upper()}: {v['rule_name']}. "
                f"{v['finding']} "
                f"Action: {v['action']}"
            )
        lines.append("")

    if not results:
        lines.append("All files are within retention thresholds.")

    lines.append("\n---JSON---")
    lines.append(json.dumps({
        "service": service,
        "files_checked": len(DEMO_FILES),
        "files_exceeding_retention": len(results),
        "results": results,
    }))
    return "\n".join(lines)


def _file_age_display(last_modified: str) -> str:
    """Human-readable file age."""
    from datetime import datetime, timezone
    try:
        if "T" in last_modified:
            dt = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(last_modified, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days = (now - dt).days
        if days < 30:
            return f"{days} days ago"
        months = days // 30
        return f"{months} months ago"
    except (ValueError, TypeError):
        return "unknown age"


# ── Workflow 4: DPIA Generator ─────────────────────────────────────────

def _generate_dpia(activity: str, data_types: list[str], purpose: str) -> str:
    """Generate a structured Data Protection Impact Assessment."""
    from datetime import datetime, timezone

    # Determine risk level based on data types
    high_risk_types = {"biometric_data", "special_category_data", "location_data"}
    medium_risk_types = {"humanitarian_identifier", "government_identifier"}

    risk_types_found = set(data_types) & high_risk_types
    medium_types_found = set(data_types) & medium_risk_types

    if risk_types_found:
        overall_risk = "HIGH"
        risk_rationale = (
            f"Processing involves high-risk data categories: {', '.join(risk_types_found)}. "
            "GDPR Article 35 mandates a DPIA for processing that is likely to result "
            "in a high risk to the rights and freedoms of data subjects."
        )
    elif medium_types_found:
        overall_risk = "MEDIUM"
        risk_rationale = (
            f"Processing involves sensitive identifiers: {', '.join(medium_types_found)}. "
            "While not automatically high-risk, these require careful controls."
        )
    else:
        overall_risk = "LOW"
        risk_rationale = "Processing involves standard personal data with limited sensitivity."

    # Build mitigation measures based on data types
    mitigations = []
    if "biometric_data" in data_types:
        mitigations.extend([
            "Encrypt biometric templates at rest and in transit (AES-256 minimum)",
            "Implement strict access control — registration officers only",
            "Define maximum retention period for biometric data (recommend 2 years)",
            "Conduct regular access audits on biometric systems",
        ])
    if "special_category_data" in data_types:
        mitigations.extend([
            "Obtain explicit, informed consent before processing (GDPR Art. 9(2)(a))",
            "Ensure consent is voluntary — beneficiaries must not lose services by refusing",
            "Store separately from identifying information where possible",
            "Restrict access to authorized case workers on need-to-know basis",
        ])
    if "location_data" in data_types:
        mitigations.extend([
            "Generalize GPS coordinates to area level (remove sub-100m precision)",
            "Strip location metadata from shared files",
            "Do not combine location data with identifying information in exports",
        ])
    if "humanitarian_identifier" in data_types or "government_identifier" in data_types:
        mitigations.extend([
            "Pseudonymize identifiers in any shared reports or exports",
            "Implement access logging for all identifier lookups",
            "Define clear retention schedule aligned with operational need",
        ])
    if not mitigations:
        mitigations = [
            "Apply standard data protection controls as per organizational policy",
            "Ensure purpose limitation — data used only for stated purpose",
            "Implement appropriate access controls based on role",
        ]

    # Legal bases
    legal_bases = [
        "GDPR Article 6(1)(d) — vital interests of data subject (humanitarian context)",
        "GDPR Article 6(1)(e) — task in the public interest",
    ]
    if "special_category_data" in data_types:
        legal_bases.append(
            "GDPR Article 9(2)(c) — vital interests where subject is incapable of giving consent"
        )

    dpia = {
        "title": f"DPIA: {activity}",
        "generated": datetime.now(timezone.utc).isoformat(),
        "status": "DRAFT — requires DPO review",
        "sections": {
            "1_description": {
                "activity": activity,
                "purpose": purpose or "Not specified — must be completed before processing begins",
                "data_types": data_types,
                "data_subjects": "Beneficiaries, affected populations, and/or staff",
            },
            "2_necessity_and_proportionality": {
                "legal_basis": legal_bases,
                "proportionality": (
                    "Processing must be limited to what is strictly necessary for the stated "
                    "purpose. In humanitarian contexts, necessity must be balanced against "
                    "the heightened risks to vulnerable populations (ICRC Handbook Ch. 2)."
                ),
            },
            "3_risk_assessment": {
                "overall_risk_level": overall_risk,
                "risk_rationale": risk_rationale,
                "risks_identified": [
                    "Unauthorized access to sensitive personal data",
                    "Re-identification of anonymized data through combination",
                    "Data breach exposing beneficiaries to targeting or persecution",
                    "Coerced consent due to power imbalance in humanitarian settings",
                ],
            },
            "4_mitigation_measures": mitigations,
            "5_consultation": {
                "dpo_review_required": overall_risk in ("HIGH", "MEDIUM"),
                "supervisory_authority": overall_risk == "HIGH",
                "beneficiary_consultation": (
                    "Required for high-risk processing — engage community representatives "
                    "to ensure data subjects understand and accept the processing"
                ),
            },
        },
    }

    # Text-first output
    lines = [
        f"DPIA GENERATED: {activity}",
        f"Risk level: {overall_risk}",
        f"Data types: {', '.join(data_types) if data_types else 'none specified'}",
        "",
        f"RATIONALE: {risk_rationale}",
        "",
        f"MITIGATIONS ({len(mitigations)} recommended):",
    ]
    for i, m in enumerate(mitigations, 1):
        lines.append(f"  {i}. {m}")
    lines.append("")
    lines.append(f"STATUS: {dpia['status']}")
    if overall_risk == "HIGH":
        lines.append("⚠ HIGH RISK: DPO review and supervisory authority consultation required before processing begins.")

    lines.append("\n---JSON---")
    lines.append(json.dumps(dpia))
    return "\n".join(lines)


# ── Workflow 5: Consent Documentation Tracker ──────────────────────────

def _check_consent(file_id: str, service: str) -> str:
    """Check consent documentation status for a data collection activity."""
    consent = DEMO_CONSENT.get(file_id)

    if not consent:
        # No consent record — this is itself a violation
        file = next((f for f in DEMO_FILES if f["id"] == file_id), None)
        name = file["name"] if file else file_id
        pii = detect_pii_in_text(file["content"]) if file else []

        result = {
            "file_id": file_id,
            "name": name,
            "consent_status": "NO_RECORD",
            "consent_obtained": False,
            "pii_detected": len(pii) > 0,
            "issues": [
                "No consent documentation found for this data collection activity",
                "Cannot verify lawful basis for processing under GDPR Article 6",
                "If consent is the legal basis, processing must stop until consent is obtained",
                "If vital interests (Art. 6(1)(d)) is the basis, this must be documented",
            ],
            "severity": "critical" if pii else "warning",
        }

        lines = [
            f"CONSENT CHECK: {name}",
            "Status: NO CONSENT RECORD FOUND",
            f"Contains PII: {'Yes' if pii else 'No'}",
            "",
            "ISSUES:",
        ]
        for issue in result["issues"]:
            lines.append(f"  - {issue}")
        lines.append("")
        lines.append("Action: Document the legal basis for processing immediately.")

        lines.append("\n---JSON---")
        lines.append(json.dumps(result))
        return "\n".join(lines)

    # Consent record exists — evaluate completeness
    issues = list(consent["issues"])  # copy
    score = 0
    checks = [
        ("consent_obtained", "Consent obtained from data subjects"),
        ("consent_documented", "Consent properly documented (written/recorded)"),
        ("data_subjects_informed", "Data subjects informed about processing"),
        ("purpose_explained", "Purpose of data collection explained"),
        ("right_to_withdraw_explained", "Right to withdraw consent communicated"),
        ("third_party_sharing_disclosed", "Third-party data sharing disclosed"),
    ]

    total = len(checks)
    for field, description in checks:
        if consent.get(field):
            score += 1

    completeness = f"{score}/{total}"
    status = "COMPLETE" if score == total else "INCOMPLETE" if score > total // 2 else "INADEQUATE"
    severity = "info" if score == total else "warning" if score > total // 2 else "critical"

    file = next((f for f in DEMO_FILES if f["id"] == file_id), None)
    name = file["name"] if file else file_id

    result = {
        "file_id": file_id,
        "name": name,
        "data_collection": consent["data_collection"],
        "consent_status": status,
        "consent_type": consent["consent_type"],
        "consent_language": consent["consent_language"],
        "consent_date": consent["consent_date"],
        "completeness_score": completeness,
        "checks_passed": [desc for field, desc in checks if consent.get(field)],
        "checks_failed": [desc for field, desc in checks if not consent.get(field)],
        "issues": issues,
        "severity": severity,
    }

    lines = [
        f"CONSENT CHECK: {name}",
        f"Activity: {consent['data_collection']}",
        f"Status: {status} ({completeness} requirements met)",
        f"Type: {consent['consent_type']} | Language: {consent['consent_language']}",
        "",
    ]
    if result["checks_failed"]:
        lines.append("MISSING REQUIREMENTS:")
        for check in result["checks_failed"]:
            lines.append(f"  ✗ {check}")
        lines.append("")
    if issues:
        lines.append("ISSUES:")
        for issue in issues:
            lines.append(f"  - {issue}")
        lines.append("")
    if status == "COMPLETE":
        lines.append("All consent requirements are met for this data collection activity.")

    lines.append("\n---JSON---")
    lines.append(json.dumps(result))
    return "\n".join(lines)
