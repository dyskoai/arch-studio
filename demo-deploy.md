# Demo Deployment Guide

Full end-to-end deployment for the live demo:
**Frontend** (Cloud Run) → **FastAPI backend** (Cloud Run) → **Vertex AI Agent Engine**

---

## Architecture

```
Browser
  │  HTTPS  →  thedysko.ai
  ▼
Cloud Run — Next.js frontend
  │  HTTPS  →  api.thedysko.ai
  ▼
Cloud Run — FastAPI backend  (Application Default Credentials, no API key)
  │  Vertex AI SDK
  ▼
Agent Engine — ADK pipeline  (VertexAiSessionService, persistent sessions)
  │
  ▼
Gemini API  (called by Agent Engine, not by FastAPI)
```

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| `gcloud` CLI | latest | `gcloud components update` |
| Docker | any | docker.com |
| Python | 3.12+ | for running the deploy script |
| `uv` | latest | `pip install uv` |

```bash
# Authenticate
gcloud auth login
gcloud auth application-default login   # needed for Agent Engine deploy script

# Set your project
export GCP_PROJECT=your-gcp-project-id
gcloud config set project $GCP_PROJECT

# Enable required APIs (one-time)
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com
```

---

## Step 1 — IAM Setup (one-time)

Creates the service account the backend Cloud Run service runs as.
It needs `roles/aiplatform.user` to call Agent Engine via ADC — **no API key in the container**.

```bash
cd acrh-studio
chmod +x deploy/cloud-run/iam-setup.sh
./deploy/cloud-run/iam-setup.sh
```

What it does:
- Creates service account `intentiv-backend-sa@$GCP_PROJECT.iam.gserviceaccount.com`
- Grants `roles/aiplatform.user` so it can call Vertex AI Agent Engine

---

## Step 2 — Store the Gemini API Key in Secret Manager (one-time)

The API key is used by Agent Engine internally when it calls Gemini.
Store it so the deploy script can reference it:

```bash
# Create the secret
echo -n "YOUR_GOOGLE_API_KEY" | \
  gcloud secrets create dysko-google-api-key \
    --data-file=- \
    --replication-policy=automatic

# Verify
gcloud secrets versions access latest --secret=dysko-google-api-key
```

> **Note:** In demo mode (`USE_AGENT_ENGINE=true`) the FastAPI backend does **not** call Gemini directly — Agent Engine does. This secret is stored for reference and future fallback use only.

---

## Step 3 — Deploy the Pipeline to Agent Engine (one-time)

Packages the ADK SequentialAgent (router → architect → validator) and deploys it
to Vertex AI as a managed agent. This takes ~5 minutes.

```bash
cd acrh-studio

# Install backend deps (needed to import pipeline modules)
cd backend && uv pip install -r pyproject.toml --system && cd ..

# Deploy (creates the GCS staging bucket automatically if it doesn't exist)
GCP_PROJECT=$GCP_PROJECT python deploy/agent-engine/deploy.py
```

> To use a custom staging bucket: `STAGING_BUCKET=gs://my-bucket GCP_PROJECT=$GCP_PROJECT python deploy/agent-engine/deploy.py`

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
and deploys to Cloud Run. The service authenticates to Agent Engine via ADC.

```bash
cd acrh-studio
chmod +x deploy/cloud-run/deploy-backend.sh
./deploy/cloud-run/deploy-backend.sh
```

**After deploy, map the custom domain:**
```bash
gcloud beta run domain-mappings create \
  --service intentiv-backend \
  --domain api.thedysko.ai \
  --region us-central1
```

Follow the DNS instructions printed by the command (add a CNAME or A record to your DNS provider).

**Verify:**
```bash
curl https://api.thedysko.ai/health
# → {"status":"ok","version":"3.0.0"}
```

---

## Step 5 — Deploy the Frontend (Cloud Run)

`NEXT_PUBLIC_API_URL` is baked into the JS bundle at build time, so the backend
must be live at `api.thedysko.ai` **before** building the frontend image.

```bash
cd acrh-studio
chmod +x deploy/cloud-run/deploy-frontend.sh
./deploy/cloud-run/deploy-frontend.sh
```

**After deploy, map the custom domain:**
```bash
gcloud beta run domain-mappings create \
  --service intentiv-frontend \
  --domain thedysko.ai \
  --region us-central1
```

Add the DNS record from the output to your DNS provider.

---

## Step 6 — Verify End-to-End

```bash
# 1. Backend health
curl https://api.thedysko.ai/health

# 2. Refine endpoint (Phase 1)
curl -s -X POST https://api.thedysko.ai/refine \
  -H "Content-Type: application/json" \
  -d '{"rough_input": "customer support chatbot with memory"}' | jq .

# 3. Generate endpoint (Phase 2 — calls Agent Engine)
curl -s -X POST https://api.thedysko.ai/generate \
  -H "Content-Type: application/json" \
  -d '{"refined_spec": "Build a customer support chatbot that remembers conversation history across sessions and routes queries to specialist agents for billing, shipping, and returns."}' | jq .

# 4. Open the app
open https://thedysko.ai
```

The `/generate` response should include `meta.stages.total_ms` — this confirms
the pipeline ran through Agent Engine.

---

## Re-deploy Cheatsheet

| What changed | Command |
|---|---|
| Frontend code | `./deploy/cloud-run/deploy-frontend.sh` |
| FastAPI routes / exporters | `./deploy/cloud-run/deploy-backend.sh` |
| Agent prompts / schemas / best-practices.md | `python deploy/agent-engine/deploy.py` → update `AGENT_ENGINE_RESOURCE` → `./deploy/cloud-run/deploy-backend.sh` |
| Both frontend and backend | Run both deploy scripts |

---

## Environment Variables Reference

### Backend Cloud Run service
| Variable | Value | Notes |
|---|---|---|
| `ENV` | `production` | Disables `/docs` |
| `USE_AGENT_ENGINE` | `true` | Routes pipeline to Agent Engine |
| `GCP_PROJECT` | `your-project-id` | |
| `GCP_LOCATION` | `us-central1` | |
| `AGENT_ENGINE_RESOURCE` | `projects/.../reasoningEngines/NNN` | From Step 3 output |
| `ALLOWED_ORIGINS` | `https://thedysko.ai` | CORS |

### Frontend Cloud Run service (build-time arg)
| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://api.thedysko.ai` |

---

## OSS Self-Hosting (no GCP)

The open-source version requires only a `GOOGLE_API_KEY` and Docker:

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — add GOOGLE_API_KEY=your-key
docker-compose up --build
# → http://localhost:3000
```
