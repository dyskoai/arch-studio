"""
Execution abstraction — routes pipeline calls to either:
  - in-process ADK pipeline (OSS / local)
  - Vertex AI Agent Engine  (demo / Cloud Run, when USE_AGENT_ENGINE=true)

The return dict shape is identical in both paths so generate.py needs no changes.
"""
import time
import json
import logging
from typing import Any

from app.agents.pipeline import run_pipeline
from app.config import get_settings
from app.models.schemas import ArchResult, PipelineTimings

logger = logging.getLogger(__name__)


async def run_generate(refined_spec: str) -> dict[str, Any]:
    """Entry point called by generate.py — replaces direct run_pipeline() call."""
    settings = get_settings()
    if settings.use_agent_engine and settings.agent_engine_resource:
        return await _run_via_agent_engine(refined_spec, settings)
    return await run_pipeline(refined_spec)


async def _run_via_agent_engine(refined_spec: str, settings) -> dict[str, Any]:
    """
    Calls the pipeline deployed on Vertex AI Agent Engine.

    Pattern from samples/agent_api.py:
      - agent_engines.get()          to retrieve the deployed app (call API)
      - async_create_session()       for a fresh per-request session
      - async_stream_query()         to run the pipeline and wait for completion
      - get_session()                to read final_architecture from session state
        (our pipeline writes output to state, not to text events)

    Note: agent_engines (call API) ≠ reasoning_engines (deploy API).
    """
    import vertexai
    from vertexai import agent_engines

    vertexai.init(project=settings.gcp_project, location=settings.gcp_location)
    remote_app = agent_engines.get(settings.agent_engine_resource)

    # Fresh session per request — stateless for now.
    # session_id can be preserved for future multi-turn chat.
    session = await remote_app.async_create_session(user_id="api_user")
    session_id = (
        session.get("id")
        or session.get("name")
        or session.get("session_id")
    )
    if not session_id:
        raise ValueError(f"Could not extract session_id from Agent Engine response: {session}")

    logger.info("Agent Engine session created: %s", session_id)

    t_start = time.monotonic()
    streamed_final_architecture = ""
    async for event in remote_app.async_stream_query(
        user_id="api_user",
        session_id=session_id,
        message=refined_spec,
    ):
        # Agent Engine should persist validator state_delta, but some deployed
        # ADK/Agent Engine combinations expose the validator output only in
        # streamed event text. Keep a parsed fallback so production generation
        # does not depend on state persistence alone.
        streamed_final_architecture = (
            _extract_architecture_from_event(event) or streamed_final_architecture
        )
        logger.warning("Agent Engine stream event: %s", event)
        logger.debug("Agent Engine event: %s", event)
    t_end = time.monotonic()

    # Prefer session state; fall back to validator event text if Agent Engine did
    # not persist EventActions(state_delta=...).
    session_data = remote_app.get_session(user_id="api_user", session_id=session_id)
    state = session_data.get("state", {})

    return _extract_result(
        state,
        total_sec=t_end - t_start,
        fallback_final_architecture=streamed_final_architecture,
    )


def _extract_architecture_from_event(event: Any) -> str:
    """Return architecture JSON from an Agent Engine stream event, if present."""
    state_architecture = _event_state_delta(event).get("final_architecture", "")
    if state_architecture:
        return state_architecture

    for text in _event_text_parts(event):
        candidate = text.strip()
        if candidate.startswith("```"):
            candidate = candidate.strip("`").removeprefix("json").strip()
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "nodes" in data and "edges" in data:
            return json.dumps(data)
    return ""


def _event_state_delta(event: Any) -> dict[str, Any]:
    """Return EventActions state_delta from dict or ADK Event object."""
    if isinstance(event, dict):
        actions = event.get("actions") or {}
        state_delta = (
            actions.get("state_delta")
            or actions.get("stateDelta")
            or actions.get("state")
            or {}
        )
        return state_delta if isinstance(state_delta, dict) else {}

    actions = getattr(event, "actions", None)
    state_delta = getattr(actions, "state_delta", {}) if actions else {}
    return state_delta if isinstance(state_delta, dict) else {}


def _event_text_parts(event: Any) -> list[str]:
    """Support both dict events from Agent Engine and local ADK Event objects."""
    if isinstance(event, dict):
        parts = event.get("content", {}).get("parts", [])
        return [
            part.get("text", "")
            for part in parts
            if isinstance(part, dict) and part.get("text")
        ]

    content = getattr(event, "content", None)
    parts = getattr(content, "parts", []) if content else []
    texts: list[str] = []
    for part in parts:
        text = getattr(part, "text", "")
        if text:
            texts.append(text)
    return texts


def _extract_result(
    state: dict,
    total_sec: float = 0.0,
    fallback_final_architecture: str = "",
) -> dict[str, Any]:
    """
    Mirrors the final section of pipeline.run_pipeline() so the return shape is identical.
    Called for both Agent Engine results and (in tests) direct state inspection.
    """
    final_arch_json = state.get("final_architecture", "") or fallback_final_architecture
    if not final_arch_json:
        raise ValueError(
            "Pipeline completed but final_architecture is empty in session state "
            "and no architecture JSON was found in streamed events"
        )

    arch_data = json.loads(final_arch_json)

    # Normalise edge field aliases (from/from_node, to/to_node)
    for edge in arch_data.get("edges", []):
        if "from" not in edge and "from_node" in edge:
            edge["from"] = edge.pop("from_node")
        if "to" not in edge and "to_node" in edge:
            edge["to"] = edge.pop("to_node")

    arch_result = ArchResult.model_validate(arch_data)

    return {
        "result":  arch_result,
        "pattern": arch_result.pattern,
        "timings": PipelineTimings(
            router_ms=0,
            architect_ms=0,
            validator_ms=0,
            total_ms=int(total_sec * 1000),
        ),
        "repaired": bool(state.get("repaired", False)),
    }
