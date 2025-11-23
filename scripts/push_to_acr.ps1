# Script to build and push Docker images to Azure Container Registry
# Reads configuration from .env file

param(
    [string]$ImageTag = "latest"
)

$ErrorActionPreference = "Stop"

# Function to print colored output
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Error ".env file not found. Please create one with ACR_NAME and other required variables."
    exit 1
}

# Load environment variables from .env
Write-Info "Loading environment variables from .env..."
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        if ($key -and $value) {
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# Get variables
$acrName = $env:ACR_NAME
$resourceGroup = $env:AZURE_RESOURCE_GROUP
$subscriptionId = $env:AZURE_SUBSCRIPTION_ID
$ollamaModel = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "gemma3:1b" }

# Check required variables
if (-not $acrName) {
    Write-Error "ACR_NAME is not set in .env file"
    Write-Info "Please add: ACR_NAME=your-registry-name"
    exit 1
}

# Image names
$appImage = "azsre-agent"
$ollamaImage = "azsre-ollama"
$tag = $ImageTag

# Full ACR image names
$acrAppImage = "${acrName}.azurecr.io/${appImage}:${tag}"
$acrOllamaImage = "${acrName}.azurecr.io/${ollamaImage}:${tag}"

Write-Info "Configuration:"
Write-Host "  ACR Name: $acrName"
Write-Host "  App Image: $acrAppImage"
Write-Host "  Ollama Image: $acrOllamaImage"
Write-Host "  Tag: $tag"
if ($resourceGroup) {
    Write-Host "  Resource Group: $resourceGroup"
}
if ($subscriptionId) {
    Write-Host "  Subscription: $subscriptionId"
}
Write-Host ""

# Check if Azure CLI is installed
try {
    $null = Get-Command az -ErrorAction Stop
} catch {
    Write-Error "Azure CLI is not installed. Please install it first:"
    Write-Host "  https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
}

# Check if logged in to Azure
Write-Info "Checking Azure CLI authentication..."
try {
    $null = az account show 2>$null
} catch {
    Write-Warn "Not logged in to Azure. Logging in..."
    az login
}

# Set subscription if provided
if ($subscriptionId) {
    Write-Info "Setting Azure subscription to $subscriptionId..."
    az account set --subscription $subscriptionId
}

# Get resource group if not provided
if (-not $resourceGroup) {
    Write-Info "Resource group not specified, attempting to find ACR resource group..."
    $resourceGroup = az acr show --name $acrName --query "resourceGroup" -o tsv 2>$null
    if (-not $resourceGroup) {
        Write-Error "Could not find resource group for ACR $acrName"
        Write-Info "Please set AZURE_RESOURCE_GROUP in .env or ensure ACR exists"
        exit 1
    }
    Write-Info "Found resource group: $resourceGroup"
}

# Verify ACR exists
Write-Info "Verifying ACR exists..."
try {
    $null = az acr show --name $acrName --resource-group $resourceGroup 2>$null
} catch {
    Write-Error "ACR $acrName not found in resource group $resourceGroup"
    exit 1
}

# Login to ACR
Write-Info "Logging in to Azure Container Registry..."
az acr login --name $acrName

# Check if buildx is available (better for cross-platform builds)
$useBuildx = $false
try {
    $null = docker buildx version 2>$null
    Write-Info "Docker buildx detected - using for better cross-platform builds"
    $useBuildx = $true
} catch {
    Write-Warn "Docker buildx not available - using standard docker build (may be slower on ARM)"
}

# Build and push App image
# Use --platform linux/amd64 for Azure Container Apps compatibility
Write-Info "Building $appImage image for linux/amd64 platform..."
if ($useBuildx) {
    docker buildx build --platform linux/amd64 -f Dockerfile -t "${appImage}:${tag}" --load .
} else {
    docker build --platform linux/amd64 -f Dockerfile -t "${appImage}:${tag}" .
}

Write-Info "Tagging $appImage for ACR..."
docker tag "${appImage}:${tag}" $acrAppImage

Write-Info "Pushing $acrAppImage..."
docker push $acrAppImage

# Build and push Ollama image
# Use --platform linux/amd64 for Azure Container Apps compatibility
Write-Info "Building $ollamaImage image for linux/amd64 platform..."
if ($useBuildx) {
    docker buildx build --platform linux/amd64 -f Dockerfile.ollama --build-arg OLLAMA_MODEL=$ollamaModel -t "${ollamaImage}:${tag}" --load .
} else {
    docker build --platform linux/amd64 -f Dockerfile.ollama --build-arg OLLAMA_MODEL=$ollamaModel -t "${ollamaImage}:${tag}" .
}

Write-Info "Tagging $ollamaImage for ACR..."
docker tag "${ollamaImage}:${tag}" $acrOllamaImage

Write-Info "Pushing $acrOllamaImage..."
docker push $acrOllamaImage

# Summary
Write-Host ""
Write-Info "Successfully pushed images to ACR:"
Write-Host "  $acrAppImage"
Write-Host "  $acrOllamaImage"
Write-Host ""
Write-Info "To pull these images:"
Write-Host "  docker pull $acrAppImage"
Write-Host "  docker pull $acrOllamaImage"
Write-Host ""
Write-Info "To deploy to Azure Container Instances or AKS, use these image names:"
Write-Host "  App: $acrAppImage"
Write-Host "  Ollama: $acrOllamaImage"

