"""
Amanat Agent — Strands Agents SDK with Granite 4 Micro.

Uses Strands for the agent loop with native tool call hooks:
- BeforeToolCallEvent: confirmation dialog for destructive actions, show Chainlit steps
- AfterToolCallEvent: capture results for charts, close Chainlit steps
"""

import os

from strands import Agent, tool
from strands.models.openai import OpenAIModel

from amanat.knowledge.policies import get_rag_documents
from amanat.tools.scanner import execute_tool


SYSTEM_PROMPT = """\
You are Amanat, a data governance agent for the Waqwaq Relief Authority (WRA).
You protect beneficiary data by scanning, investigating, and acting.

TOOL ROUTING — use the right tool for each service:
- OneDrive files: scan_files(service="onedrive")
- Slack messages: search_messages(service="slack", query="...")
- Outlook emails: search_messages(service="outlook", query="...")
- "scan outlook" or "check emails" means: search_messages(service="outlook", query="beneficiary OR case OR medical")
- "scan slack" means: search_messages(service="slack", query="beneficiary OR case OR medical")
- scan_files is ONLY for OneDrive. NEVER use scan_files for outlook or slack.
- To post alerts to Slack: notify_channel(channel="CHANNEL", pii_summary="...", service="slack")
- ONLY use channel names from scan results (listed under AFFECTED CHANNELS). NEVER invent channel names.
- After a Slack scan that finds violations, post an alert to each affected channel listed in the results.

CRITICAL RULES:
- NEVER ask the user for channel names, file IDs, or folder paths. Just call the tool immediately.
- If the user asks to search or scan, call the tool right away with a broad query.
- For Slack: search_messages(service="slack", query="beneficiary OR case OR medical")
- For Outlook: search_messages(service="outlook", query="beneficiary OR case OR medical")
- For OneDrive: scan_files(service="onedrive")
- Do NOT ask clarifying questions. Act first, report what you find.

WORKFLOW:
1. SCAN the requested service(s) using the correct tool above. Call the tool NOW.
2. DIG DEEPER: use detect_pii, check_sharing, check_consent on flagged items.
3. ACT: for Slack scans, auto-post alerts to affected channels. For OneDrive, act only when asked.
4. REPORT what you found and what you did.

Chain multiple tools in sequence. If a scan reveals a problem, investigate it.\
"""


def _build_system_prompt(query: str) -> str:
    """Build system prompt with optional RAG documents for policy questions.

    Policy questions get RAG documents injected. Scan/action queries don't
    (to keep context short for Granite Micro). A query is a policy question
    if it asks about rules, standards, or requirements rather than requesting
    a scan or action on a specific service.
    """
    q = query.lower()

    # Policy question indicators — these override scan keywords
    policy_indicators = [
        "what does", "what are the rules", "what are the requirements",
        "icrc", "gdpr", "iasc", "sphere", "handbook", "article",
        "policy", "standard", "guideline", "regulation",
        "allowed", "permitted", "legal basis", "lawful",
        "do we need", "are we compliant", "is it okay", "can we",
        "what constitutes", "when is", "under what circumstances",
        "difference between",
    ]
    is_policy_question = any(p in q for p in policy_indicators)

    # Scan/action indicators — only if NOT a policy question
    scan_keywords = [
        "scan", "search slack", "search outlook", "check my", "check if",
        "audit", "fix", "delete", "revoke", "download", "remediate",
        "remove", "redact", "retention scan", "notify", "lock down",
        "publicly shared", "publicly accessible", "are any",
    ]
    is_scan_query = not is_policy_question and any(kw in q for kw in scan_keywords)

    if is_scan_query:
        return SYSTEM_PROMPT

    # Policy question or ambiguous — inject RAG documents
    documents_block = get_rag_documents(query, max_docs=5)
    if documents_block:
        return (
            SYSTEM_PROMPT + "\n\n"
            "Answer the following question using ONLY the information in the "
            "provided documents. Cite the source document in your answer. "
            "If the answer cannot be found in the documents, say so. "
            "Do NOT scan any services — just answer the policy question.\n\n"
            + documents_block
        )
    return SYSTEM_PROMPT


# --- Tool definitions using Strands @tool decorator ---
# Each tool wraps execute_tool() from scanner.py, which handles
# both demo mode and live API calls via Token Vault.

_access_token: str | None = None
_service_tokens: dict[str, str] = {}


