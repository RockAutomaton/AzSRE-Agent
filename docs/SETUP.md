## Setup Guide

This guide will help you set up the Azure SRE Agent for local development, Docker-based testing, and frontend usage.

## Prerequisites

### 1. Python 3.11+ (Backend)

The project requires Python 3.11+ (or the version specified in `pyproject.toml`). Verify your Python version:

```bash
python --version
# or
python3 --version
```

If you need to install Python 3.13, visit [python.org](https://www.python.org/downloads/) or use a version manager like `pyenv`.

### 2. Node.js (Frontend)

The React/Next.js dashboard lives in the `frontend/` directory.

```bash
node --version
npm --version
```

Install Node.js (LTS recommended) from `https://nodejs.org` if needed.

### 3. Docker (Recommended for local stack)

Docker is the recommended way to run the backend + Ollama + frontend together:

```bash
docker --version
docker compose version  # or: docker-compose --version
```

Install Docker Desktop from `https://www.docker.com/products/docker-desktop` if you don’t have it.

### 4. Azure CLI

Install the Azure CLI and authenticate:

```bash
# Install Azure CLI (macOS)
brew install azure-cli

# Install Azure CLI (Linux)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Authenticate
az login
```

Verify authentication:

```bash
az account show
```

### 5. Log Analytics Workspace

You need access to an Azure Log Analytics Workspace where your Application Insights and other monitoring data is stored.

1. Navigate to your Azure Portal
2. Find your Log Analytics Workspace
3. Copy the **Workspace ID** (you'll need this for the `LOG_WORKSPACE_ID` environment variable)

### 6. Ollama (Local LLM Server)

The agent uses Ollama to run local LLM models. Install and start Ollama:

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve

# Pull required models (in a separate terminal)
ollama pull qwen3-vl:4b
ollama pull gemma3:27b
```

**Note**: The `gemma3:27b` model is large (~15GB). Ensure you have sufficient disk space and RAM.

Verify Ollama is running:

```bash
curl http://localhost:11434/api/tags
```

## Environment Variables

Create a `.env` file in the project root with at least:

```bash
# Azure Configuration (Required)
AZURE_SUBSCRIPTION_ID=your-subscription-id-here
LOG_WORKSPACE_ID=your-workspace-id-here
APPLICATIONINSIGHTS_CONNECTION_STRING=your-app-insights-connection-string

# Azure Table Storage (Required for history & dashboard)
# Use your Storage Account table endpoint, e.g.:
#   https://<your-storage-account>.table.core.windows.net
AZURE_STORAGE_TABLE_ENDPOINT=https://<your-storage-account>.table.core.windows.net

# Ollama Configuration
OLLAMA_BASE_URL=http://ollama:11434  # when using docker-compose
# OLLAMA_BASE_URL=http://localhost:11434  # when running Ollama directly

# Optional model overrides (defaults shown)
# OLLAMA_MODEL_TRIAGE=qwen3-vl:4b
# OLLAMA_MODEL_ANALYSIS=gemma3:27b
# OLLAMA_MODEL_DATABASE=qwen3-vl:4b
# OLLAMA_MODEL_REPORTER=qwen3-vl:4b
# OLLAMA_MODEL_MAIN=gemma3:27b

# CORS Configuration
# Frontend URL(s) - comma-separated list for multiple origins
# Defaults to localhost:3000 for local development
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Frontend Configuration (for Next.js)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

The Table Storage configuration is used by:

- `app/core/database.py` for connecting to the `AlertHistory` table.
- `app/main.py` for persisting alert entities and serving `/api/history` and `/api/alerts/{row_key}`.

### Finding Your Subscription ID

```bash
az account show --query id --output tsv
```

### Finding Your Workspace ID

1. Go to Azure Portal → Log Analytics workspaces
2. Select your workspace
3. Under **Properties**, copy the **Workspace ID**

## Installation (Backend)

### Using `uv` (Recommended)

The project uses `uv` for dependency management. Install `uv` if you haven't already:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install dependencies:

```bash
# Install all dependencies
uv sync

# Or install with dev dependencies
uv sync --all-groups
```

### Using `pip` (Alternative)

If you prefer `pip`:

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Note**: If `requirements.txt` doesn't exist, you can generate it from `pyproject.toml`:

```bash
pip install -e .
```

## Frontend Setup

From the `frontend/` directory:

```bash
cd frontend
npm install
```

To run the Next.js app during development:

```bash
cd frontend
npm run dev
```

This starts the dashboard on `http://localhost:3000`.

## Running the Local Server (Backend without Docker)

### Start the FastAPI Server

```bash
# Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python
python -m app.main
```

The server will start on `http://localhost:8000`.

### Verify the Server is Running

```bash
# Check health (if you have a health endpoint)
curl http://localhost:8000/docs

# Or test the chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

## Testing with Mock Alerts

Use the provided script to send test alerts:

```bash
# Send a mock alert (uses tests/mock_payload.json by default)
python scripts/trigger_alert.py

# Or specify a custom mock file
python scripts/trigger_alert.py mock_app_payload.json
```

The script will:
1. Load the mock payload from `tests/`
2. Send it to `http://localhost:8000/webhook/azure`
3. Display the agent's classification and report

## Docker Setup (Recommended)

The project includes a `docker-compose.yml` file that sets up the agent, Ollama, and (optionally) the frontend.

### Using Docker Compose

```bash
# Build and start the stack
docker-compose up --build

# Or run in the background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

The Docker Compose setup:

- Runs the agent on port `8000`.
- Runs Ollama on port `11434`.
- Configures the agent to connect to Ollama via the `OLLAMA_BASE_URL` service name.
- Can be extended to run the frontend container (if configured in `docker-compose.yml`).

### Using Docker Directly

If you prefer to run the agent in Docker without Docker Compose:

```bash
# Build the image
docker build -t azsre-agent .

# Run the container
docker run -p 8000:8000 \
  -e AZURE_SUBSCRIPTION_ID=your-subscription-id \
  -e LOG_WORKSPACE_ID=your-workspace-id \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  azsre-agent
```

**Note**: 
- For Docker, you may need to configure Managed Identity or use environment variables for Azure authentication instead of Azure CLI
- If running Ollama separately, ensure the `OLLAMA_BASE_URL` points to the correct address (use `host.docker.internal` for local Ollama, or the container name if using Docker Compose)
- The agent container needs network access to both Azure APIs and the Ollama service

## Verifying Your Setup

1. **Check Ollama**: Ensure models are available
   ```bash
   ollama list
   ```

2. **Check Azure Authentication**: Verify you can access Azure resources
   ```bash
   az account show
   ```

3. **Check Environment Variables**: Ensure all required variables are set
   ```bash
   # In Python
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('SUB_ID:', os.getenv('AZURE_SUBSCRIPTION_ID')); print('WORKSPACE_ID:', os.getenv('LOG_WORKSPACE_ID'))"
   ```

4. **Test the Webhook**: Send a test alert
   ```bash
   python scripts/trigger_alert.py
   ```

## Common Setup Issues

### Issue: "Ollama connection refused"

**Solution**: Ensure Ollama is running:
```bash
ollama serve
```

### Issue: "AZURE_SUBSCRIPTION_ID is not set"

**Solution**: Create a `.env` file in the project root with the required variables.

### Issue: "DefaultAzureCredential failed"

**Solution**: Authenticate with Azure CLI:
```bash
az login
```

### Issue: "Model not found" (Ollama)

**Solution**: Pull the required models:
```bash
ollama pull qwen3-vl:4b
ollama pull gemma3:27b
```

## Next Steps

- Read the [Architecture Documentation](./ARCHITECTURE.md) to understand the system design
- Review [Troubleshooting Guide](./TROUBLESHOOTING.md) for common errors
- Check the [Index](./INDEX.md) for an overview of all documentation

