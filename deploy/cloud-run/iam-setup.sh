#!/usr/bin/env bash
# One-time IAM setup for the Cloud Run backend service account.
# The service account is granted roles/aiplatform.user so it can call Agent Engine
# via Application Default Credentials — no API key needed in the container.
#
# Usage:
#   export GCP_PROJECT=your-project
#   ./deploy/cloud-run/iam-setup.sh

set -euo pipefail

: "${GCP_PROJECT:?GCP_PROJECT must be set}"

SA_NAME="intentiv-backend-sa"
SA_EMAIL="${SA_NAME}@${GCP_PROJECT}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "${SA_EMAIL}" --project "${GCP_PROJECT}" >/dev/null 2>&1; then
  echo "Service account already exists: ${SA_EMAIL}"
else
  echo "Creating service account ${SA_EMAIL}..."
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name "Intentiv Backend (Cloud Run)" \
    --project "${GCP_PROJECT}"
fi

echo "Granting roles/aiplatform.user..."
gcloud projects add-iam-policy-binding "${GCP_PROJECT}" \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/aiplatform.user"

echo ""
echo "✓ IAM setup complete. Service account: ${SA_EMAIL}"
