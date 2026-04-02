"""
Programmatic tests for all 5 Amanat workflows.

Runs without Granite, without Ollama, without live APIs.
Tests the tool functions directly against demo data.
"""

import json
import pytest

from amanat.tools.scanner import execute_tool, detect_pii_in_text, redact_pii_in_text


# ── Helper to parse tool output ──────────────────────────────────────────

def parse_tool_output(raw: str) -> tuple[str, dict | None]:
    """Split tool output into text report and JSON data."""
    if "---JSON---" in raw:
        text, json_part = raw.split("---JSON---", 1)
        return text.strip(), json.loads(json_part.strip())
    try:
        return "", json.loads(raw)
    except json.JSONDecodeError:
        return raw, None


# ═══════════════════════════════════════════════════════════════════════
# Workflow 1: Safe Data Sharing / Redaction
# ═══════════════════════════════════════════════════════════════════════

class TestRedaction:
    def test_redact_removes_all_pii_types(self):
        """Redacting the case file should remove names, phones, IDs, medical, GPS, etc."""
        raw = execute_tool("redact_file", {"file_id": "doc-001", "service": "onedrive"})
        text, data = parse_tool_output(raw)

        assert data["status"] == "success"
        assert data["total_pii_redacted"] > 0

        # The redacted content should not contain original PII
        redacted = data["redacted_content"]
        assert "Rozel Tidecrest" not in redacted
        assert "100-26C00891" not in redacted
        assert "+471-55-555-1234" not in redacted
        assert "47.3821" not in redacted
        assert "PTSD" not in redacted

        # But should contain redaction labels
        assert "[NAME REDACTED]" in redacted
        assert "[CASE# REDACTED]" in redacted
        assert "[PHONE REDACTED]" in redacted
        assert "[GPS REDACTED]" in redacted
        assert "[MEDICAL REDACTED]" in redacted

    def test_redact_preserves_structure(self):
        """Redacted output should keep non-PII content intact."""
        raw = execute_tool("redact_file", {"file_id": "doc-001", "service": "onedrive"})
        _, data = parse_tool_output(raw)

        redacted = data["redacted_content"]
        # Structure markers should survive (note: some field labels may be
        # partially caught by the name pattern when adjacent to PII)
        assert "Registry" in redacted
        assert "Status:" in redacted
        assert "DOB:" in redacted

    def test_redact_file_not_found(self):
        """Redacting a nonexistent file returns an error."""
        raw = execute_tool("redact_file", {"file_id": "nonexistent", "service": "onedrive"})
        _, data = parse_tool_output(raw)
        assert "error" in data

    def test_redact_low_pii_file(self):
        """Donor report has less PII — redaction should still work."""
        raw = execute_tool("redact_file", {"file_id": "doc-002", "service": "onedrive"})
        _, data = parse_tool_output(raw)

        assert data["status"] == "success"
        # Should redact the email and names
        assert "paya.kakariko@hrc-hyrule.org" not in data["redacted_content"]

    def test_redact_function_directly(self):
        """Test the redact_pii_in_text function independently."""
        text = "Contact Rozel Tidecrest at +471-55-555-1234. Case: 100-26C00891"
        redacted, redactions = redact_pii_in_text(text)

        assert "Rozel Tidecrest" not in redacted
        assert "+471-55-555-1234" not in redacted
        assert "100-26C00891" not in redacted
        assert len(redactions) > 0

    def test_redact_idempotent(self):
        """Redacting already-redacted text should produce no new redactions."""
        text = "Name: Rozel Tidecrest, Phone: +471-55-555-1234"
        redacted_once, _ = redact_pii_in_text(text)
        redacted_twice, redactions_2 = redact_pii_in_text(redacted_once)

        # The labels themselves should not trigger PII detection
        assert "[NAME REDACTED]" in redacted_twice
        assert "[PHONE REDACTED]" in redacted_twice
        # No new name/phone redactions on the second pass
        name_redactions = [r for r in redactions_2 if r["type"] in ("name", "phone_number")]
        assert len(name_redactions) == 0


# ═══════════════════════════════════════════════════════════════════════
# Workflow 2: Retention Enforcement
# ═══════════════════════════════════════════════════════════════════════

