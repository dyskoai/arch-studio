from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Model strings ─────────────────────────────────────────────────────────
    # Any ADK-compatible string works here — no code change needed to switch provider.
    #
    # Native Gemini:   "gemini-3.1-pro-preview"
    # Via LiteLLM:     "litellm/anthropic/claude-sonnet-4-20250514"
    #                  "litellm/openai/gpt-4o"
    #
    refiner_model:   str = "gemini-2.5-flash-lite"
    router_model:    str = "gemini-2.5-flash-lite"
    architect_model: str = "gemini-2.5-pro"

    # ── API keys — all optional; set whichever your model strings require ─────
    google_api_key:    str = ""
    anthropic_api_key: str = ""
    openai_api_key:    str = ""

    # ── Server config ─────────────────────────────────────────────────────────
    allowed_origins:       str = "http://localhost:3000"
    rate_limit_per_minute: int = 10
    env:                   str = "development"

    # ── GCP / Agent Engine — demo branch only ─────────────────────────────────
    # Set USE_AGENT_ENGINE=true in Cloud Run to route pipeline calls through
    # Vertex AI Agent Engine instead of running in-process.
    # OSS deployments leave these as defaults (all off / empty).
    use_agent_engine:      bool = False
    gcp_project:           str  = ""
    gcp_location:          str  = "us-central1"
    model_location:        str  = "global"
    agent_engine_resource: str  = ""   # projects/<proj>/locations/<loc>/reasoningEngines/<id>

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
