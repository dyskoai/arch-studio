#!/usr/bin/env bash
# Deploy the FastAPI backend to Cloud Run.
#
# Prerequisites:
#   - gcloud CLI authenticated
#   - AGENT_ENGINE_RESOURCE exported (from deploy/agent-engine/deploy.py output)
#   - GCP_PROJECT exported
#   - BACKEND_SERVICE_ACCOUNT has roles/aiplatform.user
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
BACKEND_SERVICE_ACCOUNT="${BACKEND_SERVICE_ACCOUNT:-797664949634-compute@developer.gserviceaccount.com}"
FRONTEND_DOMAIN="${FRONTEND_DOMAIN:-archstudio.thedysko.ai}"
API_DOMAIN="${API_DOMAIN:-api-archstudio.thedysko.ai}"
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
echo "Using service account: ${BACKEND_SERVICE_ACCOUNT}"
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --service-account "${BACKEND_SERVICE_ACCOUNT}" \
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
ALLOWED_ORIGINS=https://${FRONTEND_DOMAIN}"

echo ""
echo "✓ Backend deployed."
echo "Map custom domain: gcloud beta run domain-mappings create --service ${SERVICE} --domain ${API_DOMAIN} --region ${REGION}"