class TestRetention:
    def test_retention_scan_finds_old_files(self):
        """Biometric log (doc-005) is from Jan 2026 — should trigger retention rules."""
        raw = execute_tool("retention_scan", {"service": "onedrive"})
        text, data = parse_tool_output(raw)

        assert data["files_checked"] == 5
        # At least the biometric file should be flagged (special category, >2 months old)
        flagged_ids = [r["file_id"] for r in data["results"]]
        assert "doc-005" in flagged_ids, "Biometric enrollment log should be flagged for retention"

    def test_retention_violations_have_correct_rule_ids(self):
        """Retention violations should reference R07 or R08."""
        raw = execute_tool("retention_scan", {"service": "onedrive"})
        _, data = parse_tool_output(raw)

        for result in data["results"]:
            for v in result["violations"]:
                assert v["rule_id"] in ("R07", "R08"), f"Unexpected rule: {v['rule_id']}"

    def test_retention_text_output_readable(self):
        """Text report should mention file names and ages."""
        raw = execute_tool("retention_scan", {"service": "onedrive"})
        text, _ = parse_tool_output(raw)

        assert "Retention scan complete" in text
        assert "months ago" in text or "days ago" in text


# ═══════════════════════════════════════════════════════════════════════
# Workflow 3: Insecure Channel Detection
# ═══════════════════════════════════════════════════════════════════════

class TestInsecureChannels:
    def test_slack_scan_finds_pii_in_public_channels(self):
        """Slack messages with beneficiary names in public channels should be flagged."""
        raw = execute_tool("search_messages", {"service": "slack", "query": "Rozel"})
        text, data = parse_tool_output(raw)

        assert data["messages_found"] > 0
        assert data["messages_with_violations"] > 0

    def test_slack_pii_triggers_M01(self):
        """PII in public channel should trigger rule M01."""
        raw = execute_tool("search_messages", {"service": "slack", "query": "Rozel"})
        _, data = parse_tool_output(raw)

        violations = []
        for msg in data["results"]:
            violations.extend(msg.get("violations", []))

        rule_ids = [v["rule_id"] for v in violations]
        assert "M01" in rule_ids, "PII in public channel should trigger M01"

    def test_guest_channel_triggers_M02(self):
        """PII in channel with guest access should trigger M02."""
        raw = execute_tool("search_messages", {"service": "slack", "query": "audit"})
        _, data = parse_tool_output(raw)

        violations = []
        for msg in data["results"]:
            violations.extend(msg.get("violations", []))

        rule_ids = [v["rule_id"] for v in violations]
        assert "M02" in rule_ids, "Guest-accessible channel should trigger M02"

    def test_gbv_reference_triggers_M04(self):
        """GBV reference in non-private channel should trigger M04."""
        raw = execute_tool("search_messages", {"service": "slack", "query": "GBV"})
        _, data = parse_tool_output(raw)

        violations = []
        for msg in data["results"]:
            violations.extend(msg.get("violations", []))

        rule_ids = [v["rule_id"] for v in violations]
        assert "M04" in rule_ids, "GBV reference should trigger M04"

    def test_gmail_external_transfer_triggers_M05(self):
        """Email with PII to external recipient should trigger M05."""
        raw = execute_tool("search_messages", {"service": "gmail", "query": "beneficiary"})
        _, data = parse_tool_output(raw)

        violations = []
        for msg in data["results"]:
            violations.extend(msg.get("violations", []))

        rule_ids = [v["rule_id"] for v in violations]
        assert "M05" in rule_ids, "External email with PII should trigger M05"

    def test_text_output_shows_violations(self):
        """Text report should clearly show violations per message."""
        raw = execute_tool("search_messages", {"service": "slack", "query": "Rozel"})
        text, _ = parse_tool_output(raw)

        assert "CRITICAL" in text
        assert "MESSAGE in" in text


# ═══════════════════════════════════════════════════════════════════════
# Workflow 4: DPIA Generator
# ═══════════════════════════════════════════════════════════════════════

