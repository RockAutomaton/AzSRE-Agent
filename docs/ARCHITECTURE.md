# Architecture Overview

## Introduction

The Azure SRE Agent is a multi-agent system built with **LangGraph** that automatically triages, investigates, and reports on Azure Monitor alerts. The system processes alerts for three main categories: **Infrastructure**, **SQL/Database**, and **Application** anomalies.

The agent uses a state machine workflow where each node performs specialized tasks, and the state is passed between nodes to accumulate investigation results and generate a final incident report.

## System Overview

The agent receives Azure Monitor webhook alerts via a FastAPI endpoint, processes them through a LangGraph workflow, and returns a structured investigation report. The system leverages:

- **LangGraph**: For orchestrating the multi-node workflow
- **LangChain + Ollama**: For LLM-based classification and analysis
- **Azure Monitor Query API**: For executing KQL queries against Log Analytics workspaces
- **Azure Monitor Management API**: For fetching real-time metrics

## Workflow Diagram

The following Mermaid diagram illustrates the complete workflow:

```mermaid
graph TD
    Start([Azure Alert Webhook]) --> Triage[Triage Node]
    
    Triage --> Route{Route Alert}
    
    Route -->|INFRA| Infra[Infrastructure Node]
    Route -->|DATABASE/SQL| DB[Database Node]
    Route -->|APP| App[Application Node]
    Route -->|NETWORK| Network[Network Node<br/>Placeholder]
    
    Infra --> Verify[Verify Node]
    DB --> Verify
    App --> Verify
    Network --> Verify
    
    Verify --> Reporter[Reporter Node]
    Reporter --> End([Final Report])
    
    style Triage fill:#e1f5ff
    style Infra fill:#fff4e1
    style DB fill:#fff4e1
    style App fill:#fff4e1
    style Network fill:#fff4e1
    style Verify fill:#e8f5e9
    style Reporter fill:#f3e5f5
```

## Node Dictionary

### 1. Triage Node (`triage_node`)

**Purpose**: Classifies incoming alerts into one of four categories.

**Location**: `app/graph/nodes/triage.py`

**Functionality**:
- Uses the `qwen3-vl:4b` model to analyze alert rule names and descriptions
- Classifies alerts into: `INFRA`, `DATABASE`, `NETWORK`, or `APP`
- Implements keyword-based fallback heuristics if LLM classification fails
- Sets the `classification` field in the agent state

**Key Features**:
- Validates LLM output against known categories
- Falls back to keyword matching for reliability (e.g., "CPU", "Memory" → INFRA)
- Defaults to `APP` category if classification is uncertain

### 2. Specialist Nodes

#### Infrastructure Node (`infra_node`)

**Purpose**: Investigates infrastructure-related alerts (CPU, Memory, Disk, Container, VM issues).

**Location**: `app/graph/nodes/infra.py`

**Functionality**:
- **Metrics Check**: Fetches real-time metrics (CPU%, Memory%, RestartCount, Requests)
- **Smart Short-Circuit**: If metrics are healthy (<90% threshold), skips log analysis
- **Deep Investigation**: If metrics exceed thresholds, executes KQL queries using templates
- Uses `gemma3:27b` model for template selection and analysis

**Key Metrics Monitored**:
- `CpuPercentage`: CPU utilization
- `MemoryPercentage`: Memory utilization
- `RestartCount`: Container/VM restart events
- `Requests`: Request rate

#### Database Node (`db_node`)

**Purpose**: Investigates SQL and database-related alerts.

**Location**: `app/graph/nodes/database.py`

**Functionality**:
- Checks SQL-specific metrics: DTU consumption, CPU percentage, storage percentage
- Generates a summary report using the `qwen3-vl:4b` model
- Focuses on resource utilization metrics rather than log analysis

**Key Metrics Monitored**:
- `dtu_consumption_percent`: Database Transaction Unit usage
- `cpu_percent`: Database CPU utilization
- `storage_percent`: Storage utilization

#### Application Node (`app_node`)

**Purpose**: Performs deep-dive diagnostics on application exceptions and errors.

**Location**: `app/graph/nodes/app.py`

**Functionality**:
- Executes a **three-part diagnostic suite**:
  1. **Impact Analysis**: Groups exceptions by `ProblemId` and `OperationId` to distinguish systemic failures from retry loops
  2. **Pattern Recognition**: Uses KQL `autocluster()` to find common attributes in failed requests (browser, OS, city, etc.)
  3. **Dependency Failures**: Correlates failed requests with downstream dependency failures to identify root causes