def set_access_token(token: str | None, service_tokens: dict[str, str] | None = None):
    """Set access tokens for live API calls.

    Args:
        token: Default token (OneDrive/Microsoft Graph).
        service_tokens: Per-service tokens {"onedrive": "...", "slack": "...", "outlook": "..."}.
    """
    global _access_token, _service_tokens
    _access_token = token
    _service_tokens = service_tokens or {}


def _run(name: str, **kwargs) -> str:
    """Execute a tool and return text result.

    Picks the correct per-service token from _service_tokens based on
    the service argument. Falls back to _access_token (default/OneDrive).
    """
    service = kwargs.get("service", "")
    token = _service_tokens.get(service, _access_token)
    result = execute_tool(name, kwargs, access_token=token)
    # Strip JSON blob — LLM gets the human-readable text portion only
    text = result.split("\n---JSON---")[0] if "---JSON---" in result else result
    # Truncate to prevent context overflow on large scans
    if len(text) > 4000:
        text = text[:4000] + "\n\n[... truncated for context. Full results available in UI.]"
    return text


@tool
def scan_files(service: str, query: str = "") -> str:
    """Scan files for sensitive data exposure and policy violations.
    ONLY for OneDrive. Do NOT use for Outlook or Slack.
    For Outlook emails, use search_messages(service="outlook").
    For Slack messages, use search_messages(service="slack").

    Args:
        service: Must be "onedrive". Use search_messages for other services.
        query: Optional search query to filter files by name.
    """
    if service in ("outlook", "gmail", "email"):
        return "Error: scan_files is for OneDrive only. Use search_messages(service=\"outlook\") to search emails."
    if service == "slack":
        return "Error: scan_files is for OneDrive only. Use search_messages(service=\"slack\") to search Slack messages."
    return _run("scan_files", service=service, query=query or None)


@tool
def check_sharing(file_id: str, service: str) -> str:
    """Check the sharing and permission settings for a specific file.

    Args:
        file_id: The file identifier to check.
        service: Which service — "onedrive".
    """
    return _run("check_sharing", file_id=file_id, service=service)


@tool
def detect_pii(file_id: str, service: str) -> str:
    """Analyze file content for PII and sensitive humanitarian data.

    Args:
        file_id: The file to analyze.
        service: Which service — "onedrive".
    """
    return _run("detect_pii", file_id=file_id, service=service)


@tool
def search_messages(service: str, query: str) -> str:
    """Search messaging services for sensitive content.
    Use this to search Slack messages or Outlook emails for PII leaks.

    Args:
        service: Which service — "slack" or "outlook".
        query: Search query.
    """
    return _run("search_messages", service=service, query=query)


@tool
def revoke_sharing(file_id: str, service: str) -> str:
    """REMEDIATION: Revoke public sharing on files that contain PII.
    Pass the file IDs exactly as returned by scan_files.
    Accepts a single file ID or multiple comma-separated file IDs.

    Args:
        file_id: One or more file IDs (comma-separated). Copy these directly from scan_files results.
        service: The service — "onedrive".
    """
    return _run("revoke_sharing", file_id=file_id, service=service)


@tool
def download_file(file_id: str, service: str) -> str:
    """REMEDIATION: Download a file from a connected service to local storage.

    Args:
        file_id: The file ID to download.
        service: The service — "onedrive".
    """
    return _run("download_file", file_id=file_id, service=service)


@tool
def delete_file(file_id: str, service: str) -> str:
    """REMEDIATION: Move a file to trash on the connected service.

    Args:
        file_id: The file ID to delete.
        service: The service — "onedrive".
    """
    return _run("delete_file", file_id=file_id, service=service)


@tool
def redact_file(file_id: str, service: str) -> str:
    """SAFE SHARING: Create a redacted copy of a file with all PII removed.
    Downloads the file, replaces all PII with redaction labels, uploads
    the redacted version as REDACTED_filename in the same folder.
    Call this directly without scanning first.

    Args:
        file_id: A file ID or filename (e.g. "Cataclysm_Displaced_Registry_2026.csv").
        service: Which service — "onedrive".
    """
    return _run("redact_file", file_id=file_id, service=service)


@tool
def retention_scan(service: str) -> str:
    """RETENTION: Scan for data retention policy violations.

    Args:
        service: Which service — "onedrive".
    """
    return _run("retention_scan", service=service)


@tool
def generate_dpia(activity: str, data_types: str, purpose: str) -> str:
    """COMPLIANCE: Generate a Data Protection Impact Assessment.

    Args:
        activity: Name of the data processing activity.
        data_types: Comma-separated data types being processed.
        purpose: Purpose of the data processing.
    """
    types_list = [t.strip() for t in data_types.split(",") if t.strip()]
    result = execute_tool("generate_dpia", {
        "activity": activity,
        "data_types": types_list,
        "purpose": purpose,
    }, access_token=_access_token)
    return result


