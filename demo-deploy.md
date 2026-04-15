# Demo Deployment Guide

Full end-to-end deployment for the live demo:
**Frontend** (Cloud Run) → **FastAPI backend** (Cloud Run) → **Vertex AI Agent Engine**

---

## Architecture

```
Browser
  │  HTTPS  →  archstudio.thedysko.ai
  ▼
Cloud Run — Next.js frontend
  │  HTTPS  →  api-archstudio.thedysko.ai
  ▼
Cloud Run — FastAPI backend  (ADC, no API key)
  │  ├─ /refine   → Vertex AI Gemini
  │  └─ /generate → Vertex AI Agent Engine
  ▼
Agent Engine — ADK pipeline  (router → architect → validator)
  │
  ▼
Vertex AI Gemini
```

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| `gcloud` CLI | latest | `gcloud components update` |
| Python | 3.12+ | for running the deploy script |
| `uv` | latest | `pip install uv` |
| Node.js/npm | Node 20+ | required for frontend prebuild deploy |
| `jq` | optional | only used for pretty-printing verification responses |

This guide is safe to run from a remote machine. It does not depend on your
local `backend/.env`; production values are passed through shell environment
variables and Cloud Run service configuration.

If your local `backend/.env` contains model overrides, copy those values into
the remote shell exports below before deploying.

Clone the repo on the remote machine first:

```bash
git clone <your-repo-url> acrh-studio
cd acrh-studio
```

```bash
# Authenticate
gcloud auth login
gcloud auth application-default login   # needed for Agent Engine deploy script

# Set your project
export GCP_PROJECT=your-gcp-project-id
export GCP_LOCATION=us-central1
export MODEL_LOCATION=global
export REFINER_MODEL=your-refiner-model
export ROUTER_MODEL=your-router-model
export ARCHITECT_MODEL=your-architect-model
export FRONTEND_DOMAIN=archstudio.thedysko.ai
export API_DOMAIN=api-archstudio.thedysko.ai
export BACKEND_SERVICE_ACCOUNT=797664949634-compute@developer.gserviceaccount.com
gcloud config set project "$GCP_PROJECT"
gcloud auth application-default set-quota-project "$GCP_PROJECT"

# Enable required APIs (one-time)
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com
```

---

## Step 1 — IAM Setup (one-time)

Grants the backend Cloud Run service account `roles/aiplatform.user` so it can
call Vertex AI and Agent Engine via ADC — **no API key in the container**.

```bash
cd acrh-studio
chmod +x deploy/cloud-run/iam-setup.sh
./deploy/cloud-run/iam-setup.sh
```

What it does:
- Uses `BACKEND_SERVICE_ACCOUNT`, defaulting to `797664949634-compute@developer.gserviceaccount.com`
- Grants `roles/aiplatform.user` so it can call Vertex AI and Agent Engine

---

## Step 2 — Production Auth Model

Production uses Vertex AI through Application Default Credentials:

- The backend Cloud Run service runs as `797664949634-compute@developer.gserviceaccount.com`.
- `/refine` calls Gemini from the backend with Vertex AI ADC.
- `/generate` calls the deployed Agent Engine resource with Vertex AI ADC.
- The deployed Agent Engine app also calls Gemini through Vertex AI ADC.

No Gemini API key or Secret Manager secret is required for this production path.

---

## Step 3 — Deploy the Pipeline to Agent Engine (one-time)

Packages the ADK SequentialAgent (router → architect → validator) and deploys it
to Vertex AI as a managed agent. This takes ~5 minutes.

```bash
cd acrh-studio

# Create/update the backend virtualenv used by the deploy script
uv sync --project backend

# Deploy (creates the GCS staging bucket automatically if it doesn't exist)
GCP_PROJECT=$GCP_PROJECT GCP_LOCATION=$GCP_LOCATION MODEL_LOCATION=$MODEL_LOCATION uv run --project backend python deploy/agent-engine/deploy.py
```

> To use a custom staging bucket: `STAGING_BUCKET=gs://my-bucket GCP_PROJECT=$GCP_PROJECT GCP_LOCATION=$GCP_LOCATION MODEL_LOCATION=$MODEL_LOCATION uv run --project backend python deploy/agent-engine/deploy.py`

**Expected output:**
```
Deploying to project=your-project, location=us-central1 ...
✓ Deployed successfully.

AGENT_ENGINE_RESOURCE=projects/123456/locations/us-central1/reasoningEngines/789

Add this value to your Cloud Run backend environment variables.
```

```bash
# Export for the next steps
export AGENT_ENGINE_RESOURCE=projects/123456/locations/us-central1/reasoningEngines/789
```

> Re-deploy Agent Engine only when agent logic changes (router/architect/validator prompts, schemas, best-practices.md). Normal code changes to FastAPI or frontend do **not** require re-deploying Agent Engine.

---

## Step 4 — Deploy the Backend (Cloud Run)

Builds the FastAPI image from the repo root (so `best-practices.md` is included)
and deploys to Cloud Run. The service authenticates to Vertex AI and Agent
Engine through the Cloud Run service account.

