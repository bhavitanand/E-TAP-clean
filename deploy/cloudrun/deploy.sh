#!/usr/bin/env bash
# Deploys the E-TAP API and dashboard to Google Cloud Run.
# Usage: PROJECT_ID=my-project REGION=us-central1 ./deploy/cloudrun/deploy.sh
# Run from the repository root. The secrets listed in README.md must already exist in Secret Manager.
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID to your Google Cloud project}"
REGION="${REGION:-us-central1}"
REPO="${REPO:-etap}"
TAG="${TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}"

gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
gcloud artifacts repositories describe "$REPO" --location "$REGION" >/dev/null 2>&1 \
  || gcloud artifacts repositories create "$REPO" --repository-format docker --location "$REGION"

echo "Building and deploying the API"
gcloud builds submit backend --tag "${REGISTRY}/etap-api:${TAG}"
sed -e "s|\${IMAGE}|${REGISTRY}/etap-api:${TAG}|" \
    -e "s|\${FRONTEND_ORIGIN}|${FRONTEND_ORIGIN:-https://placeholder.invalid}|" \
    deploy/cloudrun/service.yaml > /tmp/etap-service.yaml
gcloud run services replace /tmp/etap-service.yaml --region "$REGION"
gcloud run services add-iam-policy-binding etap-api --region "$REGION" \
  --member allUsers --role roles/run.invoker >/dev/null
API_URL="$(gcloud run services describe etap-api --region "$REGION" --format 'value(status.url)')"
echo "API: ${API_URL}"

echo "Building and deploying the dashboard"
cat > /tmp/etap-frontend-build.yaml <<EOF
steps:
  - name: gcr.io/cloud-builders/docker
    args: [build, -f, deploy/cloudrun/frontend.Dockerfile, --build-arg, VITE_API_BASE_URL=${API_URL}, -t, ${REGISTRY}/etap-web:${TAG}, .]
images: [${REGISTRY}/etap-web:${TAG}]
EOF
gcloud builds submit . --config /tmp/etap-frontend-build.yaml
gcloud run deploy etap-web --image "${REGISTRY}/etap-web:${TAG}" --region "$REGION" \
  --allow-unauthenticated --port 8080 --memory 256Mi --max-instances 3
WEB_URL="$(gcloud run services describe etap-web --region "$REGION" --format 'value(status.url)')"
echo "Dashboard: ${WEB_URL}"

# The API only accepts requests from the dashboard's origin.
if [ "${FRONTEND_ORIGIN:-}" != "$WEB_URL" ]; then
  echo "Re-run with FRONTEND_ORIGIN=${WEB_URL} so the API allows the dashboard (first deploy only)."
fi
