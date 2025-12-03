## Azure SRE Agent – An AI-powered incident response bot

An intelligent, automated incident response system that processes Azure Monitor alerts using a multi-agent LangGraph workflow. The agent automatically triages, investigates, and reports on Infrastructure, SQL/Database, and Application anomalies, and exposes the results through an API and a Next.js dashboard.

## Overview

The Azure SRE Agent receives Azure Monitor webhook alerts and processes them through an intelligent workflow:

1. **Triage**: Classifies alerts using LLM-powered analysis
2. **Investigate**: Executes specialized investigations (Infrastructure, Database, Application)
3. **Verify**: Confirms alert status before reporting
4. **Report**: Generates structured incident reports with root cause analysis

## Quick Start (Docker)

```bash
# 1. Ensure prerequisites are installed
#    - Docker / Docker Desktop
#    - Azure CLI (for az login)

# 2. Configure environment variables
cp .env.example .env   # Edit with your Azure subscription and workspace IDs

# 3. Start the stack (backend + Ollama + frontend)
docker-compose up --build
```

Once running:

- Backend API: `http://localhost:8000`
- Frontend dashboard: `http://localhost:3000`

For a code-first workflow without Docker, see `docs/SETUP.md`.

## Documentation

📚 **Full documentation is available in the [`docs/`](./docs/) directory:**

- **[Index](./docs/INDEX.md)**: Overview and navigation
- **[Architecture](./docs/ARCHITECTURE.md)**: System design and workflow diagrams
- **[Setup Guide](./docs/SETUP.md)**: Installation and configuration
- **[Troubleshooting](./docs/TROUBLESHOOTING.md)**: Common errors and solutions

## Key Features

- **Automated Triage (Infra vs App vs DB)**: LLM-powered alert classification and routing to specialist nodes.
- **Deep Dive Diagnostics using KQL**: Uses curated KQL templates against Azure Monitor and Application Insights.
- **Structured Reporting with Root Cause Analysis**: Markdown incident reports with summary, evidence, and recommendations.
- **Interactive Chat Interface & Dashboard**: Next.js frontend for chatting with the agent and reviewing incident history.

## Requirements (Core)

- Python 3.11+ (or the version specified in `pyproject.toml`)
- Node.js (for the Next.js frontend)
- Docker (for the recommended local stack)
- Azure CLI (`az login`)
- Ollama (local LLM server)
- Azure Log Analytics Workspace
- Azure Subscription with Monitor and Table Storage access

## Environment Variables (Summary)

Create a `.env` file with at least:

```bash
AZURE_SUBSCRIPTION_ID=your-subscription-id
LOG_WORKSPACE_ID=your-workspace-id
AZURE_STORAGE_TABLE_ENDPOINT=https://<your-storage-account>.table.core.windows.net
APPLICATIONINSIGHTS_CONNECTION_STRING=your-app-insights-connection-string
OLLAMA_BASE_URL=http://ollama:11434  # or http://localhost:11434 for local
```

See `docs/SETUP.md` for the full list and explanations.

## API Endpoints

- `POST /webhook/azure`: Receives Azure Monitor alerts
- `POST /chat`: Simple chat endpoint (for testing)
- `POST /stream`: Streaming chat endpoint

## Project Structure (High Level)

```text
app/          # FastAPI backend, LangGraph workflow, tools, and schemas
frontend/     # Next.js app for chat interface, history, and analytics
docs/         # Project documentation (architecture, setup, troubleshooting, etc.)
scripts/      # Utilities for testing, chaos traffic, and deployment helpers
IaC/          # Bicep templates for Azure deployment
```

## Technology Stack

- **FastAPI**: Backend API and Azure Monitor webhook endpoint.
- **LangGraph + LangChain**: Multi-agent workflow and LLM orchestration.
- **Ollama**: Local LLM runtime.
- **Next.js**: Frontend dashboard and chat UI.
- **Azure Monitor & Application Insights**: Metrics, logs, and KQL analytics.

## License

[Add your license information here]

