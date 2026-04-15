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

import importlib

import cloudpickle
import vertexai
from google.cloud import storage
from google.api_core.exceptions import Conflict
from vertexai.preview.reasoning_engines import AdkApp, ReasoningEngine

from app.agents.pipeline import build_pipeline, _load_best_practices

# Register all local app modules for cloudpickle-by-value.
# Default behaviour: cloudpickle stores a class by its module path (e.g.
# "app.agents.validator_agent.ValidatorAgent"). Agent Engine then needs to
# import that module at startup — which fails because app/ isn't installed.
# register_pickle_by_value() switches to embedding the class bytecode directly
# in the pickle, so the remote side reconstructs it without any import.
for _mod_name in [
    "app.agents.validator_agent",
    "app.agents.router_agent",
    "app.agents.architect_agent",
    "app.agents.pipeline",
    "app.config",
    "app.models.schemas",
    "app.agents._keys",
]:
    try:
        cloudpickle.register_pickle_by_value(importlib.import_module(_mod_name))
    except ImportError:
        pass

GCP_PROJECT    = os.environ["GCP_PROJECT"]
GCP_LOCATION   = os.environ.get("GCP_LOCATION", "us-central1")
STAGING_BUCKET = os.environ.get("STAGING_BUCKET", f"gs://{GCP_PROJECT}-adk-staging")
BUCKET_NAME    = STAGING_BUCKET.removeprefix("gs://")


def ensure_staging_bucket(bucket_name: str, project: str, location: str) -> None:
    """Create the GCS staging bucket if it doesn't already exist."""
    client = storage.Client(project=project)
    bucket = client.bucket(bucket_name)
    if bucket.exists():
        print(f"Staging bucket already exists: gs://{bucket_name}")
        return
    try:
        client.create_bucket(bucket, project=project, location=location)
        print(f"Created staging bucket: gs://{bucket_name}")
    except Conflict:
        # Race condition: another process created it between exists() and create_bucket()
        print(f"Staging bucket already exists: gs://{bucket_name}")


print(f"Deploying to project={GCP_PROJECT}, location={GCP_LOCATION} ...")
print("If deployment fails, check startup logs with:")
print(f"  gcloud logging read 'resource.type=ml_job' --project={GCP_PROJECT} --limit=50 --format=json | python3 -c \"import sys,json; [print(e['jsonPayload'].get('message','')) for e in json.load(sys.stdin) if 'jsonPayload' in e]\"")
ensure_staging_bucket(BUCKET_NAME, GCP_PROJECT, GCP_LOCATION)

vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION, staging_bucket=STAGING_BUCKET)

engine = ReasoningEngine.create(
    AdkApp(agent=build_pipeline(best_practices=_load_best_practices())),
    requirements=[
        # Pin to versions that match the local environment to avoid
        # pickle/unpickle class mismatch in Agent Engine.
        "google-adk==1.29.0",
        "google-genai==1.72.0",
        "pydantic==2.12.5",
        "pydantic-settings==2.13.1",
        # litellm is only used by the FastAPI refiner, not the pipeline agents.
    ],
    display_name="intentiv-pipeline",
    extra_packages=[
        # best-practices.md is read by _load_best_practices() at local build time
        # and embedded into the architect instruction string — no runtime reads.
        "best-practices.md",
    ],
)

print("\n✓ Deployed successfully.")
print(f"\nAGENT_ENGINE_RESOURCE={engine.resource_name}\n")
print("Add this value to your Cloud Run backend environment variables.")
