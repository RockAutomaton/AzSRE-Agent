## Azure SRE Agent – An AI‑powered incident response bot

The **Azure SRE Agent** is an AI‑powered incident response bot for Azure Monitor. It automatically triages alerts, runs deep-dive diagnostics using KQL, and produces structured incident reports that are surfaced through an interactive chat interface and dashboard.

### Documentation Map

- **Project Overview**: see the root `README.md` in the repository.
- **Architecture**: high-level design, LangGraph workflow, and node responsibilities → `ARCHITECTURE.md`.
- **Setup**: local dev, Docker, environment variables, and prerequisites → `SETUP.md`.
- **Permissions**: Azure RBAC roles required for logs, metrics, and storage → `PERMISSIONS.md`.
- **Troubleshooting**: common runtime and configuration issues → `TROUBLESHOOTING.md`.

### Key Features

- **Automated Triage (Infra vs App vs DB)**: Classifies alerts and routes them to the appropriate specialist node.
- **Deep Dive Diagnostics using KQL**: Executes curated KQL templates against Azure Monitor and Application Insights.
- **Structured Reporting with Root Cause Analysis**: Produces concise, Markdown incident reports with evidence and recommendations.
- **Interactive Chat Interface & Dashboard**: Next.js frontend for chat-style interaction and incident history.

### High‑Level Flow

Azure Monitor Alert Webhook → Triage Node → Specialist Node (Infra / App / DB / Network placeholder) → Verify Node → Reporter Node → Database / Frontend.


