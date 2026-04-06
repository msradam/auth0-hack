"""
Run 40 queries against the Amanat agent in demo mode and log results.

Tests tool calling, policy RAG, compliance, remediation, and edge cases.
Requires llama-server running locally with Granite 4 Micro.

Usage:
    uv run python scripts/test_40_queries.py
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("OPENAI_API_BASE", "http://localhost:8080/v1")
os.environ.setdefault("OPENAI_API_KEY", "llama")

from dotenv import load_dotenv
load_dotenv()

from amanat.agent import run_agent

QUERIES = [
    # --- Scan: OneDrive (8) ---
    ("scan-onedrive-01", "Scan my OneDrive for any files with PII that are publicly accessible."),
    ("scan-onedrive-02", "Check if any biometric data files are publicly shared."),
    ("scan-onedrive-03", "Is there any GBV data exposed on our shared drives?"),
    ("scan-onedrive-04", "What files contain medical information?"),
    ("scan-onedrive-05", "Show me all files with case numbers in them."),
    ("scan-onedrive-06", "Check the sharing settings on the biometric enrollment log."),
    ("scan-onedrive-07", "scan onedrive"),
    ("scan-onedrive-08", "check all my files"),

    # --- Scan: Slack (4) ---
    ("scan-slack-01", "Search Slack for any messages containing beneficiary names, case numbers, or medical information in public channels."),
    ("scan-slack-02", "Check Slack channels for leaked displaced person data."),
    ("scan-slack-03", "Are there GPS coordinates being shared in any public channels?"),
    ("scan-slack-04", "scan slack"),

    # --- Scan: Outlook (3) ---
    ("scan-outlook-01", "Search Outlook for emails containing displaced person data sent to external recipients."),
    ("scan-outlook-02", "Check if any case numbers were sent by email to external partners."),
    ("scan-outlook-03", "scan outlook"),

    # --- Policy / RAG (8) ---
    ("rag-01", "What does the ICRC Handbook say about sharing displaced person data with host governments?"),
    ("rag-02", "What does GDPR Article 9 say about processing medical and ethnic data?"),
    ("rag-03", "What are the rules for sharing displaced person data with donors?"),
    ("rag-04", "Under what circumstances can we process biometric data according to humanitarian standards?"),
    ("rag-05", "What retention periods apply to special category data under ICRC guidelines?"),
    ("rag-06", "When is consent not required for processing personal data in a humanitarian emergency?"),
    ("rag-07", "What security measures does the ICRC Handbook require for storing beneficiary data?"),
    ("rag-08", "Can we transfer beneficiary data to another country?"),

    # --- Compliance (5) ---
    ("comp-01", "Generate a DPIA for our biometric enrollment program that collects fingerprints and iris scans for aid distribution."),
    ("comp-02", "Check the consent documentation status for our displaced persons registry."),
    ("comp-03", "We want to start collecting GPS coordinates of beneficiary shelters. Do we need a DPIA?"),
    ("comp-04", "Are we compliant with ICRC data protection rules for how we store protection files?"),
    ("comp-05", "Is our consent process for the displaced persons registry compliant?"),

    # --- Remediation (5) ---
    ("rem-01", "Revoke public sharing on the GBV incident reports."),
    ("rem-02", "Redact all PII from the Cataclysm Displaced Registry and upload a clean copy."),
    ("rem-03", "Post a data protection alert to the field-updates channel about PII in messages."),
    ("rem-04", "Send an email alert to the sender about the policy violation."),
    ("rem-05", "Which files have exceeded their data retention period?"),

    # --- Edge cases (7) ---
    ("edge-01", "What can you help me with?"),
    ("edge-02", "What services are you connected to?"),
    ("edge-03", "Can you explain what PII means in a humanitarian context?"),
    ("edge-04", "What would happen if our beneficiary data was leaked?"),
    ("edge-05", "Tell me about the Rohingya data protection incident."),
    ("edge-06", "What is the difference between data governance and data protection?"),
    ("edge-07", "Thank you, that was helpful."),
]


def classify_result(label: str, answer: str) -> str:
    """Classify a query result as PASS, PARTIAL, or FAIL."""
    if answer.startswith("ERROR:"):
        return "FAIL"
    if len(answer) < 30:
        return "FAIL"

    a = answer.lower()

    if label.startswith("scan-onedrive"):
        return "PASS" if any(w in a for w in ["scan", "file", "pii", "found", "violation", "shared"]) else "PARTIAL"
    elif label.startswith("scan-slack"):
        return "PASS" if any(w in a for w in ["slack", "channel", "message", "pii", "found"]) else "PARTIAL"
    elif label.startswith("scan-outlook"):
        return "PASS" if any(w in a for w in ["outlook", "email", "mail", "found", "sent"]) else "PARTIAL"
    elif label.startswith("rag"):
        return "PASS" if any(w in a for w in ["icrc", "gdpr", "handbook", "article", "consent", "data protection"]) else "PARTIAL"
    elif label.startswith("comp"):
        return "PASS" if any(w in a for w in ["dpia", "consent", "compliance", "assessment", "retention"]) else "PARTIAL"
    elif label.startswith("rem"):
        return "PASS" if any(w in a for w in ["revoke", "redact", "alert", "email", "retention", "notify"]) else "PARTIAL"
    elif label.startswith("edge"):
        return "PASS" if len(answer) > 50 else "PARTIAL"

    return "PARTIAL"


async def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = Path(f"test_results_{timestamp}.jsonl")
    summary_path = Path(f"test_results_{timestamp}_summary.txt")

    results = []
    total = len(QUERIES)

    print(f"=== Amanat Agent Test Suite ({total} queries) ===")
    print(f"Log: {log_path}\n")

    for i, (label, query) in enumerate(QUERIES):
        t0 = time.time()
        try:
            answer = await run_agent(query)
            elapsed = time.time() - t0
        except Exception as e:
            answer = f"ERROR: {e}"
            elapsed = time.time() - t0

        status = classify_result(label, answer)

        entry = {
            "id": label,
            "query": query,
            "status": status,
            "time_s": round(elapsed, 1),
            "answer_length": len(answer),
            "answer": answer[:500],
        }
        results.append(entry)

        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        marker = {"PASS": "+", "PARTIAL": "~", "FAIL": "X"}[status]
        print(f"  [{marker}] {i+1:2d}/{total} {label:20s} {elapsed:5.1f}s | {answer[:80]}")

    # Summary
    passed = sum(1 for r in results if r["status"] == "PASS")
    partial = sum(1 for r in results if r["status"] == "PARTIAL")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    total_time = sum(r["time_s"] for r in results)

    categories = {}
    for r in results:
        cat = r["id"].rsplit("-", 1)[0]
        if cat not in categories:
            categories[cat] = {"pass": 0, "partial": 0, "fail": 0, "total": 0}
        categories[cat]["total"] += 1
        categories[cat][r["status"].lower()] += 1

    summary = f"""Amanat Agent Test Results
========================
Date: {datetime.now(timezone.utc).isoformat()}
Total: {total} queries
Pass: {passed}/{total} ({100*passed/total:.0f}%)
Partial: {partial}/{total}
Fail: {failed}/{total}
Total time: {total_time:.0f}s
Avg time: {total_time/total:.1f}s per query

By category:
"""
    for cat, counts in sorted(categories.items()):
        summary += f"  {cat:20s} {counts['pass']}/{counts['total']} pass"
        if counts["partial"]:
            summary += f", {counts['partial']} partial"
        if counts["fail"]:
            summary += f", {counts['fail']} fail"
        summary += "\n"

    if failed > 0:
        summary += "\nFailed queries:\n"
        for r in results:
            if r["status"] == "FAIL":
                summary += f"  {r['id']}: {r['answer'][:100]}\n"

    print(f"\n{summary}")
    with open(summary_path, "w") as f:
        f.write(summary)

    print(f"Results: {log_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    asyncio.run(main())