@tool
def check_consent(file_id: str, service: str) -> str:
    """CONSENT: Check consent documentation status for a file.

    Args:
        file_id: The file ID to check consent for.
        service: Which service — "onedrive".
    """
    return _run("check_consent", file_id=file_id, service=service)


@tool
def notify_channel(channel: str, pii_summary: str, service: str) -> str:
    """REMEDIATION: Post a data protection alert to a Slack channel.

    Args:
        channel: The Slack channel ID to post to.
        pii_summary: Summary of PII findings.
        service: Which service — "slack".
    """
    return _run("notify_channel", channel=channel, pii_summary=pii_summary, service=service)


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """REMEDIATION: Send a data protection alert email to a user.
    Use this to notify someone who sent or shared sensitive data.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body text.
    """
    return _run("send_email", to=to, subject=subject, body=body, service="outlook")


@tool
def parse_document(file_path: str) -> str:
    """DOCUMENT PARSING: Parse a PDF, DOCX, or other document and scan for PII.

    Args:
        file_path: Local path to the document to parse.
    """
    from amanat.tools.docling_tool import parse_and_scan_document
    return parse_and_scan_document(file_path)


ALL_TOOLS = [
    scan_files, check_sharing, detect_pii, search_messages,
    revoke_sharing, download_file, delete_file, redact_file,
    retention_scan, generate_dpia, check_consent, notify_channel,
    send_email, parse_document,
]

REMEDIATION_TOOLS = {"revoke_sharing", "download_file", "delete_file"}


def _get_watsonx_token() -> str:
    """Get a fresh IAM token for watsonx. Called on every agent creation."""
    import httpx
    api_key = os.environ.get("WATSONX_API_KEY", "")
    if not api_key:
        return os.environ.get("OPENAI_API_KEY", "llama")
    resp = httpx.post(
        "https://iam.cloud.ibm.com/identity/token",
        data=f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={api_key}",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return resp.json()["access_token"]


def create_model() -> OpenAIModel:
    """Create the Strands OpenAI model.

    Supports local llama-server, OpenRouter, Ollama, and IBM watsonx.
    Set GRANITE_MODEL_ID env var to override the model ID.
    """
    base_url = os.environ.get("OPENAI_API_BASE", "http://localhost:8080/v1")
    is_watsonx = "ml.cloud.ibm.com" in base_url

    if "openrouter" in base_url:
        default_model = "ibm-granite/granite-4.0-h-micro"
    elif is_watsonx:
        default_model = "ibm/granite-4-h-small"
    else:
        default_model = "granite4-micro"
    model_id = os.environ.get("GRANITE_MODEL_ID", default_model)

    params: dict = {"max_tokens": 4096}

    # watsonx requires project_id in every request body
    project_id = os.environ.get("WATSONX_PROJECT_ID", "")
    if project_id:
        params["extra_body"] = {"project_id": project_id}

    # Fresh IAM token for watsonx (expires after 1 hour)
    api_key = _get_watsonx_token() if is_watsonx else os.environ.get("OPENAI_API_KEY", "llama")

    return OpenAIModel(
        client_args={
            "base_url": base_url,
            "api_key": api_key,
        },
        model_id=model_id,
        params=params,
    )


def create_agent(system_prompt: str | None = None, access_token: str | None = None,
                 service_tokens: dict[str, str] | None = None,
                 demo_tools: bool = False) -> Agent:
    """Create a Strands Agent configured for Amanat.

    If demo_tools=True and the LLM provider doesn't support tool calling
    (e.g. OpenRouter), creates an agent without tools. The caller should
    pre-execute tools and inject results into the system prompt.
    """
    set_access_token(access_token, service_tokens)

    base_url = os.environ.get("OPENAI_API_BASE", "")
    provider_supports_tools = "openrouter" not in base_url

    return Agent(
        model=create_model(),
        system_prompt=system_prompt or SYSTEM_PROMPT,
        tools=ALL_TOOLS if provider_supports_tools else [],
    )


async def run_agent(query: str, access_token: str | None = None) -> str:
    """Run the agent on a query and return the final answer."""
    system_prompt = _build_system_prompt(query)
    agent = create_agent(system_prompt=system_prompt, access_token=access_token)
    result = agent(query)
    if result.message and result.message.get("content"):
        for block in result.message["content"]:
            if "text" in block:
                return block["text"]
    return "Agent completed without producing an answer."