class TestDPIA:
    def test_dpia_high_risk_biometric(self):
        """Biometric data processing should generate a HIGH risk DPIA."""
        raw = execute_tool("generate_dpia", {
            "activity": "Biometric enrollment for aid distribution",
            "data_types": ["biometric_data", "personal_identifier"],
            "purpose": "Verify beneficiary identity for food distribution",
        })
        text, data = parse_tool_output(raw)

        assert data["sections"]["3_risk_assessment"]["overall_risk_level"] == "HIGH"
        assert "biometric" in text.lower()
        assert "DPO review" in text

    def test_dpia_medium_risk_identifiers(self):
        """Humanitarian identifiers should generate MEDIUM risk."""
        raw = execute_tool("generate_dpia", {
            "activity": "Case number tracking",
            "data_types": ["humanitarian_identifier"],
            "purpose": "Track beneficiary case progress",
        })
        _, data = parse_tool_output(raw)

        assert data["sections"]["3_risk_assessment"]["overall_risk_level"] == "MEDIUM"

    def test_dpia_low_risk_basic(self):
        """Basic personal data should generate LOW risk."""
        raw = execute_tool("generate_dpia", {
            "activity": "Staff contact directory",
            "data_types": ["personal_identifier"],
            "purpose": "Internal staff communications",
        })
        _, data = parse_tool_output(raw)

        assert data["sections"]["3_risk_assessment"]["overall_risk_level"] == "LOW"

    def test_dpia_has_mitigations(self):
        """DPIA should include specific mitigation measures."""
        raw = execute_tool("generate_dpia", {
            "activity": "Medical screening data collection",
            "data_types": ["special_category_data", "biometric_data", "location_data"],
            "purpose": "Health screening at registration",
        })
        _, data = parse_tool_output(raw)

        mitigations = data["sections"]["4_mitigation_measures"]
        assert len(mitigations) >= 5, "High-risk DPIA should have multiple mitigations"

        # Should include biometric-specific measures
        mitigation_text = " ".join(mitigations).lower()
        assert "encrypt" in mitigation_text
        assert "consent" in mitigation_text
        assert "gps" in mitigation_text or "location" in mitigation_text

    def test_dpia_legal_basis_includes_vital_interests(self):
        """Humanitarian DPIA should cite vital interests as legal basis."""
        raw = execute_tool("generate_dpia", {
            "activity": "Emergency medical registration",
            "data_types": ["special_category_data"],
            "purpose": "Emergency medical care",
        })
        _, data = parse_tool_output(raw)

        legal = data["sections"]["2_necessity_and_proportionality"]["legal_basis"]
        legal_text = " ".join(legal)
        assert "vital interests" in legal_text
        assert "Article 9(2)(c)" in legal_text  # special category exemption

    def test_dpia_structure_complete(self):
        """Generated DPIA should have all required sections."""
        raw = execute_tool("generate_dpia", {
            "activity": "Test activity",
            "data_types": ["personal_identifier"],
            "purpose": "Testing",
        })
        _, data = parse_tool_output(raw)

        assert "title" in data
        assert "status" in data
        required_sections = [
            "1_description",
            "2_necessity_and_proportionality",
            "3_risk_assessment",
            "4_mitigation_measures",
            "5_consultation",
        ]
        for section in required_sections:
            assert section in data["sections"], f"Missing DPIA section: {section}"


# ═══════════════════════════════════════════════════════════════════════
# Workflow 5: Consent Documentation Tracker
# ═══════════════════════════════════════════════════════════════════════

