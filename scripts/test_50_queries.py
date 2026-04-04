"""
Run 50 diverse queries against the Strands agent and log results.

Usage:
    uv run python scripts/test_50_queries.py
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("OPENAI_API_BASE", "http://localhost:8080/v1")
os.environ.setdefault("OPENAI_API_KEY", "llama")

from dotenv import load_dotenv
load_dotenv()

from amanat.agent import run_agent

QUERIES = [
    # --- Scan queries (15) ---
    ("scan-01", "Scan my OneDrive for any files with PII that are publicly accessible."),
    ("scan-02", "Search Slack for any messages containing beneficiary names, case numbers, or medical information in public channels."),
    ("scan-03", "Are we leaking any data? Scan OneDrive for PII exposure and check Slack for beneficiary information in public channels."),
    ("scan-04", "scan onedrive"),
    ("scan-05", "check all my files"),
    ("scan-06", "Which of our files have exceeded their data retention period?"),
    ("scan-07", "Check if any biometric data files are publicly shared."),
    ("scan-08", "Scan Outlook for emails containing displaced person data sent to external recipients."),
    ("scan-09", "Is there any GBV data exposed on our shared drives?"),
    ("scan-10", "What files contain medical information?"),
    ("scan-11", "audit everything"),
    ("scan-12", "is our data safe?"),
    ("scan-13", "any problems?"),
    ("scan-14", "Show me all files with case numbers in them."),
    ("scan-15", "Check the sharing settings on the biometric enrollment log."),

    # --- Policy / RAG queries (10) ---
    ("rag-01", "What does the ICRC Handbook say about sharing displaced person data with host governments? Do we need consent?"),
    ("rag-02", "What does GDPR Article 9 say about processing medical and ethnic data?"),
    ("rag-03", "What are the rules for sharing displaced person data with donors like the Ambara Development Fund?"),
    ("rag-04", "Under what circumstances can we process biometric data according to humanitarian standards?"),
    ("rag-05", "What retention periods apply to special category data under ICRC guidelines?"),
    ("rag-06", "When is consent not required for processing personal data in a humanitarian emergency?"),
    ("rag-07", "What security measures does the ICRC Handbook require for storing beneficiary data?"),
    ("rag-08", "Can we transfer beneficiary data to another country? What does the IASC guidance say?"),
    ("rag-09", "What are the Sphere Standards requirements for handling sensitive information?"),
    ("rag-10", "What constitutes a data breach under humanitarian data protection standards?"),

    # --- Compliance / DPIA queries (8) ---
    ("comp-01", "Generate a DPIA for our biometric enrollment program that collects fingerprints and iris scans at Kanbaloh for aid distribution."),
    ("comp-02", "Check the consent documentation status for our displaced persons registry and biometric enrollment log."),
    ("comp-03", "We want to start collecting GPS coordinates of beneficiary shelters. Do we need a DPIA?"),
    ("comp-04", "Generate a DPIA for sharing our case files with the Ambara Development Fund for their quarterly audit."),
    ("comp-05", "Are we compliant with ICRC data protection rules for how we store protection assessment files?"),
    ("comp-06", "What legal basis can we use for processing refugee medical records?"),
    ("comp-07", "We need to conduct a data protection audit before the donor visit. What should we check?"),
    ("comp-08", "Is our consent process for the displaced persons registry compliant?"),

    # --- Remediation queries (7) ---
    ("rem-01", "Those GBV files should not be publicly shared. Revoke access immediately."),
    ("rem-02", "Create a redacted version of the displaced persons registry for the donor audit."),
    ("rem-03", "Download all sensitive files locally."),
    ("rem-04", "Lock down all publicly shared files containing PII."),
    ("rem-05", "Post a data protection alert to the #field-updates channel warning about PII in messages."),
    ("rem-06", "The biometric enrollment log has been shared org-wide. Restrict it to registration officers only."),
    ("rem-07", "Remove the case file from cloud storage after downloading it locally."),

    # --- Edge cases / conversational (10) ---
    ("edge-01", "Hello, what can you help me with?"),
    ("edge-02", "What is amanat?"),
    ("edge-03", "Who are you?"),
    ("edge-04", "Can you explain what PII means in a humanitarian context?"),
    ("edge-05", "What services are you connected to?"),
    ("edge-06", "How does Token Vault work?"),
    ("edge-07", "What would happen if our beneficiary data was leaked?"),
    ("edge-08", "Tell me about the Rohingya data protection incident."),
    ("edge-09", "What is the difference between data governance and data sovereignty?"),
    ("edge-10", "Thank you, that was helpful."),
]


async def main():
    log_path = Path("test_results_50.jsonl")
    summary_path = Path("test_results_50_summary.txt")

    results = []

    print(f"Running {len(QUERIES)} queries...\n")

    for i, (label, query) in enumerate(QUERIES):
        t0 = time.time()
        try:
            answer = await run_agent(query)
            elapsed = time.time() - t0
            status = "OK" if len(answer) > 50 else "SHORT"
        except Exception as e:
            answer = f"ERROR: {e}"
            elapsed = time.time() - t0
            status = "FAIL"

        entry = {
            "id": label,
            "query": query,
            "status": status,
            "time_s": round(elapsed, 1),
            "chars": len(answer),
            "answer_preview": answer[:200],
        }
        results.append(entry)

        # Write to JSONL incrementally
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        marker = {"OK": "+", "SHORT": "~", "FAIL": "X"}[status]
        print(f"  [{marker}] {i+1:2d}/50 {label:10s} {elapsed:5.1f}s {len(answer):5d}ch | {answer[:80]}")

    # Summary
    ok = sum(1 for r in results if r["status"] == "OK")
    short = sum(1 for r in results if r["status"] == "SHORT")
    fail = sum(1 for r in results if r["status"] == "FAIL")
    total_time = sum(r["time_s"] for r in results)
    avg_time = total_time / len(results)
    avg_chars = sum(r["chars"] for r in results) / len(results)

    summary = f"""
