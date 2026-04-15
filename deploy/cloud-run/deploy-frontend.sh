#!/usr/bin/env bash
# Deploy the Next.js frontend to Cloud Run.
#
# NEXT_PUBLIC_API_URL is baked into the JS bundle at build time.
# The backend Cloud Run service must already be live at api-archstudio.thedysko.ai
# before building the frontend image.
#
# Usage:
#   export GCP_PROJECT=your-project
#   ./deploy/cloud-run/deploy-frontend.sh

set -euo pipefail

: "${GCP_PROJECT:?GCP_PROJECT must be set}"

REGION="${GCP_LOCATION:-us-central1}"
SERVICE="intentiv-frontend"
IMAGE="gcr.io/${GCP_PROJECT}/${SERVICE}"
FRONTEND_DOMAIN="${FRONTEND_DOMAIN:-archstudio.thedysko.ai}"
API_DOMAIN="${API_DOMAIN:-api-archstudio.thedysko.ai}"
BACKEND_URL="${NEXT_PUBLIC_API_URL:-https://${API_DOMAIN}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Step 1 — build and push frontend image with API URL baked in
echo "Building frontend image (NEXT_PUBLIC_API_URL=${BACKEND_URL})..."
gcloud builds submit "${REPO_ROOT}" \
  --substitutions "_IMAGE=${IMAGE},_NEXT_PUBLIC_API_URL=${BACKEND_URL}" \
  --config "${REPO_ROOT}/deploy/cloud-run/cloudbuild-frontend.yaml"

# Step 2 — deploy service
echo "Deploying Cloud Run service ${SERVICE}..."
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --allow-unauthenticated

echo ""
echo "✓ Frontend deployed."
echo "Map custom domain: gcloud beta run domain-mappings create --service ${SERVICE} --domain ${FRONTEND_DOMAIN} --region ${REGION}"
