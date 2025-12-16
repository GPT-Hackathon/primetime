#!/bin/bash
# Deploy Data Validation Agent to Google Cloud Run
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Docker installed (for local testing)
#   - GCP project with Cloud Run, BigQuery, and Vertex AI APIs enabled

set -e

# Configuration - UPDATE THESE VALUES
PROJECT_ID="${GCP_PROJECT_ID:-ccibt-hack25ww7-750}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="data-validation-agent"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "================================================"
echo "Data Validation Agent - Cloud Run Deployment"
echo "================================================"
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service Name: ${SERVICE_NAME}"
echo "================================================"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set the project
echo ""
echo "Setting GCP project..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo ""
echo "Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    bigquery.googleapis.com \
    aiplatform.googleapis.com

# Build and push the container image using Cloud Build
echo ""
echo "Building and pushing container image..."
gcloud builds submit --tag ${IMAGE_NAME} .

# Deploy to Cloud Run
echo ""
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION}" \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0

# Get the service URL
echo ""
echo "================================================"
echo "Deployment Complete!"
echo "================================================"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Test the API:"
echo "  curl ${SERVICE_URL}/health"
echo ""
echo "Validate data:"
echo "  curl -X POST ${SERVICE_URL}/validate \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"schema_mapping\": {...}, \"mode\": \"REPORT\"}'"
echo "================================================"
