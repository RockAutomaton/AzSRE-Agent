# Azure SRE Agent Documentation Index

Welcome to the Azure SRE Agent documentation. This index provides an overview of the project and links to detailed documentation.

## What is Azure SRE Agent?

The **Azure SRE Agent** is an intelligent, automated incident response system that processes Azure Monitor alerts using a multi-agent LangGraph workflow. When an alert is triggered, the agent:

1. **Triages** the alert to classify it (Infrastructure, Database, Application, or Network)
2. **Investigates** using specialized nodes that execute KQL queries and fetch metrics
3. **Verifies** the alert is still active before reporting
4. **Reports** a structured incident summary with root cause analysis and recommendations

The system leverages local LLM models (via Ollama) for intelligent classification and analysis, combined with Azure Monitor APIs for real-time data collection.

## Key Features

- 🤖 **Automated Triage**: LLM-powered alert classification
- 🔍 **Deep Investigation**: Specialized nodes for Infrastructure, Database, and Application alerts
- 📊 **Real-time Metrics**: Fetches CPU, Memory, DTU, and other Azure metrics
- 📝 **KQL Queries**: Executes sophisticated Log Analytics queries for root cause analysis
- ✅ **Verification**: Double-checks alert status to prevent false positives
- 📋 **Structured Reports**: Generates professional Markdown incident reports

## Documentation Structure

### [Architecture Guide](./ARCHITECTURE.md)

Comprehensive overview of the system architecture, including:
- Multi-agent workflow design
- Mermaid.js workflow diagram
- Detailed node dictionary (Triage, Specialists, Verify, Reporter)
- State management and routing logic
- Tools and services used

**Start here** if you want to understand how the system works internally.

### [Setup Guide](./SETUP.md)

Step-by-step instructions for getting the agent running:
- Prerequisites (Python, Azure CLI, Ollama)
- Environment variable configuration
- Installation methods (uv or pip)
- Running the local server
- Testing with mock alerts

**Start here** if you're setting up the project for the first time.

### [Troubleshooting Guide](./TROUBLESHOOTING.md)

Common errors and their solutions:
- KQL query failures (BadArgumentError)
- Ollama connection issues
- Azure authentication problems
- Model not found errors
- Testing and simulation guide

**Start here** if you're encountering errors or issues.

## Quick Start

1. **Prerequisites**: Install Python 3.13+, Azure CLI, and Ollama
2. **Configure**: Set up `.env` file with `AZURE_SUBSCRIPTION_ID` and `LOG_WORKSPACE_ID`
3. **Install**: Run `uv sync` or `pip install -r requirements.txt`
4. **Start**: Run `uvicorn app.main:app --reload`
5. **Test**: Use `python scripts/trigger_alert.py` to send a mock alert

For detailed instructions, see the [Setup Guide](./SETUP.md).

## Project Structure

```
AzSRE-Agent/
├── app/
│   ├── main.py              # FastAPI application and webhook endpoint
│   ├── core/
│   │   ├── auth.py          # Azure authentication
│   │   └── kql_templates.py # KQL query templates
│   ├── graph/
│   │   ├── workflow.py      # LangGraph workflow definition
│   │   ├── state.py         # AgentState TypedDict
│   │   └── nodes/           # Workflow nodes
│   │       ├── triage.py    # Alert classification
│   │       ├── infra.py     # Infrastructure investigation
│   │       ├── database.py  # Database investigation
│   │       ├── app.py       # Application investigation
│   │       ├── verify.py    # Alert verification
│   │       └── reporter.py  # Report generation
│   ├── tools/
│   │   ├── monitor.py       # Azure Log Analytics client
│   │   └── metrics.py       # Azure Metrics client
│   └── schemas/
│       └── azure_alerts.py  # Pydantic models for alerts
├── scripts/
│   └── trigger_alert.py     # Mock alert testing script
├── tests/
│   └── mock_payload.json    # Sample alert payloads
└── docs/                    # Documentation (you are here)
```

## Technology Stack

- **LangGraph**: Workflow orchestration
- **LangChain**: LLM integration and prompt management
- **Ollama**: Local LLM server (qwen3-vl:4b, gemma3:27b)
- **FastAPI**: REST API framework
- **Azure Monitor Query API**: KQL query execution
- **Azure Monitor Management API**: Metrics retrieval
- **Pydantic**: Data validation and serialization

## Workflow Overview

```
Azure Alert → Triage → [Infra/DB/App/Network] → Verify → Reporter → Final Report
```

1. **Triage**: Classifies alert using LLM + keyword fallback
2. **Specialist Nodes**: Execute domain-specific investigations
3. **Verify**: Confirms alert is still active
4. **Reporter**: Synthesizes final Markdown report

See the [Architecture Guide](./ARCHITECTURE.md) for detailed workflow diagrams and node descriptions.

## Contributing

When contributing to this project:

1. Review the [Architecture Guide](./ARCHITECTURE.md) to understand the system design
2. Follow the existing code patterns and structure
3. Test your changes using `scripts/trigger_alert.py`
4. Update documentation if you modify the workflow or add new features

## Support

For issues and questions:

1. Check the [Troubleshooting Guide](./TROUBLESHOOTING.md) for common solutions
2. Review application logs for detailed error messages
3. Verify your configuration matches the [Setup Guide](./SETUP.md)

## License

[Add your license information here]

