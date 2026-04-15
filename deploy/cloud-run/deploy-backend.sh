#!/usr/bin/env bash
# Deploy the FastAPI backend to Cloud Run.
#
# Prerequisites:
#   - gcloud CLI authenticated
#   - AGENT_ENGINE_RESOURCE exported (from deploy/agent-engine/deploy.py output)
#   - GCP_PROJECT exported
#   - Secret Manager secret "intentiv-google-api-key" created
#     (only needed if USE_AGENT_ENGINE=false; Agent Engine uses ADC internally)
#
# Usage:
#   export GCP_PROJECT=your-project
#   export AGENT_ENGINE_RESOURCE=projects/.../reasoningEngines/NNN
#   ./deploy/cloud-run/deploy-backend.sh

set -euo pipefail

: "${GCP_PROJECT:?GCP_PROJECT must be set}"
: "${AGENT_ENGINE_RESOURCE:?AGENT_ENGINE_RESOURCE must be set}"

REGION="${GCP_LOCATION:-us-central1}"
SERVICE="intentiv-backend"
IMAGE="gcr.io/${GCP_PROJECT}/${SERVICE}"
REFINER_MODEL="${REFINER_MODEL:-gemini-3.1-flash-lite-preview}"
ROUTER_MODEL="${ROUTER_MODEL:-gemini-3.1-flash-lite-preview}"
ARCHITECT_MODEL="${ARCHITECT_MODEL:-gemini-3.1-pro-preview}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Step 1 — build and push backend image (build context = repo root)
echo "Building backend image..."
gcloud builds submit "${REPO_ROOT}" \
  --substitutions "_IMAGE=${IMAGE}" \
  --config "${REPO_ROOT}/deploy/cloud-run/cloudbuild-backend.yaml"

# Step 2 — deploy service
echo "Deploying Cloud Run service ${SERVICE}..."
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --service-account "intentiv-backend-sa@${GCP_PROJECT}.iam.gserviceaccount.com" \
  --set-env-vars "\
ENV=production,\
USE_AGENT_ENGINE=true,\
GCP_PROJECT=${GCP_PROJECT},\
GCP_LOCATION=${REGION},\
REFINER_MODEL=${REFINER_MODEL},\
ROUTER_MODEL=${ROUTER_MODEL},\
ARCHITECT_MODEL=${ARCHITECT_MODEL},\
GOOGLE_GENAI_USE_VERTEXAI=true,\
GOOGLE_CLOUD_PROJECT=${GCP_PROJECT},\
GOOGLE_CLOUD_LOCATION=${REGION},\
AGENT_ENGINE_RESOURCE=${AGENT_ENGINE_RESOURCE},\
ALLOWED_ORIGINS=https://thedysko.ai"

echo ""
echo "✓ Backend deployed."
echo "Map custom domain: gcloud beta run domain-mappings create --service ${SERVICE} --domain api.thedysko.ai --region ${REGION}"