class TestConsent:
    def test_consent_no_record_is_critical(self):
        """File with PII but no consent record should be critical."""
        raw = execute_tool("check_consent", {"file_id": "doc-002", "service": "onedrive"})
        text, data = parse_tool_output(raw)

        assert data["consent_status"] == "NO_RECORD"
        assert data["severity"] == "critical"
        assert "No consent documentation" in text

    def test_consent_complete_gbv(self):
        """GBV file (doc-004) has complete consent — should pass all checks."""
        raw = execute_tool("check_consent", {"file_id": "doc-004", "service": "onedrive"})
        _, data = parse_tool_output(raw)

        assert data["consent_status"] == "COMPLETE"
        assert data["severity"] == "info"
        assert data["completeness_score"] == "6/6"
        assert len(data["issues"]) == 0

    def test_consent_incomplete_case_file(self):
        """Case file (doc-001) has verbal consent only — should be incomplete."""
        raw = execute_tool("check_consent", {"file_id": "doc-001", "service": "onedrive"})
        text, data = parse_tool_output(raw)

        assert data["consent_status"] in ("INCOMPLETE", "INADEQUATE")
        assert data["consent_type"] == "verbal"
        assert len(data["issues"]) > 0
        assert len(data["checks_failed"]) > 0
        assert "Right to withdraw" in " ".join(data["checks_failed"])

    def test_consent_biometric_gaps(self):
        """Biometric enrollment (doc-005) should flag missing withdrawal & sharing disclosure."""
        raw = execute_tool("check_consent", {"file_id": "doc-005", "service": "onedrive"})
        _, data = parse_tool_output(raw)

        assert data["consent_status"] in ("INCOMPLETE", "INADEQUATE")
        assert "biometric" in data["data_collection"].lower()
        assert len(data["checks_failed"]) >= 2

        failed_text = " ".join(data["checks_failed"]).lower()
        assert "withdraw" in failed_text
        assert "third-party" in failed_text or "sharing" in failed_text

    def test_consent_no_record_staff_file(self):
        """Staff contact file (doc-003) with no consent record."""
        raw = execute_tool("check_consent", {"file_id": "doc-003", "service": "onedrive"})
        _, data = parse_tool_output(raw)

        assert data["consent_status"] == "NO_RECORD"
        assert data["pii_detected"]  # file has PII

    def test_consent_text_output_readable(self):
        """Text output should be human-readable with clear status."""
        raw = execute_tool("check_consent", {"file_id": "doc-001", "service": "onedrive"})
        text, _ = parse_tool_output(raw)

        assert "CONSENT CHECK" in text
        assert "verbal" in text.lower()
        assert "MISSING REQUIREMENTS" in text or "ISSUES" in text


# ═══════════════════════════════════════════════════════════════════════
# Existing workflow: File scanning + governance rules
# ═══════════════════════════════════════════════════════════════════════

class TestExistingScan:
    def test_scan_files_produces_violations(self):
        """Full scan should find violations in demo files."""
        raw = execute_tool("scan_files", {"service": "onedrive"})
        text, data = parse_tool_output(raw)

        assert data["files_scanned"] == 5
        assert data["files_with_violations"] > 0

    def test_case_file_has_critical_violations(self):
        """Syria case file (public + special category data) should be critical."""
        raw = execute_tool("scan_files", {"service": "onedrive"})
        _, data = parse_tool_output(raw)

        case_file = next(r for r in data["results"] if r["file_id"] == "doc-001")
        assert case_file["risk_level"] == "critical"
        assert len(case_file.get("violations", [])) > 0

    def test_detect_pii_categories(self):
        """PII detection should find multiple categories in case file."""
        raw = execute_tool("detect_pii", {"file_id": "doc-001", "service": "onedrive"})
        _, data = parse_tool_output(raw)

        assert data["total_pii_types"] >= 5
        assert data["has_special_category_data"]


# ═══════════════════════════════════════════════════════════════════════
# Integration: tool execution routing
# ═══════════════════════════════════════════════════════════════════════

class TestToolRouting:
    def test_unknown_tool_returns_error(self):
        raw = execute_tool("nonexistent_tool", {})
        data = json.loads(raw)
        assert "error" in data

    def test_all_new_tools_are_routable(self):
        """All new tools should be callable through execute_tool."""
        tools = [
            ("redact_file", {"file_id": "doc-001", "service": "onedrive"}),
            ("retention_scan", {"service": "onedrive"}),
            ("generate_dpia", {"activity": "test", "data_types": [], "purpose": "test"}),
            ("check_consent", {"file_id": "doc-001", "service": "onedrive"}),
        ]
        for tool_name, args in tools:
            raw = execute_tool(tool_name, args)
            assert "error" not in raw.lower() or "not found" not in raw.lower(), \
                f"Tool {tool_name} returned error: {raw[:100]}"
