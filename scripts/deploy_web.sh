#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# SVPMS Frontend Deployment Script — Google Cloud Run
# ============================================================
#
# Usage:
#   ./scripts/deploy_web.sh
#
# ============================================================
export PATH=$PATH:/Users/pacewisdom/google-cloud-sdk/bin

# ---- Configuration ----
PROJECT_ID="${GCP_PROJECT_ID:-svpms-cloud}"
REGION="${GCP_REGION:-asia-south1}"
SERVICE_NAME="svpms-web"
IMAGE_NAME="svpms-frontend"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/svpms"
IMAGE_TAG="${REGISTRY}/${IMAGE_NAME}:$(date +%Y%m%d-%H%M%S)"
IMAGE_LATEST="${REGISTRY}/${IMAGE_NAME}:latest"

echo "╔══════════════════════════════════════════════════╗"
echo "║         SVPMS Frontend Deployment               ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  Project:  ${PROJECT_ID}"
echo "║  Region:   ${REGION}"
echo "║  Service:  ${SERVICE_NAME}"
echo "║  Image:    ${IMAGE_TAG}"
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
cd web
gcloud builds submit --tag "${IMAGE_TAG}" --project "${PROJECT_ID}" .
cd ..
echo "   ✅ Image built and pushed: ${IMAGE_TAG}"

# Skip Step 4 as it's handled by Cloud Build
echo "▶ [4/5] Image already pushed by Cloud Build."

# ---- Step 5: Deploy to Cloud Run ----
echo "▶ [5/5] Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image="${IMAGE_TAG}" \
    --region="${REGION}" \
    --platform=managed \
    --port=3000 \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=3 \
    --timeout=300 \
    --allow-unauthenticated \
    --set-env-vars="NEXT_PUBLIC_API_URL=https://svpms-be-gcloud-325948496969.asia-south1.run.app" \
    --quiet

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  ✅ Deployment Complete!                        ║"
echo "╠══════════════════════════════════════════════════╣"

# Get the service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --format="value(status.url)" 2>/dev/null || echo "unknown")
echo "║  URL: ${SERVICE_URL}"
echo "╚══════════════════════════════════════════════════╝"
