#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# SVPMS Backend Deployment Script — Google Cloud Run
# ============================================================
#
# Usage:
#   ./scripts/deploy.sh              # Deploy backend
#   ./scripts/deploy.sh --dry-run    # Build only, don't deploy
#
# Prerequisites:
#   - gcloud CLI authenticated (`gcloud auth login`)
#   - Docker daemon running
#   - GCP project configured
# ============================================================
export PATH=$PATH:/Users/pacewisdom/google-cloud-sdk/bin

# ---- Configuration ----
PROJECT_ID="${GCP_PROJECT_ID:-svpms-cloud}"
REGION="${GCP_REGION:-asia-south1}"
SERVICE_NAME="svpms-api"
IMAGE_NAME="svpms-backend"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/svpms"
IMAGE_TAG="${REGISTRY}/${IMAGE_NAME}:$(date +%Y%m%d-%H%M%S)"
IMAGE_LATEST="${REGISTRY}/${IMAGE_NAME}:latest"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

echo "╔══════════════════════════════════════════════════╗"
echo "║         SVPMS Backend Deployment                ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  Project:  ${PROJECT_ID}"
echo "║  Region:   ${REGION}"
echo "║  Service:  ${SERVICE_NAME}"
echo "║  Image:    ${IMAGE_TAG}"
echo "║  Dry Run:  ${DRY_RUN}"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ---- Step 1: Set GCP project ----
echo "▶ [1/5] Setting GCP project..."
gcloud config set project "${PROJECT_ID}"

# ---- Step 2: Ensure Artifact Registry repo exists ----
echo "▶ [2/5] Ensuring Artifact Registry repository exists..."
gcloud artifacts repositories describe svpms --location="${REGION}" 2>/dev/null || \
    gcloud artifacts repositories create svpms \
        --repository-format=docker \
        --location="${REGION}" \
        --description="SVPMS Docker images"

# ---- Step 3: Build Docker image ----
# ---- Step 3: Build and Push with Cloud Build ----
echo "▶ [3/5] Building and Pushing with Cloud Build..."
gcloud builds submit --tag "${IMAGE_TAG}" --project "${PROJECT_ID}" .
echo "   ✅ Image built and pushed: ${IMAGE_TAG}"

if [ "${DRY_RUN}" = true ]; then
    echo ""
    echo "🏁 Dry run complete."
    exit 0
fi

# Skip Step 4 as it's handled by Cloud Build
echo "▶ [4/5] Image already pushed by Cloud Build."

# ---- Step 5: Deploy to Cloud Run ----
echo "▶ [5/5] Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image="${IMAGE_TAG}" \
    --region="${REGION}" \
    --platform=managed \
    --port=8080 \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=3 \
    --timeout=300 \
    --allow-unauthenticated \
    --set-env-vars="ENVIRONMENT=production,APP_VERSION=$(date +%Y%m%d)" \
    --quiet

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  ✅ Deployment Complete!                        ║"
echo "╠══════════════════════════════════════════════════╣"

# Get the service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --format="value(status.url)" 2>/dev/null || echo "unknown")
echo "║  URL: ${SERVICE_URL}"
echo "╚══════════════════════════════════════════════════╝"

# ---- Smoke test ----
echo ""
echo "▶ Running smoke test..."
if curl -s --max-time 10 "${SERVICE_URL}/health" | grep -q "healthy"; then
    echo "   ✅ Health check passed!"
else
    echo "   ⚠️  Health check failed or timed out"
fi
