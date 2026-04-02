"""
Governance rules for Amanat.

Each rule is a concrete, evaluable condition that maps scan results
(PII categories, sharing scope, file age, data type) to specific
policy violations with severity, citation, and recommended action.

The scanner produces raw signals. These rules interpret them.
"""

from datetime import datetime, timezone


# --- Rule definitions ---
# Each rule has:
#   condition: callable(file_result) -> bool
#   severity: critical / warning / info
#   violation: which policy is violated (exact title from policies.py)
#   doc_ids: which policy doc_ids to cite
#   finding: human-readable description of the problem
#   action: specific remediation step

RULES = [
    # ── SHARING + PII ──────────────────────────────────────────────
    {
        "id": "R01",
        "name": "Special category data shared publicly",
        "condition": lambda f: (
            f.get("sharing") in ("anyone_with_link",)
            and _has_category(f, "special_category_data")
        ),
        "severity": "critical",
        "violation": "GDPR Article 9 - Processing of special categories of personal data",
        "doc_ids": [2, 14],
        "finding": (
            "File contains special category data (medical, ethnic, or religious information) "
            "and is shared via public link. Anyone with the URL can access this data."
        ),
        "action": "Immediately revoke public link. Restrict access to authorized case workers only.",
    },
    {
        "id": "R02",
        "name": "Beneficiary PII shared publicly",
        "condition": lambda f: (
            f.get("sharing") == "anyone_with_link"
            and f.get("pii_detected")
        ),
        "severity": "critical",
        "violation": "ICRC Rule 6 - Data security in humanitarian contexts",
        "doc_ids": [7, 16],
        "finding": (
            "File contains personally identifiable information and is accessible to "
            "anyone with the link. In conflict-affected areas, exposed beneficiary data "
            "can lead to targeting or forced return."
        ),
        "action": "Revoke public sharing immediately. Apply need-to-know access restrictions.",
    },
    {
        "id": "R03",
        "name": "PII shared org-wide without need-to-know",
        "condition": lambda f: (
            f.get("sharing") == "org_wide"
            and f.get("pii_detected")
        ),
        "severity": "warning",
        "violation": "IASC Operational Guidance - Confidentiality principle",
        "doc_ids": [19],
        "finding": (
            "File with beneficiary data is shared with the entire organization. "
            "Not all staff have a legitimate need to access this information."
        ),
        "action": "Restrict to specific teams/individuals who need this data for their role.",
    },
    # ── BIOMETRIC DATA ─────────────────────────────────────────────
    {
        "id": "R04",
        "name": "Biometric data without restricted access",
        "condition": lambda f: (
            _has_category(f, "biometric_data")
            and f.get("sharing") != "private"
        ),
        "severity": "critical",
        "violation": "ICRC Rule 3 - Data minimisation in humanitarian action",
        "doc_ids": [6],
        "finding": (
            "Biometric data (fingerprints, iris scans) is shared beyond the data owner. "
            "Biometric data cannot be changed if compromised and requires the highest "
            "level of access control."
        ),
        "action": "Restrict access to registration officers only. Ensure storage is encrypted.",
    },
    # ── LOCATION / GPS ─────────────────────────────────────────────
    {
        "id": "R05",
        "name": "GPS coordinates in beneficiary files",
        "condition": lambda f: _has_category(f, "location_data"),
        "severity": "warning",
        "violation": "Do No Digital Harm - Humanitarian metadata risks",
        "doc_ids": [11],
        "finding": (
            "File contains GPS coordinates that could reveal beneficiary locations. "
            "Even without names, precise coordinates can enable re-identification "
            "and physical targeting."
        ),
        "action": "Remove or generalize GPS coordinates. Use area-level location references instead.",
    },
    # ── HUMANITARIAN IDENTIFIERS ───────────────────────────────────
    {
        "id": "R06",
        "name": "UNHCR case numbers exposed",
        "condition": lambda f: (
            _has_category(f, "humanitarian_identifier")
            and f.get("sharing") in ("anyone_with_link", "org_wide")
        ),
        "severity": "critical",
        "violation": "GDPR Article 5 - Principles relating to processing of personal data",
        "doc_ids": [1, 9],
        "finding": (
            "UNHCR case numbers are shared beyond authorized personnel. These are "
            "unique identifiers that link directly to individual refugee records "
            "and must be treated as sensitive personal data."
        ),
        "action": "Restrict file access. Aggregate or pseudonymize case numbers in shared reports.",
    },
    # ── DATA RETENTION ─────────────────────────────────────────────
    {
        "id": "R07",
        "name": "Beneficiary data exceeds retention period",
        "condition": lambda f: (
            f.get("pii_detected")
            and _file_age_months(f) > 12
        ),
        "severity": "warning",
        "violation": "ICRC Handbook Section 2.7 - Data retention in humanitarian action",
        "doc_ids": [17],
        "finding": (
            "File containing beneficiary PII has not been modified in over 12 months. "
            "Data should be retained only as long as necessary. If the operational "
            "purpose has ended, data must be deleted or anonymized."
        ),
        "action": "Review whether this data is still operationally needed. If not, delete or anonymize.",
    },
    {
        "id": "R08",
        "name": "Special category data exceeds retention period",
        "condition": lambda f: (
            (_has_category(f, "special_category_data") or _has_category(f, "biometric_data"))
            and _file_age_months(f) > 6
        ),
        "severity": "critical",
        "violation": "ICRC Handbook Section 2.7 - Data retention in humanitarian action",
        "doc_ids": [17, 2],
        "finding": (
            "File with medical, ethnic, or religious data has not been modified in over "
            "6 months. Special category data requires shorter retention periods and "
            "more frequent review."
        ),
        "action": "Conduct immediate retention review. Delete if no longer needed for active casework.",
    },
    # ── DATA TRANSFERS ─────────────────────────────────────────────
    {
        "id": "R09",
        "name": "Sensitive data shared with external parties",
        "condition": lambda f: (
            f.get("pii_detected")
            and f.get("sharing") == "anyone_with_link"
        ),
        "severity": "critical",
        "violation": "ICRC Rules - Article 23: Limitations on Data Transfers",
        "doc_ids": [18, 8],
        "finding": (
            "File with personal data is accessible externally via link. Any sharing "
            "of personal data with third parties requires a data protection impact "
            "assessment and must be limited to the recipient's need to know."
        ),
        "action": "Revoke external access. Conduct impact assessment before any re-sharing.",
    },
    # ── GBV / PROTECTION DATA ──────────────────────────────────────
    {
        "id": "R10",
        "name": "Protection-sensitive file with broad access",
        "condition": lambda f: (
            _is_protection_file(f)
            and f.get("sharing") != "private"
        ),
        "severity": "critical",
        "violation": "Sphere Handbook Protection Principle 1 - Sensitive information management",
        "doc_ids": [20],
        "finding": (
            "File appears to contain GBV, protection, or incident data and is shared "
            "beyond the file owner. Protection data requires the strictest access controls. "
            "Failure to restrict access may compromise the safety of survivors and staff."
        ),
        "action": "Restrict to protection team only. Ensure all access is logged.",
    },
    # ── GOVERNMENT IDs ─────────────────────────────────────────────
    {
        "id": "R11",
        "name": "Government IDs stored in cloud",
        "condition": lambda f: _has_category(f, "government_identifier"),
        "severity": "warning",
        "violation": "GDPR Article 32 - Security of processing",
        "doc_ids": [3, 16],
        "finding": (
            "File contains government-issued identification numbers (SSN, national ID). "
            "These require encryption at rest and restricted access as they enable "
            "identity theft and cannot be changed if compromised."
        ),
        "action": "Encrypt file or move to a secure, access-controlled system. Minimize copies.",
    },
    # ── DATA MINIMISATION ──────────────────────────────────────────
    {
        "id": "R12",
        "name": "Excessive PII categories in single file",
        "condition": lambda f: len(f.get("pii_categories", [])) >= 4,
        "severity": "warning",
        "violation": "GDPR Article 5 - Data minimisation",
        "doc_ids": [1, 6, 9],
        "finding": (
            "File contains 4 or more categories of personal data (names, IDs, medical, "
            "location, etc.). Collecting and storing this much data in a single file "
            "increases risk disproportionately. Data should be separated by purpose."
        ),
        "action": "Split data by purpose. Keep identifiers separate from case details.",
    },
]


