"""
Amanat Agent — BeeAI Framework with Granite 4 Micro.

Uses BeeAI's RequirementAgent for native tool calling with retry logic,
cycle detection, and structured final answers. Works with any model that
supports OpenAI-compatible function calling (Granite via Ollama, OpenAI, etc).
"""

import asyncio

from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.backend.chat import ChatModel
from beeai_framework.memory import UnconstrainedMemory

from amanat.knowledge.policies import get_documents_for_prompt, search_policies
from amanat.tools.bee_tools import ALL_TOOLS, set_access_token


# Flat system prompt string for consumers that manage their own agent loop
# (e.g. Chainlit app.py). RequirementAgent uses role/instructions instead.
SYSTEM_PROMPT = """\
You are Amanat, a data governance agent for humanitarian NGOs.
You protect beneficiary data by scanning, investigating, and acting.

TOOL ROUTING — use the right tool for each service:
- To scan FILES on OneDrive: scan_files(service="onedrive")
- To scan SLACK messages: search_messages(service="slack", query="...")
- To scan OUTLOOK emails: search_messages(service="outlook", query="...")
- To scan ALL services: call scan_files for OneDrive, then search_messages for Slack, then search_messages for Outlook.

WORKFLOW: Do not just report — investigate and act.
1. SCAN the requested service(s) using the correct tool above.
2. DIG DEEPER: use detect_pii, check_sharing, check_consent on flagged items.
3. ACT: use redact_file, revoke_sharing, download_file, delete_file, generate_dpia.
4. REPORT what you found and what you did.

Chain multiple tools in sequence. If a scan reveals a problem, investigate it.
If sharing a file, check PII and redact first. If data is sensitive, check consent.\
"""

# Role and instructions are passed separately to RequirementAgent —
# it builds its own system prompt from these fields.
AGENT_ROLE = (
    "Amanat, a data governance agent for humanitarian NGOs. "
    "You protect beneficiary data by scanning, investigating, and acting."
)

AGENT_INSTRUCTIONS = [
    "TOOL ROUTING: scan_files is for OneDrive files only. search_messages is for Slack and Outlook.",
    "To scan Slack: search_messages(service='slack', query='...')",
    "To scan Outlook: search_messages(service='outlook', query='...')",
    "To scan OneDrive: scan_files(service='onedrive')",
    "Do not just report — investigate and act.",
    "DIG DEEPER: use detect_pii, check_sharing, check_consent on flagged items.",
    "ACT: use redact_file, revoke_sharing, download_file, delete_file, generate_dpia.",
    "REPORT what you found and what you did.",
    "Chain multiple tools in sequence. If a scan reveals a problem, investigate it.",
    "If sharing a file, check PII and redact first. If data is sensitive, check consent.",
]


def _get_extra_instructions(query: str) -> list[str]:
    """Get additional instructions with policy documents for policy questions.

    For scan/remediation queries, the violation report from tools already
    contains policy citations. Adding documents makes the prompt too long
    for small models and causes them to produce boilerplate instead of
    grounding on tool results.
    """
    scan_keywords = {"scan", "check", "audit", "review", "fix", "delete",
                     "revoke", "download", "remediate", "remove", "redact",
                     "share", "retention", "consent", "dpia"}
    is_scan_query = any(kw in query.lower() for kw in scan_keywords)

    if is_scan_query:
        return []

    relevant_policies = search_policies(query)
    policy_ids = [p["doc_id"] for p in relevant_policies]
    documents_block = get_documents_for_prompt(policy_ids)
    if documents_block:
        return [f"Ground your answer in these policy documents:\n{documents_block}"]
    return []


def create_agent(
    model: str = "openai:granite4-micro",
    access_token: str | None = None,
    extra_instructions: list[str] | None = None,
) -> RequirementAgent:
    """Create a BeeAI RequirementAgent configured for Amanat.

    RequirementAgent uses native tool calling with built-in retry logic,
    cycle detection, and a structured final_answer pattern.
    """
    set_access_token(access_token)

    llm = ChatModel.from_name(model)

    instructions = AGENT_INSTRUCTIONS + (extra_instructions or [])

    agent = RequirementAgent(
        llm=llm,
        tools=ALL_TOOLS,
        memory=UnconstrainedMemory(),
        role=AGENT_ROLE,
        instructions=instructions,
    )
    return agent


async def run_agent(query: str, access_token: str | None = None,
                    model: str = "openai:granite4-micro") -> str:
    """Run the agent on a query and return the final answer."""
    extra = _get_extra_instructions(query)
    agent = create_agent(model=model, access_token=access_token,
                         extra_instructions=extra)

    result = await agent.run(
        query,
        execution={
            "max_iterations": 10,
            "total_max_retries": 5,
            "max_retries_per_step": 2,
        },
    )

    # RequirementAgent returns output as a list of messages
    # The final answer is in the last output message
    if result.output:
        return result.output[-1].text
    return "Agent completed without producing an answer."


def run_agent_sync(query: str, access_token: str | None = None,
                   model: str = "openai:granite4-micro") -> str:
    """Synchronous wrapper for run_agent."""
    return asyncio.run(run_agent(query, access_token=access_token, model=model))


class AmanatAgent:
    """Compatibility wrapper around BeeAI RequirementAgent.

    Provides the same interface as the old manual agent loop
    for code that hasn't been migrated yet.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080/v1",
        api_key: str = "llama",
        model: str = "granite4-micro",
        tool_executor=None,
    ):
        self.model = f"openai:{model}"
        self.tool_executor = tool_executor
        self.messages: list[dict] = []

    def run(self, user_query: str) -> str:
        """Run the agent loop via BeeAI."""
        return run_agent_sync(user_query, model=self.model)
