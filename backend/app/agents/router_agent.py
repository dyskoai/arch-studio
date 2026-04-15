"""
Pipeline Stage 1 — Router Agent
Classifies the problem into a pattern and writes to session.state["classification"]
via output_key. Fast/cheap model — triage only, no deep reasoning.
"""
from google.adk.agents import LlmAgent

from app.config import get_settings


ROUTER_INSTRUCTION = """You are an AI architecture classifier. Read the problem specification \
and output ONLY valid JSON — no markdown, no preamble.

Schema:
{
  "pattern": "single-agent-router" | "multi-agent-supervisor",
  "confidence": "high" | "medium" | "low",
  "reasoning": "one internal sentence explaining the choice",
  "node_count_hint": 7,
  "conversational": false
}

Classification rules:
- single-agent-router: One router dispatches to bounded, deterministic tools.
  Signals: "route to", "classify and forward", "look up", "fetch from",
  sequential steps, API calls, no cross-agent collaboration. node_count_hint: 5–8.
- multi-agent-supervisor: A supervisor coordinates multiple agents in parallel
  or iteratively. Signals: "multiple specialists", "parallel processing",
  "maker/checker", "different personas", "cross-review", "iterative refinement".
  node_count_hint: 8–14.

Conversational detection — set "conversational": true if the spec mentions any of:
  "multi-turn", "conversation", "dialog", "dialogue", "chat", "chatbot",
  "follow-up", "follow up", "user history", "session", "remember context",
  "memory", "back-and-forth", "ongoing", "persistent context", "turn-by-turn".
  Otherwise set "conversational": false.

Output ONLY the JSON object. Nothing else."""


def build_router_agent() -> LlmAgent:
    settings = get_settings()
    return LlmAgent(
        name="router_agent",
        model=settings.router_model,
        instruction=ROUTER_INSTRUCTION,
        output_key="classification",   # writes JSON string to session.state["classification"]
    )