AMANAT AGENT TEST RESULTS — {len(QUERIES)} QUERIES
{'=' * 60}
Pass:  {ok}/{len(QUERIES)}
Short: {short}/{len(QUERIES)}
Fail:  {fail}/{len(QUERIES)}

Total time: {total_time:.0f}s
Avg time:   {avg_time:.1f}s per query
Avg length: {avg_chars:.0f} chars per answer

{'=' * 60}
CATEGORY BREAKDOWN:
  Scan queries (15):      {sum(1 for r in results if r['id'].startswith('scan') and r['status']=='OK')}/15 OK
  Policy/RAG queries (10): {sum(1 for r in results if r['id'].startswith('rag') and r['status']=='OK')}/10 OK
  Compliance queries (8):  {sum(1 for r in results if r['id'].startswith('comp') and r['status']=='OK')}/8 OK
  Remediation queries (7): {sum(1 for r in results if r['id'].startswith('rem') and r['status']=='OK')}/7 OK
  Edge cases (10):         {sum(1 for r in results if r['id'].startswith('edge') and r['status']=='OK')}/10 OK

{'=' * 60}
FAILURES/ISSUES:
"""
    for r in results:
        if r["status"] != "OK":
            summary += f"  [{r['status']}] {r['id']}: {r['query'][:60]}\n"
            summary += f"         {r['answer_preview'][:100]}\n"

    if all(r["status"] == "OK" for r in results):
        summary += "  None\n"

    summary += f"""
{'=' * 60}
PER-QUERY RESULTS:
"""
    for r in results:
        summary += f"  {r['status']:5s} {r['time_s']:5.1f}s {r['chars']:5d}ch | {r['id']:10s} | {r['query'][:50]}\n"

    with open(summary_path, "w") as f:
        f.write(summary)

    print(summary)


if __name__ == "__main__":
    # Clear previous log
    Path("test_results_50.jsonl").unlink(missing_ok=True)
    asyncio.run(main())
