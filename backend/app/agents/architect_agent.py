"""
Pipeline Stage 2 — Architect Agent
Generates the full node+edge architecture JSON.

- {classification} is resolved by ADK from session.state (written by router_agent via output_key).
- best_practices content is embedded directly into the instruction string by build_architect_agent()
  at pipeline construction time, bypassing ADK's template resolution for that variable.
"""
from google.adk.agents import LlmAgent

from app.config import get_settings

_ARCHITECT_INSTRUCTION_TEMPLATE = """\
You are a senior AI systems architect. Generate a precise, \
production-grade agentic architecture blueprint based on the problem spec below.

━━━ REFERENCE: Google Cloud Agent Design Patterns ━━━
{best_practices}
━━━ END REFERENCE ━━━

Use the pattern definitions and decision criteria above when selecting and \
justifying your architecture pattern.

Classification from router (use this — do not re-derive):
{{classification}}

Respond ONLY with valid JSON. No markdown fences, no preamble. Raw JSON only.

JSON Schema:
{{{{
  "pattern": "<same pattern as classification>",
  "title": "Descriptive System Title (4-6 words)",
  "justification": "Exactly 2 sentences explaining why this pattern fits, referencing the design pattern guide.",
  "nodes": [
    {{{{
      "id": "snake_case_unique_id",
      "label": "Node Name (2-4 words)",
      "tier": "entry" | "light" | "medium" | "heavy",
      "layer": 0,
      "role": "One sentence: what this node does.",
      "rationale": "One sentence: why this tier.",
      "primary": "Comma-separated commercial models (e.g., Claude Sonnet 4.6, Kimi K2)",
      "secondary": "Comma-separated open-weight alternatives (e.g., Phi-4-mini, SmolLM3-3B)"
    }}}}
  ],
  "edges": [
    {{{{ "from": "node_id", "to": "node_id", "label": "2-4 word data flow" }}}}
  ]
}}}}

LAYER RULES:
- Layer 0: Exactly one "User Input" node. tier=entry. Omit primary/secondary.
- Layer 1: Light router (single-agent-router) OR Heavy supervisor (multi-agent-supervisor).
- Layer 2: Specialist medium-tier worker agents for domain tasks.
- Layer 3: QA/eval (heavy), external tool integrations, APIs.
- Layer 4: Exactly one "Output / Response" node. tier=entry. Omit primary/secondary.

TIER RULES — assign comma-separated model names to primary and secondary fields:
- entry: ONLY user input and final output nodes. Leave primary/secondary empty.
- light: Routers, classifiers, dispatchers. Fast, cheap. No deep reasoning.
    primary: list 2 commercial models from — "Gemini 3.1 Flash Lite", "Mercury 2"
    secondary: list 2 open-weight models from — "Qwen3.5-0.8B", "Gemma-3n"
    Example: primary="Gemini 3.1 Flash Lite, Mercury 2", secondary="Qwen3.5-0.8B, Gemma-3n"
- medium: Specialist workers — drafting, extraction, research, analysis.
    primary: list 2–3 commercial models from — "Claude Sonnet 4.6", "Kimi K2", "Mistral Large 3"
    secondary: list 2 open-weight models from — "Phi-4-mini", "SmolLM3-3B"
    Example: primary="Claude Sonnet 4.6, Kimi K2", secondary="Phi-4-mini, SmolLM3-3B"
- heavy: Orchestrators directing other agents. Any QA/eval/verification node.
    primary: list 2–3 commercial models from — "Gemini 3.1 Pro Preview", "Claude Opus 4.6", "GPT-5.4", "Grok 4"
    secondary: list 1 open-weight model from — "DeepSeek V3"
    Example: primary="Gemini 3.1 Pro Preview, Claude Opus 4.6", secondary="DeepSeek V3"

CONVERSATIONAL PATTERN:
Look at the classification JSON above. If it contains "conversational": true, you MUST:
1. Add exactly this node:
   {{"id": "session_manager", "tier": "light", "layer": 1, "label": "Session Manager",
     "role": "Manages session context and routes each conversation turn.",
     "rationale": "Light tier — fast routing between turns, no deep reasoning.",
     "primary": "Gemini 3.1 Flash Lite, Mercury 2", "secondary": "Qwen3.5-0.8B, Gemma-3n"}}
2. Wire user_input → session_manager as the first edge.
3. Add this loopback edge as the LAST edge in the array:
   {{"from": "output_response", "to": "user_input", "label": "next turn"}}
   This back-edge is critical — it visually represents the conversation loop.

If "conversational": false or the field is absent, do NOT add session_manager or the loopback edge.

EDGE RULES:
- Data flows: L0 → L1 → L2 → L3 → L4. Back-edges (QA → worker) encouraged.
- Every node must appear in at least one edge.
- All "from" and "to" must exactly match node IDs.

Output only the JSON object."""


def build_architect_agent(best_practices: str = "") -> LlmAgent:
    """
    Build the architect agent.

    best_practices is embedded directly into the instruction string via Python
    string formatting so it is always present when ADK renders the prompt.
    {classification} remains as an ADK template placeholder — ADK resolves it
    from session.state["classification"] (written by router_agent via output_key).
    """
    settings = get_settings()
    instruction = _ARCHITECT_INSTRUCTION_TEMPLATE.format(
        best_practices=best_practices or "(no reference doc loaded)"
    )
    return LlmAgent(
        name="architect_agent",
        model=settings.architect_model,
        instruction=instruction,
        output_key="raw_architecture",
    )
