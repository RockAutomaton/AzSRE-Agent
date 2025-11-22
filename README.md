# Azure SRE Agent

An intelligent, automated incident response system that processes Azure Monitor alerts using a multi-agent LangGraph workflow. The agent automatically triages, investigates, and reports on Infrastructure, SQL, and Application anomalies.

## Overview

The Azure SRE Agent receives Azure Monitor webhook alerts and processes them through an intelligent workflow:

1. **Triage**: Classifies alerts using LLM-powered analysis
2. **Investigate**: Executes specialized investigations (Infrastructure, Database, Application)
3. **Verify**: Confirms alert status before reporting
4. **Report**: Generates structured incident reports with root cause analysis

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment variables
cp .env.example .env  # Edit with your Azure credentials

# 3. Start Ollama and pull models
ollama serve
ollama pull qwen3-vl:4b
ollama pull gemma3:27b

# 4. Run the server
uvicorn app.main:app --reload

# 5. Test with a mock alert
python scripts/trigger_alert.py
```

## Documentation

📚 **Full documentation is available in the [`docs/`](./docs/) directory:**

- **[Index](./docs/INDEX.md)**: Overview and navigation
- **[Architecture](./docs/ARCHITECTURE.md)**: System design and workflow diagrams
- **[Setup Guide](./docs/SETUP.md)**: Installation and configuration
- **[Troubleshooting](./docs/TROUBLESHOOTING.md)**: Common errors and solutions

## Features

- 🤖 **Automated Triage**: LLM-powered alert classification
- 🔍 **Deep Investigation**: Specialized nodes for different alert types
- 📊 **Real-time Metrics**: Fetches Azure Monitor metrics (CPU, Memory, DTU, etc.)
- 📝 **KQL Queries**: Executes sophisticated Log Analytics queries
- ✅ **Verification**: Prevents false positives by verifying alert status
- 📋 **Structured Reports**: Generates professional Markdown incident reports

## Requirements

- Python 3.13+
- Azure CLI (`az login`)
- Ollama (local LLM server)
- Azure Log Analytics Workspace
- Azure Subscription with Monitor API access

## Environment Variables

Create a `.env` file with:

```bash
AZURE_SUBSCRIPTION_ID=your-subscription-id
LOG_WORKSPACE_ID=your-workspace-id
```

## API Endpoints

- `POST /webhook/azure`: Receives Azure Monitor alerts
- `POST /chat`: Simple chat endpoint (for testing)
- `POST /stream`: Streaming chat endpoint

## Project Structure

```
app/
├── main.py              # FastAPI application
├── core/                # Authentication and KQL templates
├── graph/               # LangGraph workflow and nodes
├── tools/               # Azure Monitor clients
└── schemas/             # Pydantic models
```

## Technology Stack

- **LangGraph**: Workflow orchestration
- **LangChain + Ollama**: LLM integration
- **FastAPI**: REST API framework
- **Azure Monitor APIs**: Metrics and logs

## License

[Add your license information here]

