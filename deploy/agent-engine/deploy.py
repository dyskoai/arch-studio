"""
Deploy the Intentiv pipeline to Vertex AI Agent Engine.

Run ONCE to create the managed agent. After running, copy the printed
AGENT_ENGINE_RESOURCE value into the Cloud Run backend environment.

Usage:
    cd acrh-studio
    GCP_PROJECT=your-project python deploy/agent-engine/deploy.py

API notes:
    - reasoning_engines.ReasoningEngine.create()  →  DEPLOY API  (this file)
    - vertexai.agent_engines.get(resource)        →  CALL API    (runner.py)
    These are two different Vertex AI SDK namespaces.
"""
import os
import sys

# Add backend/ to path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import vertexai
from vertexai.preview.reasoning_engines import AdkApp, ReasoningEngine

from app.agents.pipeline import build_pipeline, _load_best_practices

GCP_PROJECT  = os.environ["GCP_PROJECT"]
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")

print(f"Deploying to project={GCP_PROJECT}, location={GCP_LOCATION} ...")

vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)

engine = ReasoningEngine.create(
    AdkApp(agent=build_pipeline(best_practices=_load_best_practices())),
    requirements=[
        "google-adk>=1.0.0",
        "google-genai>=1.9.0",
        "litellm>=1.50.0",
        "pydantic>=2.9.0",
        "pydantic-settings>=2.6.0",
    ],
    display_name="intentiv-pipeline",
    # Include best-practices.md so the agent has access to it inside the engine
    extra_packages=["best-practices.md"],
)

print("\n✓ Deployed successfully.")
print(f"\nAGENT_ENGINE_RESOURCE={engine.resource_name}\n")
print("Add this value to your Cloud Run backend environment variables.")
