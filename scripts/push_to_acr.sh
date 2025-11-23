#!/bin/bash

# Script to build and push Docker images to Azure Container Registry
# Reads configuration from .env file

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found. Please create one with ACR_NAME and other required variables."
    exit 1
fi

# Load environment variables from .env
print_info "Loading environment variables from .env..."
export $(grep -v '^#' .env | xargs)

# Check required variables
if [ -z "$ACR_NAME" ]; then
    print_error "ACR_NAME is not set in .env file"
    print_info "Please add: ACR_NAME=your-registry-name"
    exit 1
fi

# Optional: Resource group (if not set, will try to find it)
RESOURCE_GROUP=${AZURE_RESOURCE_GROUP:-""}
SUBSCRIPTION_ID=${AZURE_SUBSCRIPTION_ID:-""}

# Image names and tags
APP_IMAGE="azsre-agent"
OLLAMA_IMAGE="azsre-ollama"
TAG=${IMAGE_TAG:-"latest"}

# Full ACR image names
ACR_APP_IMAGE="${ACR_NAME}.azurecr.io/${APP_IMAGE}:${TAG}"
ACR_OLLAMA_IMAGE="${ACR_NAME}.azurecr.io/${OLLAMA_IMAGE}:${TAG}"

print_info "Configuration:"
echo "  ACR Name: ${ACR_NAME}"
echo "  App Image: ${ACR_APP_IMAGE}"
echo "  Ollama Image: ${ACR_OLLAMA_IMAGE}"
echo "  Tag: ${TAG}"
if [ -n "$RESOURCE_GROUP" ]; then
    echo "  Resource Group: ${RESOURCE_GROUP}"
fi
if [ -n "$SUBSCRIPTION_ID" ]; then
    echo "  Subscription: ${SUBSCRIPTION_ID}"
fi
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    print_error "Azure CLI is not installed. Please install it first:"
    echo "  https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in to Azure
print_info "Checking Azure CLI authentication..."
if ! az account show &> /dev/null; then
    print_warn "Not logged in to Azure. Logging in..."
    az login
fi

# Set subscription if provided
if [ -n "$SUBSCRIPTION_ID" ]; then
    print_info "Setting Azure subscription to ${SUBSCRIPTION_ID}..."
    az account set --subscription "${SUBSCRIPTION_ID}"
fi

# Get resource group if not provided
if [ -z "$RESOURCE_GROUP" ]; then
    print_info "Resource group not specified, attempting to find ACR resource group..."
    RESOURCE_GROUP=$(az acr show --name "${ACR_NAME}" --query "resourceGroup" -o tsv 2>/dev/null || echo "")
    if [ -z "$RESOURCE_GROUP" ]; then
        print_error "Could not find resource group for ACR ${ACR_NAME}"
        print_info "Please set AZURE_RESOURCE_GROUP in .env or ensure ACR exists"
        exit 1
    fi
    print_info "Found resource group: ${RESOURCE_GROUP}"
fi

# Verify ACR exists
print_info "Verifying ACR exists..."
if ! az acr show --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" &> /dev/null; then
    print_error "ACR ${ACR_NAME} not found in resource group ${RESOURCE_GROUP}"
    exit 1
fi

# Login to ACR
print_info "Logging in to Azure Container Registry..."
az acr login --name "${ACR_NAME}"

# Check if buildx is available (better for cross-platform builds)
if docker buildx version &> /dev/null; then
    print_info "Docker buildx detected - using for better cross-platform builds"
    USE_BUILDX=true
else
    print_warn "Docker buildx not available - using standard docker build (may be slower on ARM)"
    USE_BUILDX=false
fi

# Build and push App image
# Use --platform linux/amd64 for Azure Container Apps compatibility
print_info "Building ${APP_IMAGE} image for linux/amd64 platform..."
if [ "$USE_BUILDX" = true ]; then
    docker buildx build --platform linux/amd64 -f Dockerfile -t "${APP_IMAGE}:${TAG}" --load .
else
    docker build --platform linux/amd64 -f Dockerfile -t "${APP_IMAGE}:${TAG}" .
fi

print_info "Tagging ${APP_IMAGE} for ACR..."
docker tag "${APP_IMAGE}:${TAG}" "${ACR_APP_IMAGE}"

print_info "Pushing ${ACR_APP_IMAGE}..."
docker push "${ACR_APP_IMAGE}"

# Build and push Ollama image
# Use --platform linux/amd64 for Azure Container Apps compatibility
print_info "Building ${OLLAMA_IMAGE} image for linux/amd64 platform..."
# Get OLLAMA_MODEL from .env or use default
OLLAMA_MODEL=${OLLAMA_MODEL:-"gemma3:1b"}
if [ "$USE_BUILDX" = true ]; then
    docker buildx build --platform linux/amd64 -f Dockerfile.ollama --build-arg OLLAMA_MODEL="${OLLAMA_MODEL}" -t "${OLLAMA_IMAGE}:${TAG}" --load .
else
    docker build --platform linux/amd64 -f Dockerfile.ollama --build-arg OLLAMA_MODEL="${OLLAMA_MODEL}" -t "${OLLAMA_IMAGE}:${TAG}" .
fi

print_info "Tagging ${OLLAMA_IMAGE} for ACR..."
docker tag "${OLLAMA_IMAGE}:${TAG}" "${ACR_OLLAMA_IMAGE}"

print_info "Pushing ${ACR_OLLAMA_IMAGE}..."
docker push "${ACR_OLLAMA_IMAGE}"

# Summary
echo ""
print_info "✅ Successfully pushed images to ACR:"
echo "  ${ACR_APP_IMAGE}"
echo "  ${ACR_OLLAMA_IMAGE}"
echo ""
print_info "To pull these images:"
echo "  docker pull ${ACR_APP_IMAGE}"
echo "  docker pull ${ACR_OLLAMA_IMAGE}"
echo ""
print_info "To deploy to Azure Container Instances or AKS, use these image names:"
echo "  App: ${ACR_APP_IMAGE}"
echo "  Ollama: ${ACR_OLLAMA_IMAGE}"

