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

# ---- Configuration ----
PROJECT_ID="${GCP_PROJECT_ID:-325948496969}"
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
echo "▶ [3/5] Building Docker image (this may take a while)..."
# Build from the web directory
cd web
docker build -t "${IMAGE_TAG}" -t "${IMAGE_LATEST}" .
cd ..
echo "   ✅ Image built: ${IMAGE_TAG}"

# ---- Step 4: Push to Artifact Registry ----
echo "▶ [4/5] Pushing to Artifact Registry..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
docker push "${IMAGE_TAG}"
docker push "${IMAGE_LATEST}"
echo "   ✅ Image pushed"

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
    --set-env-vars="NEXT_PUBLIC_API_URL=https://svpms-api-4z654654-el.a.run.app" \
    --quiet

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  ✅ Deployment Complete!                        ║"
echo "╠══════════════════════════════════════════════════╣"

# Get the service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --format="value(status.url)" 2>/dev/null || echo "unknown")
echo "║  URL: ${SERVICE_URL}"
echo "╚══════════════════════════════════════════════════╝"