```bash
chmod +x deploy/cloud-run/deploy-backend.sh
./deploy/cloud-run/deploy-backend.sh
```

The script sets the production Vertex AI env vars required by ADK:

- `GOOGLE_GENAI_USE_VERTEXAI=true`
- `GOOGLE_CLOUD_PROJECT=$GCP_PROJECT`
- `GOOGLE_CLOUD_LOCATION=global`

**After deploy, map the custom domain:**
```bash
gcloud beta run domain-mappings create \
  --service intentiv-backend \
  --domain api-archstudio.thedysko.ai \
  --region us-central1
```

Follow the DNS instructions printed by the command (add a CNAME or A record to your DNS provider).

**Verify:**
```bash
curl https://api-archstudio.thedysko.ai/health
# → {"status":"ok","version":"3.0.0"}
```

---

## Step 5 — Deploy the Frontend (Cloud Run)

`NEXT_PUBLIC_API_URL` is baked into the JS bundle at build time. This script
builds the Next.js app on the remote machine first, then Cloud Build only
packages the compiled `.next/standalone` output into a runtime image. The
backend must be live at `api-archstudio.thedysko.ai` before running it.

```bash
chmod +x deploy/cloud-run/deploy-frontend.sh
./deploy/cloud-run/deploy-frontend.sh
```

For a non-default backend domain, override the build-time API URL:

```bash
NEXT_PUBLIC_API_URL=https://your-api-domain ./deploy/cloud-run/deploy-frontend.sh
```

**After deploy, map the custom domain:**
```bash
gcloud beta run domain-mappings create \
  --service intentiv-frontend \
  --domain archstudio.thedysko.ai \
  --region us-central1
```

Add the DNS record from the output to your DNS provider.

---

## Step 6 — Verify End-to-End

```bash
# 1. Backend health
curl https://api-archstudio.thedysko.ai/health

# 2. Refine endpoint (Phase 1)
curl -s -X POST https://api-archstudio.thedysko.ai/refine \
  -H "Content-Type: application/json" \
  -d '{"rough_input": "customer support chatbot with memory"}' | jq .

# 3. Generate endpoint (Phase 2 — calls Agent Engine)
curl -s -X POST https://api-archstudio.thedysko.ai/generate \
  -H "Content-Type: application/json" \
  -d '{"refined_spec": "Build a customer support chatbot that remembers conversation history across sessions and routes queries to specialist agents for billing, shipping, and returns."}' | jq .

# 4. Open the app
# Open https://archstudio.thedysko.ai in a browser
```

The `/generate` response should include `meta.stages.total_ms` — this confirms
the pipeline ran through Agent Engine.

The `/refine` response confirms the backend service account can call Gemini
through Vertex AI ADC.

---

## Re-deploy Cheatsheet

| What changed | Command |
|---|---|
| Frontend code | `./deploy/cloud-run/deploy-frontend.sh` |
| FastAPI routes / exporters | `./deploy/cloud-run/deploy-backend.sh` |
| Agent prompts / schemas / best-practices.md | `uv run --project backend python deploy/agent-engine/deploy.py` → update `AGENT_ENGINE_RESOURCE` → `./deploy/cloud-run/deploy-backend.sh` |
| Both frontend and backend | Run both deploy scripts |

---

## Environment Variables Reference

### Backend Cloud Run service
| Variable | Value | Notes |
|---|---|---|
| `ENV` | `production` | Disables `/docs` |
| `USE_AGENT_ENGINE` | `true` | Routes pipeline to Agent Engine |
| `GCP_PROJECT` | `your-project-id` | |
| `GCP_LOCATION` | `us-central1` | Cloud Run and Agent Engine location |
| `MODEL_LOCATION` | `global` | Vertex AI Gemini model location |
| `REFINER_MODEL` | production model name | Used by `/refine` in Cloud Run |
| `ROUTER_MODEL` | production model name | Baked into the deployed Agent Engine pipeline |
| `ARCHITECT_MODEL` | production model name | Baked into the deployed Agent Engine pipeline |
| `BACKEND_SERVICE_ACCOUNT` | `797664949634-compute@developer.gserviceaccount.com` | Cloud Run runtime identity |
| `GOOGLE_GENAI_USE_VERTEXAI` | `true` | Lets ADK use Vertex AI instead of an API key |
| `GOOGLE_CLOUD_PROJECT` | `your-project-id` | Required by Google GenAI/ADK Vertex mode |
| `GOOGLE_CLOUD_LOCATION` | `global` | Required by Google GenAI/ADK Vertex mode |
| `AGENT_ENGINE_RESOURCE` | `projects/.../reasoningEngines/NNN` | From Step 3 output |
| `ALLOWED_ORIGINS` | `https://archstudio.thedysko.ai` | CORS |

### Frontend Cloud Run service (build-time arg)
| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://api-archstudio.thedysko.ai` |

---

## OSS Self-Hosting (no GCP)

The open-source version requires only a `GOOGLE_API_KEY` and Docker:

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — add GOOGLE_API_KEY=your-key
docker-compose up --build
# → http://localhost:3000
```
