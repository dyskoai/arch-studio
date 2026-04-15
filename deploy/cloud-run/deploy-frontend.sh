#!/usr/bin/env bash
# Deploy the Next.js frontend to Cloud Run.
#
# NEXT_PUBLIC_API_URL is baked into the JS bundle at local build time.
# The backend Cloud Run service must already be live at api-archstudio.thedysko.ai
# before building the compiled frontend.
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

# Step 1 — compile the Next.js app locally/remotely before packaging.
if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm is required for the prebuilt frontend deploy path."
  echo "Install Node.js 20+ on this machine, then rerun this script."
  exit 1
fi

echo "Building compiled frontend (NEXT_PUBLIC_API_URL=${BACKEND_URL})..."
pushd "${REPO_ROOT}/frontend" >/dev/null
mkdir -p public
NEXT_PUBLIC_API_URL="${BACKEND_URL}" npm ci
NEXT_PUBLIC_API_URL="${BACKEND_URL}" npm run build
popd >/dev/null

if [ ! -f "${REPO_ROOT}/frontend/.next/standalone/server.js" ]; then
  echo "ERROR: frontend/.next/standalone/server.js was not created."
  echo "Check that frontend/next.config.mjs uses output: \"standalone\"."
  exit 1
fi

# Step 2 — create a small Docker context from compiled output.
# gcloud builds submit can exclude .next via .gcloudignore/.gitignore defaults,
# so copy only the runtime files into an explicit temporary context.
BUILD_CONTEXT="$(mktemp -d)"
cleanup() {
  rm -rf "${BUILD_CONTEXT}"
}
trap cleanup EXIT

cp -R "${REPO_ROOT}/frontend/.next/standalone/." "${BUILD_CONTEXT}/"
mkdir -p "${BUILD_CONTEXT}/.next" "${BUILD_CONTEXT}/public"
cp -R "${REPO_ROOT}/frontend/.next/static" "${BUILD_CONTEXT}/.next/static"
cp -R "${REPO_ROOT}/frontend/public/." "${BUILD_CONTEXT}/public/"
cp "${REPO_ROOT}/frontend/Dockerfile.prebuilt" "${BUILD_CONTEXT}/Dockerfile"

# Step 3 — package and push the already-compiled frontend image.
echo "Packaging frontend image from compiled output..."
gcloud builds submit "${BUILD_CONTEXT}" \
  --tag "${IMAGE}"

# Step 4 — deploy service
echo "Deploying Cloud Run service ${SERVICE}..."
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --allow-unauthenticated

echo ""
echo "✓ Frontend deployed."
echo "Map custom domain: gcloud beta run domain-mappings create --service ${SERVICE} --domain ${FRONTEND_DOMAIN} --region ${REGION}"