# --- Helper functions for rule conditions ---

def _has_category(file_result: dict, category: str) -> bool:
    """Check if a file result includes a specific PII category."""
    return category in file_result.get("pii_categories", [])


def _file_age_months(file_result: dict) -> int:
    """Calculate how many months since the file was last modified."""
    last_mod = file_result.get("last_modified", "")
    if not last_mod:
        return 0
    try:
        # Handle both ISO format and simple date strings
        if "T" in last_mod:
            dt = datetime.fromisoformat(last_mod.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(last_mod, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0, (now.year - dt.year) * 12 + (now.month - dt.month))
    except (ValueError, TypeError):
        return 0


def _is_protection_file(file_result: dict) -> bool:
    """Check if file name or content suggests protection/GBV data."""
    name = file_result.get("name", "").lower()
    protection_keywords = ("gbv", "incident", "protection", "violence", "abuse", "safeguard")
    return any(kw in name for kw in protection_keywords)


# --- Evaluation engine ---

def evaluate_file(file_result: dict) -> list[dict]:
    """
    Evaluate a single file scan result against all governance rules.
    Returns a list of triggered violations, each with severity, citation, and action.
    """
    violations = []
    for rule in RULES:
        try:
            if rule["condition"](file_result):
                violations.append({
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "severity": rule["severity"],
                    "violation": rule["violation"],
                    "doc_ids": rule["doc_ids"],
                    "finding": rule["finding"],
                    "action": rule["action"],
                })
        except Exception:
            continue
    return violations


def evaluate_scan(scan_results: list[dict]) -> list[dict]:
    """
    Evaluate a full set of scan results. Returns a list of per-file
    violation reports, sorted by severity (critical first).
    """
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    reports = []

    for file_result in scan_results:
        violations = evaluate_file(file_result)
        if violations:
            worst = min(violations, key=lambda v: severity_order.get(v["severity"], 9))
            reports.append({
                "file_id": file_result.get("file_id", ""),
                "name": file_result.get("name", ""),
                "sharing": file_result.get("sharing", ""),
                "worst_severity": worst["severity"],
                "violation_count": len(violations),
                "violations": violations,
            })

    reports.sort(key=lambda r: severity_order.get(r["worst_severity"], 9))
    return reports


# --- Message / Channel safety rules ---

MESSAGE_RULES = [
    {
        "id": "M01",
        "name": "PII in public Slack channel",
        "condition": lambda m: (
            m.get("visibility") == "public_channel"
            and m.get("pii_detected")
        ),
        "severity": "critical",
        "finding": (
            "Beneficiary PII (names, case numbers, or identifiers) shared in a public "
            "Slack channel. All members of the workspace — and external guests if enabled "
            "— can see this information."
        ),
        "action": "Delete message immediately. Remind staff to use private channels or case management systems for PII.",
    },
    {
        "id": "M02",
        "name": "PII in channel with guest access",
        "condition": lambda m: (
            m.get("guest_access")
            and m.get("pii_detected")
        ),
        "severity": "critical",
        "finding": (
            "Sensitive data shared in a channel with external guest access. "
            "External partners, donors, or consultants can view this information "
            "without data sharing agreements in place."
        ),
        "action": "Delete message. Review guest access policies. Ensure data sharing agreements exist before granting channel access.",
    },
    {
        "id": "M03",
        "name": "Case numbers in messaging platform",
        "condition": lambda m: (
            any(t in m.get("pii_types", []) for t in ("unhcr_case_number",))
        ),
        "severity": "warning",
        "finding": (
            "UNHCR case numbers or humanitarian identifiers shared via messaging. "
            "These are unique identifiers that link to individual records and should "
            "only be transmitted through secure, authorized systems."
        ),
        "action": "Use case management system instead of chat for case-specific communications.",
    },
    {
        "id": "M04",
        "name": "GBV/protection reference in insecure channel",
        "condition": lambda m: _message_mentions_protection(m),
        "severity": "critical",
        "finding": (
            "Message references GBV, protection cases, or incident details in a "
            "non-private channel. Protection data requires the strictest confidentiality. "
            "Even vague references can compromise survivor safety."
        ),
        "action": "Delete immediately. Protection discussions must use encrypted, access-controlled channels only.",
    },
    {
        "id": "M05",
        "name": "Beneficiary data in email to external recipient",
        "condition": lambda m: (
            m.get("pii_detected")
            and _is_external_email(m)
        ),
        "severity": "critical",
        "finding": (
            "Email containing beneficiary data sent to an external recipient "
            "without verified data sharing agreement. External transfers require "
            "a DPIA and explicit data processing agreement."
        ),
        "action": "Verify data sharing agreement exists. If not, conduct DPIA before any further transfers.",
    },
]


def _message_mentions_protection(msg: dict) -> bool:
    """Check if a message references GBV/protection topics."""
    content = msg.get("content", "").lower()
    keywords = ("gbv", "gender-based violence", "protection", "incident",
                "abuse", "violence", "safeguard", "survivor")
    return any(kw in content for kw in keywords)


def _is_external_email(msg: dict) -> bool:
    """Check if a message is an email to an external recipient."""
    to = msg.get("to", "")
    from_addr = msg.get("from", "")
    if not to or not from_addr:
        return False
    # Different domain = external
    from_domain = from_addr.split("@")[-1] if "@" in from_addr else ""
    to_domain = to.split("@")[-1] if "@" in to else ""
    return from_domain != to_domain and bool(to_domain)


def evaluate_message(message: dict) -> list[dict]:
    """Evaluate a message against channel safety rules."""
    violations = []
    for rule in MESSAGE_RULES:
        try:
            if rule["condition"](message):
                violations.append({
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "severity": rule["severity"],
                    "finding": rule["finding"],
                    "action": rule["action"],
                })
        except Exception:
            continue
    return violations


def get_rules_summary() -> str:
    """
    Return a concise summary of all rules for injection into the agent's
    system prompt. This tells the LLM exactly what to look for.
    """
    lines = [
        "GOVERNANCE RULES - evaluate every scanned file against these criteria:",
        "",
    ]
    for rule in RULES:
        lines.append(
            f"[{rule['id']}] {rule['severity'].upper()}: {rule['name']} "
            f"-> Cite: {rule['violation']} -> Action: {rule['action']}"
        )
    lines.append("")
    lines.append(
        "When reporting findings, use the rule ID and cite the exact policy title. "
        "Apply ALL matching rules to each file — a single file can trigger multiple violations."
    )
    return "\n".join(lines)
