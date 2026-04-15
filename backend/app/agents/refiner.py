"""
Phase 1 — Refiner Agent
Standalone LlmAgent that transforms a vague problem description into a
precise, opinionated 2–4 sentence spec. Runs as a single ADK Runner
invocation, separate from the Phase 2 pipeline.
"""
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from app.agents._keys import export_api_keys
from app.config import get_settings


REFINER_INSTRUCTION = """You are a senior AI product architect who turns rough, vague problem \
descriptions into precise, actionable agent system specifications.

When the user gives you a rough idea, return a refined specification that:
1. Specifies what data sources or backend systems the agent connects to
2. Describes what the agent does with multiple inputs (parallel? sequential?)
3. States exactly what the output format should be (table, report, action, etc.)
4. Mentions any specific features like export options, filtering, or user controls

Rules:
- Output ONLY the refined specification text. No headers, no lists, no labels.
- 2–4 sentences maximum. Be specific and opinionated.
- Use present tense ("Build an agent that...", "The system should...")
- Do not mention architecture patterns, tiers, or implementation details

Example input: "order status agent for support"
Example output: "Build an agent that connects across backend order management, \
warehouse, and shipping systems to retrieve real-time status for multiple orders \
simultaneously. The agent should aggregate results into a structured table showing \
order ID, current status, last update, and estimated delivery, with a one-click \
option to download the results as a CSV file."
"""


def build_refiner_agent() -> LlmAgent:
    settings = get_settings()
    return LlmAgent(
        name="refiner_agent",
        model=settings.refiner_model,
        instruction=REFINER_INSTRUCTION,
        # No output_key — we read the runner's final event text directly
    )


async def run_refiner(rough_input: str) -> str:
    """
    Runs the refiner agent standalone and returns the refined spec text.
    Creates a fresh session for each call — stateless by design.
    """
    settings = get_settings()
    export_api_keys(settings)

    session_service = InMemorySessionService()
    agent = build_refiner_agent()
    runner = Runner(
        agent=agent,
        app_name="intentiv_refiner",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="intentiv_refiner",
        user_id="api_user",
    )

    user_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=rough_input)],
    )

    refined_text = ""
    async for event in runner.run_async(
        user_id="api_user",
        session_id=session.id,
        new_message=user_message,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            refined_text = "".join(
                part.text for part in event.content.parts if hasattr(part, "text")
            )

    return refined_text.strip()
