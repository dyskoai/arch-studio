"""
Shared helper: export whichever API keys are configured into the environment.
ADK / LiteLLM pick them up automatically based on the model string prefix.
"""
import os
from app.config import Settings


def export_api_keys(settings: Settings) -> None:
    """Set env vars for whichever provider keys are configured."""
    if settings.google_api_key:
        os.environ["GOOGLE_API_KEY"] = settings.google_api_key
    if settings.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