- Uses `gemma3:27b` model for root cause analysis
- Handles KQL errors gracefully (e.g., `BadArgumentError`)

**KQL Templates Used**:
- `app_impact_analysis`: Signal vs. noise analysis
- `app_patterns`: ML-based pattern matching
- `dependency_failures`: Correlation with downstream services

#### Network Node (`network_placeholder_node`)

**Purpose**: Placeholder for network investigation (pending implementation).

**Location**: `app/graph/workflow.py`

**Functionality**:
- Returns a consistent state structure indicating network investigation is skipped
- Maintains workflow compatibility while network features are developed

### 3. Verify Node (`verify_node`)

**Purpose**: Double-checks alert status before generating the final report.

**Location**: `app/graph/nodes/verify.py`

**Functionality**:
- **For INFRA alerts**: Re-checks CPU and Memory metrics over the last 15 minutes
- **For APP/SQL alerts**: Queries logs to verify if errors are still active
- Prevents false positives by confirming the alert condition still exists
- Uses KQL injection protection via `validate_and_escape_kql_string()`

**Verification Strategies**:
- Infrastructure: Real-time metric checks
- Application/SQL: Log count queries with 15-minute lookback window

### 4. Reporter Node (`reporter_node`)

**Purpose**: Synthesizes investigation results into a professional incident report.

**Location**: `app/graph/nodes/reporter.py`

**Functionality**:
- Formats investigation steps into a bulleted list
- Uses `qwen3-vl:4b` model to generate a structured Markdown report
- Report format includes:
  - **Classification**: Alert category
  - **Summary**: 2-sentence overview
  - **Evidence**: Key logs or metrics found
  - **Recommendation**: Actionable next steps

## State Management

The workflow uses a `TypedDict` state (`AgentState`) that is passed between nodes:

```python
class AgentState(TypedDict, total=False):
    alert_data: AzureAlertData          # Original alert payload
    investigation_steps: List[str]      # Accumulated investigation steps
    final_report: Optional[str]         # Final formatted report
    classification: Optional[str]       # Set by triage node
```

Each node can read from and update the state, allowing information to flow through the workflow.

## Routing Logic

The `route_alert` function in `workflow.py` determines which specialist node to invoke based on:

1. **Primary**: The `classification` field set by the triage node
2. **Fallback**: Keyword matching on `alertRule` and `monitoringService` if classification is missing

Routing supports:
- `INFRA` → `investigate_infra`
- `DATABASE` / `SQL` → `investigate_db`
- `NETWORK` → `investigate_network`
- Default → `investigate_app`

## Tools and Services

### AzureLogTool (`app/tools/monitor.py`)

- Executes KQL queries against Log Analytics workspaces
- Requires `LOG_WORKSPACE_ID` environment variable
- Returns formatted string tables from query results
- Handles partial/failure query statuses gracefully

### AzureMetricsTool (`app/tools/metrics.py`)

- Fetches Azure Monitor metrics via Management API
- Requires `AZURE_SUBSCRIPTION_ID` environment variable
- Formats metrics into human-readable units (percentages, GiB/MiB, cores)
- Supports custom time ranges (default: 30 minutes)

### KQL Templates (`app/core/kql_templates.py`)

- Pre-defined KQL query templates for common investigation patterns
- Includes input sanitization to prevent KQL injection
- Templates include:
  - `container_logs`: Container Apps console logs
  - `app_impact_analysis`: Exception grouping by ProblemId
  - `app_patterns`: ML autocluster for pattern detection
  - `dependency_failures`: Request-dependency correlation
  - `sql_errors`: SQL error logs from Azure Diagnostics

## Authentication

The system uses Azure's `DefaultAzureCredential` chain:

- **Local Development**: Uses Azure CLI credentials (`az login`)
- **Docker/Production**: Uses Managed Identity or environment variables
- Credentials are cached via `@lru_cache()` for performance

## LLM Models Used

- **Triage**: `qwen3-vl:4b` (lightweight, fast classification)
- **Infrastructure Analysis**: `gemma3:27b` (template selection and analysis)
- **Application Analysis**: `gemma3:27b` (root cause analysis)
- **Database Reporting**: `qwen3-vl:4b` (metric summarization)
- **Reporter**: `qwen3-vl:4b` (report synthesis)

All models run via **Ollama** (local LLM server) with `temperature=0` for deterministic outputs.

