# Azure Alert AI Agent 🤖

An AI-powered Tier 1 responder for Azure Monitor Alerts, built with LangGraph, FastAPI, and local LLMs (Ollama).

## 🏗 Architecture

1. **Webhook Receiver:** FastAPI endpoint accepts Azure Common Alert Schema.
2. **Triage Agent:** Classifies alert (Infra, DB, App) using `qwen3-vl:4b`.
3. **Specialist Agents:**
   * *Infra:* Queries KQL for logs.
   * *DB:* Checks SQL Metrics (DTU/CPU).
   * *App:* Checks App Insights Exceptions.
4. **Reporter:** Synthesizes a human-readable summary.

## 🚀 Quick Start

### 1. Prerequisites

* Docker & Docker Compose
* Python 3.11+ (for running test scripts)

### 2. Environment Setup

Create a `.env` file:

```bash
# Azure Auth (Use Service Principal for Dev)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_SUBSCRIPTION_ID=your-sub-id

# Log Analytics Workspace ID (for KQL queries)
LOG_WORKSPACE_ID=your-workspace-uuid
```

### 3. Run the Stack

Start the API and the Ollama LLM container:

```bash
docker-compose up --build
```

**Note:** On first run, Ollama needs to pull the model. You may need to run:

```bash
docker exec -it azure-agent-ollama-1 ollama pull qwen3-vl:4b
```

### 4. Simulate an Alert

In a new terminal, run the simulation script:

```bash
pip install requests
python scripts/trigger_alert.py
```

## 📂 Folder Structure

```
app/
├── graph/          # The LangGraph workflow logic
│   └── nodes/      # The individual AI agents
├── tools/          # Azure SDK integrations
├── schemas/        # Pydantic models for Azure alerts
└── core/           # Core utilities (auth, etc.)
```

## 🔧 Development

### Running Locally

```bash
# Install dependencies
uv sync

# Run the API
uvicorn app.main:app --reload
```

### Testing

Use the mock payload in `tests/mock_payload.json` to test the workflow:

```bash
python scripts/trigger_alert.py
```

## 📝 API Endpoints

* `POST /webhook/azure` - Receives Azure Monitor alerts
* `POST /chat` - Simple chat endpoint (for testing)
* `POST /stream` - Streaming chat endpoint

