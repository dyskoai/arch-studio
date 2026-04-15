"""
Phase 2 Architecture Pipeline
Assembles router → architect → validator as an ADK SequentialAgent.

best_practices.md is read from disk and embedded directly into the architect
agent's instruction string at pipeline construction time (Python string format).
{classification} remains as an ADK template placeholder — ADK resolves it from
session.state["classification"] written by router_agent via output_key.
"""
import json
import os
import time
from pathlib import Path
from typing import Any

from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from app.agents._keys import export_api_keys
from app.agents.router_agent import build_router_agent
from app.agents.architect_agent import build_architect_agent
from app.agents.validator_agent import build_validator_agent
from app.config import get_settings
from app.models.schemas import ArchResult, PipelineTimings

# Path to the best-practices reference doc (acrh-studio/best-practices.md)
# __file__ = acrh-studio/backend/app/agents/pipeline.py
# parents[3] = acrh-studio/
_BEST_PRACTICES_PATH = Path(__file__).parents[3] / "best-practices.md"


def _sanitize_best_practices(content: str) -> str:
    """
    Strip vendor-specific branding and links — keep only the core architectural
    ideas (pattern names, descriptions, trade-offs, decision criteria).
    """
    import re
    # Remove "What's next" and "Contributors" sections (everything after)
    content = re.sub(r"What.s next.*", "", content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"Contributors.*", "", content, flags=re.DOTALL | re.IGNORECASE)
    # Strip provider names and product branding
    for phrase in [
        r"Google Cloud\s*",
        r"Google\s+Cloud\b",
        r"\bCloud Run\b",
        r"Agent Development Kit \(ADK\)",
        r"\bADK\b",
        r"Google Cloud Documentation",
        r"Cloud Architecture Center",
    ]:
        content = re.sub(phrase, "", content)
    # Strip all URLs
    content = re.sub(r"https?://\S+", "", content)
    # Strip markdown image/link syntax that references external resources
    content = re.sub(r"!\[.*?\]\(.*?\)", "", content)
    content = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", content)  # keep link text
    # Clean up excessive blank lines
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def _load_best_practices() -> str:
    """Read best-practices.md fresh from disk and strip vendor branding."""
    if _BEST_PRACTICES_PATH.exists():
        raw = _BEST_PRACTICES_PATH.read_text(encoding="utf-8")
        return _sanitize_best_practices(raw)
    return "(no reference doc — use standard agent pattern selection criteria)"


def build_pipeline(best_practices: str = "") -> SequentialAgent:
    """
    Assembles the three-stage pipeline as a SequentialAgent.

    Data flow via session.state:
      router_agent     → state["classification"]     (JSON string)
      architect_agent  → state["raw_architecture"]   (JSON string, reads {classification})
      validator_agent  → state["final_architecture"] (JSON string)
                       → state["repaired"]           (bool)
                       → state["validator_issues"]   (list[str])

    best_practices is embedded into the architect instruction at build time.
    """
    return SequentialAgent(
        name="architecture_pipeline",
        description="Three-stage pipeline: classify pattern → generate architecture → validate graph",
        sub_agents=[
            build_router_agent(),
            build_architect_agent(best_practices=best_practices),
            build_validator_agent(),
        ],
    )


async def run_pipeline(refined_spec: str) -> dict[str, Any]:
    """
    Runs the architecture pipeline for a given refined spec.
    Returns a dict with the ArchResult, timings, and repair flag.
    """
    settings = get_settings()
    export_api_keys(settings)

    session_service = InMemorySessionService()
    pipeline = build_pipeline(best_practices=_load_best_practices())
    runner = Runner(
        agent=pipeline,
        app_name="intentiv_pipeline",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="intentiv_pipeline",
        user_id="api_user",
    )

    user_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=refined_spec)],
    )

    t_start = time.monotonic()
    timings: dict[str, float] = {
        "router_start": 0.0,
        "architect_start": 0.0,
        "validator_start": 0.0,
    }

    async for event in runner.run_async(
        user_id="api_user",
        session_id=session.id,
        new_message=user_message,
    ):
        author = getattr(event, "author", "")
        now = time.monotonic()
        if author == "router_agent" and timings["router_start"] == 0.0:
            timings["router_start"] = now
        elif author == "architect_agent" and timings["architect_start"] == 0.0:
            timings["architect_start"] = now
        elif author == "validator_agent" and timings["validator_start"] == 0.0:
            timings["validator_start"] = now

    t_end = time.monotonic()

    # Re-fetch the session from the service — the runner writes state to its
    # internal copy; the original session object is not mutated in place.
    updated_session = await session_service.get_session(
        app_name="intentiv_pipeline",
        user_id="api_user",
        session_id=session.id,
    )
    final_state = updated_session.state if updated_session else {}
    final_arch_json = final_state.get("final_architecture", "")
    repaired = bool(final_state.get("repaired", False))

    if not final_arch_json:
        raise ValueError("Pipeline completed but final_architecture is empty")

    arch_data = json.loads(final_arch_json)

    # Normalise edge field aliases (from/from_node, to/to_node)
    for edge in arch_data.get("edges", []):
        if "from" not in edge and "from_node" in edge:
            edge["from"] = edge.pop("from_node")
        if "to" not in edge and "to_node" in edge:
            edge["to"] = edge.pop("to_node")

    arch_result = ArchResult.model_validate(arch_data)

    total_ms    = int((t_end - t_start) * 1000)
    router_ms   = max(0, int((timings["architect_start"] - t_start) * 1000))
    architect_ms = max(0, int((timings["validator_start"] - timings["architect_start"]) * 1000))
    validator_ms = max(0, int((t_end - timings["validator_start"]) * 1000))

    return {
        "result": arch_result,
        "pattern": arch_result.pattern,
        "timings": PipelineTimings(
            router_ms=router_ms,
            architect_ms=architect_ms,
            validator_ms=validator_ms,
            total_ms=total_ms,
        ),
        "repaired": repaired,
    }
