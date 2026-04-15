#!/usr/bin/env bash
# One-time IAM setup for the Cloud Run backend service account.
# The service account is granted roles/aiplatform.user so it can call Vertex AI and Agent Engine
# via Application Default Credentials — no API key needed in the container.
#
# Usage:
#   export GCP_PROJECT=your-project
#   export BACKEND_SERVICE_ACCOUNT=797664949634-compute@developer.gserviceaccount.com
#   ./deploy/cloud-run/iam-setup.sh

set -euo pipefail

: "${GCP_PROJECT:?GCP_PROJECT must be set}"

SA_EMAIL="${BACKEND_SERVICE_ACCOUNT:-797664949634-compute@developer.gserviceaccount.com}"

echo "Using backend service account: ${SA_EMAIL}"

echo "Granting roles/aiplatform.user..."
gcloud projects add-iam-policy-binding "${GCP_PROJECT}" \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/aiplatform.user"

echo ""
echo "✓ IAM setup complete. Service account: ${SA_EMAIL}"
