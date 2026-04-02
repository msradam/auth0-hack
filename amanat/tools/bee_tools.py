"""
BeeAI Framework tool definitions for Amanat.

Each tool is a thin wrapper around the scanner/onedrive implementations,
exposed via the @tool decorator for BeeAI's agent loop.
"""

from beeai_framework.tools import StringToolOutput, tool

from amanat.tools.scanner import execute_tool


def _run(name: str, **kwargs) -> StringToolOutput:
    """Execute a tool and return the text portion (strip JSON for LLM)."""
    result = execute_tool(name, kwargs, access_token=_get_token())
    # Strip JSON blob — LLM gets text only
    text = result.split("\n---JSON---")[0] if "---JSON---" in result else result
    return StringToolOutput(text)


# Access token is set at runtime by the Chainlit app or test harness
_access_token: str | None = None


def set_access_token(token: str | None):
    """Set the access token for live API calls."""
    global _access_token
    _access_token = token


def _get_token() -> str | None:
    return _access_token


# ── Scanning tools ─────────────────────────────────────────────────────

@tool
def scan_files(service: str, query: str = "") -> StringToolOutput:
    """Scan files and channels for sensitive data exposure, oversharing, and policy violations.
    For OneDrive files: returns file metadata, sharing settings, PII types, and governance violations.
    For Slack channels: scans public channels for PII leaks in messages.
    For Outlook: use search_messages instead.

    Args:
        service: Which service to scan — "onedrive" or "slack".
        query: Optional search query to filter files (e.g. "case files", "displaced").
    """
    return _run("scan_files", service=service, query=query or None)


@tool
def check_sharing(file_id: str, service: str) -> StringToolOutput:
    """Check the sharing and permission settings for a specific file.
    Returns who has access, sharing scope (public, org-wide, restricted),
    and whether the access level is appropriate for the content sensitivity.

    Args:
        file_id: The file or folder identifier to check.
        service: Which service the file is on — "onedrive".
    """
    return _run("check_sharing", file_id=file_id, service=service)


@tool
def detect_pii(file_id: str, service: str) -> StringToolOutput:
    """Analyze file content for personally identifiable information (PII)
    and sensitive humanitarian data. Detects names, ID numbers, locations,
    medical information, biometric references, and ethnic/religious identifiers.

    Args:
        file_id: The file to analyze for PII.
        service: Which service the file is on — "onedrive".
    """
    return _run("detect_pii", file_id=file_id, service=service)


@tool
def search_messages(service: str, query: str) -> StringToolOutput:
    """Search messaging services for sensitive content that may violate data protection policies.
    Use this to search Slack messages or Outlook emails for PII leaks — names, case numbers,
    medical details, GPS coordinates, or ethnic identifiers shared insecurely.

    Args:
        service: Which messaging service to search — "slack" or "outlook".
        query: Search query (e.g. "displaced", "case", "medical", "GBV").
    """
    return _run("search_messages", service=service, query=query)


# ── Remediation tools ──────────────────────────────────────────────────

@tool
def revoke_sharing(file_id: str, service: str) -> StringToolOutput:
    """REMEDIATION: Revoke public or link-based sharing on a file.
    Removes 'anyone with link' and domain-wide permissions, restricting
    access to only explicitly shared users.

    Args:
        file_id: The file ID to revoke sharing on.
        service: The service the file is on — "onedrive".
    """
    return _run("revoke_sharing", file_id=file_id, service=service)


@tool
def download_file(file_id: str, service: str) -> StringToolOutput:
    """REMEDIATION: Download a file from a connected service to local storage.
    Use this to preserve a copy before deleting from the cloud.

    Args:
        file_id: The file ID to download.
        service: The service to download from — "onedrive".
    """
    return _run("download_file", file_id=file_id, service=service)


@tool
def delete_file(file_id: str, service: str) -> StringToolOutput:
    """REMEDIATION: Move a file to trash on the connected service.
    The file can be recovered within 30 days.

    Args:
        file_id: The file ID to delete/trash.
        service: The service to delete from — "onedrive".
    """
    return _run("delete_file", file_id=file_id, service=service)


# ── New workflow tools ─────────────────────────────────────────────────

@tool
def redact_file(file_id: str, service: str) -> StringToolOutput:
    """SAFE SHARING: Create a redacted copy of a file with all PII removed.
    Replaces names, phone numbers, case numbers, medical info, GPS coordinates,
    and other sensitive data with safe labels like [NAME REDACTED].
    Use this before sharing files with external partners or donors.

    Args:
        file_id: The file ID to redact.
        service: Which service the file is on — "onedrive".
    """
    return _run("redact_file", file_id=file_id, service=service)


@tool
def retention_scan(service: str) -> StringToolOutput:
    """RETENTION: Scan all files for data retention policy violations.
    Identifies files containing PII that have exceeded retention thresholds
    (12 months for general PII, 6 months for special category data).

    Args:
        service: Which service to scan for retention violations — "onedrive".
    """
    return _run("retention_scan", service=service)


@tool
def generate_dpia(activity: str, data_types: str, purpose: str) -> StringToolOutput:
    """COMPLIANCE: Generate a Data Protection Impact Assessment (DPIA) for
    a data processing activity. Required under GDPR Article 35 for high-risk
    processing. Produces risk analysis, mitigation measures, and consultation requirements.

    Args:
        activity: Name of the data processing activity (e.g. "Biometric enrollment for aid distribution").
        data_types: Comma-separated data types being processed (e.g. "biometric_data, special_category_data, location_data, personal_identifier, humanitarian_identifier, government_identifier").
        purpose: Purpose of the data processing.
    """
    # Parse comma-separated string into list for the underlying function
    types_list = [t.strip() for t in data_types.split(",") if t.strip()]
    result = execute_tool("generate_dpia", {
        "activity": activity,
        "data_types": types_list,
        "purpose": purpose,
    }, access_token=_get_token())
    text = result.split("\n---JSON---")[0] if "---JSON---" in result else result
    return StringToolOutput(text)


@tool
def check_consent(file_id: str, service: str) -> StringToolOutput:
    """CONSENT: Check the consent documentation status for a data collection
    activity associated with a file. Verifies whether consent was obtained,
    properly documented, and covers all requirements (purpose explained,
    right to withdraw, third-party sharing disclosed).

    Args:
        file_id: The file ID to check consent for.
        service: Which service the file is on — "onedrive".
    """
    return _run("check_consent", file_id=file_id, service=service)


# ── All tools list for agent construction ──────────────────────────────

ALL_TOOLS = [
    scan_files,
    check_sharing,
    detect_pii,
    search_messages,
    revoke_sharing,
    download_file,
    delete_file,
    redact_file,
    retention_scan,
    generate_dpia,
    check_consent,
]


def get_openai_tools_schema() -> list[dict]:
    """Export tool definitions in OpenAI function-calling format.

    Used by the Chainlit app which manages its own agent loop
    for UI control (visible steps, confirmation dialogs, charts).
    """
    schemas = []
    for t in ALL_TOOLS:
        schema = {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema.model_json_schema(),
            },
        }
        schemas.append(schema)
    return schemas
