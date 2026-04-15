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

REGION="us-central1"
SERVICE="intentiv-backend"
IMAGE="gcr.io/${GCP_PROJECT}/${SERVICE}"

# Step 1 — build and push backend image (build context = repo root)
echo "Building backend image..."
gcloud builds submit ../.. \
  --tag "${IMAGE}" \
  --config deploy/cloud-run/cloudbuild-backend.yaml

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
AGENT_ENGINE_RESOURCE=${AGENT_ENGINE_RESOURCE},\
ALLOWED_ORIGINS=https://thedysko.ai"

echo ""
echo "✓ Backend deployed."
echo "Map custom domain: gcloud beta run domain-mappings create --service ${SERVICE} --domain api.thedysko.ai --region ${REGION}"
