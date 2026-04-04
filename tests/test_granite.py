"""
End-to-end tests with real Granite 4 Micro via Strands Agents SDK.

Tests the full agent loop: user query → Strands Agent →
Granite tool calls → tool execution → Granite synthesis.
Requires llama-server running locally with Granite 4 Micro GGUF.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from amanat.agent import run_agent


async def run_test(label: str, query: str):
    """Run a single agent test, print results."""
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"QUERY: {query}")
    print(f"{'='*60}")

    try:
        response = await run_agent(query)
        print(f"\nGRANITE RESPONSE ({len(response)} chars):")
        print("-" * 40)
        print(response[:2000])
        if len(response) > 2000:
            print(f"... ({len(response) - 2000} more chars)")
        print("-" * 40)
        return label, "PASS"
    except Exception as e:
        print(f"\nERROR: {e}")
        return label, f"FAIL: {e}"


async def main():
    tests = [
        ("File scan with violations",
         "Scan my OneDrive files for data protection issues."),

        ("Redact file for safe sharing",
         "Redact the Upheaval displaced registry (doc-001) so I can share it with the Hateno Development Fund."),

        ("Retention enforcement",
         "Check which files have exceeded their data retention period."),

        ("Insecure channel scan",
         "Scan our Slack channels for any displaced person data being shared insecurely."),

        ("DPIA generation",
         "Generate a DPIA for our biometric enrollment program that collects "
         "fingerprints and iris scans for supply distribution verification at Kanbaloh."),

        ("Consent documentation check",
         "Check the consent status for doc-001 and doc-005."),

        ("Multi-step: safe sharing workflow",
         "I need to share the Upheaval displaced registry (doc-001) with the Hateno Development Fund. "
         "Make sure it is safe to share first."),
    ]

    # Run specific test if index provided
    if len(sys.argv) > 1:
        idx = int(sys.argv[1])
        tests = [tests[idx]]

    results = []
    for label, query in tests:
        result = await run_test(label, query)
        results.append(result)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for label, status in results:
        print(f"  [{status}] {label}")


if __name__ == "__main__":
    asyncio.run(main())
