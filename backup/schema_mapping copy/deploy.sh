#!/bin/bash
# Deployment script for Schema Mapping API to Google Cloud Run

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-ccibt-hack25ww7-750}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="schema-mapping-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=========================================="
echo "Deploying Schema Mapping API to Cloud Run"
echo "=========================================="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "=========================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found. Please install it first."
    exit 1
fi

# Set the project
echo "Setting GCP project..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    aiplatform.googleapis.com \
    bigquery.googleapis.com

# Build the container image
echo "Building container image..."
gcloud builds submit \
    --tag ${IMAGE_NAME} \
    --timeout=20m \
    .

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},GOOGLE_GENAI_USE_VERTEXAI=1" \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --format 'value(status.url)')

echo ""
echo "=========================================="
echo "✅ Deployment successful!"
echo "=========================================="
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Test the API:"
echo "  Health check:"
echo "    curl ${SERVICE_URL}/health"
echo ""
echo "  Generate mapping:"
echo "    curl -X POST ${SERVICE_URL}/generate-mapping \\"
echo "      -H 'Content-Type: application/json' \\"
echo "      -d '{\"source_dataset\":\"staging\",\"target_dataset\":\"prod\",\"mode\":\"FIX\"}'"
echo ""
echo "  API documentation:"
echo "    ${SERVICE_URL}/docs"
echo "=========================================="
