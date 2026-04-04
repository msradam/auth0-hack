#!/usr/bin/env python3
"""Decrypt and print an encrypted Amanat audit log file.

Usage:
    uv run python scripts/read_audit_log.py audit-logs/<session_id>.jsonl.enc

Requires the CHAINLIT_AUTH_SECRET env var to match the one used when the
log was written. If unset, falls back to "dev-fallback-secret".
"""

import json
import sys
from pathlib import Path

# Add project root to path so we can import from app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import decrypt_audit_log


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/read_audit_log.py <path-to-encrypted-log>")
        sys.exit(1)

    log_path = Path(sys.argv[1])
    if not log_path.exists():
        print(f"File not found: {log_path}")
        sys.exit(1)

    entries = decrypt_audit_log(log_path)
    for entry in entries:
        print(json.dumps(entry, indent=2))


if __name__ == "__main__":
    main()
