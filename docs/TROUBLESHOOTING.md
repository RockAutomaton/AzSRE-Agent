# Troubleshooting Guide

This guide covers common errors, their causes, and solutions for the Azure SRE Agent.

## Common Errors

### 1. BadArgumentError / KQL Query Failures

**Error Message**:
```
BadArgumentError: Query execution failed
Scalar expression: user_Id
```

**Cause**: 
KQL queries can fail due to schema mismatches. Common causes include:
- Case sensitivity issues (e.g., `user_Id` vs `user_id`)
- Missing columns in the Log Analytics workspace
- Incorrect table names or schema changes
- Application Insights tables may not exist if the resource doesn't send telemetry to Log Analytics

**Solution**:
1. **Check the KQL template**: Review the query in `app/core/kql_templates.py`
2. **Verify table schema**: Run the query directly in Azure Portal → Log Analytics to see the actual column names
3. **Update the template**: Modify the query to match your workspace schema
4. **Use safe operators**: The agent uses `has` operator for string matching, which is more forgiving than exact matches
5. **Check table existence**: Verify that Application Insights tables (AppRequests, AppExceptions, etc.) exist in your workspace

**Example Fix**:
```python
# Before (may fail if column doesn't exist)
| where user_Id == "value"

# After (safer, uses has operator)
| where AppRoleName has "value"
```

**Note**: The app node's analysis prompt includes a safety rail that detects KQL errors and reports them as "Agent Configuration Error: Unable to query logs" rather than interpreting them as application failures.

### 2. ConnectionError: Ollama Not Running

**Error Message**:
```
ConnectionError: Connection refused
Could not connect to localhost:11434
```

**Cause**: 
Ollama service is not running or not accessible.

**Solution**:
```bash
# Start Ollama
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

**Prevention**: 
- Add Ollama to your system startup services
- Use a process manager like `systemd` or `supervisord` in production

### 3. DefaultAzureCredential Failed

**Error Message**:
```
DefaultAzureCredential failed to retrieve a token
```

**Cause**: 
Azure authentication is not configured properly.

**Solution**:

**For Local Development**:
```bash
# Authenticate with Azure CLI
az login

# Verify authentication
az account show
```

**For Docker/Production**:
- Use Managed Identity (recommended for Azure-hosted containers)
- Or set environment variables:
  ```bash
  export AZURE_CLIENT_ID=your-client-id
  export AZURE_CLIENT_SECRET=your-client-secret
  export AZURE_TENANT_ID=your-tenant-id
  ```

### 4. LOG_WORKSPACE_ID Not Set

**Error Message**:
```
Error: LOG_WORKSPACE_ID is not set in environment.
```

**Cause**: 
The required environment variable is missing.

**Solution**:
1. Create a `.env` file in the project root:
   ```bash
   LOG_WORKSPACE_ID=your-workspace-id-here
   ```

2. Verify the variable is loaded:
   ```python
   import os
   from dotenv import load_dotenv
   load_dotenv()
   print(os.getenv("LOG_WORKSPACE_ID"))
   ```

### 5. Model Not Found (Ollama)

**Error Message**:
```
Error: model "qwen3-vl:4b" not found
```

**Cause**: 
The required Ollama model hasn't been pulled/downloaded.

**Solution**:
```bash
# Pull all required models
ollama pull qwen3-vl:4b
ollama pull gemma3:27b

# Verify models are available
ollama list
```

**Note**: `gemma3:27b` is a large model (~15GB). Ensure you have sufficient disk space.

### 6. KQL Injection Validation Error

**Error Message**:
```
ValueError: Resource name contains invalid characters
ValueError: Resource name is empty or too long
ValueError: Resource name contains dangerous token
```

**Cause**: 
The resource name contains characters that could be used for KQL injection. The agent uses strict validation to prevent security issues. The validation checks for:
- Empty or excessively long names (>256 characters)
- Dangerous tokens: newlines (`\n`, `\r`), pipe (`|`), backslash (`\`), comment markers (`//`, `/*`, `*/`)
- Invalid characters outside the whitelist

**Solution**:
- Ensure resource names only contain alphanumeric characters, hyphens, underscores, dots, spaces, and forward slashes
- If you're passing custom resource names, sanitize them before calling the agent
- The validation is performed by `sanitize_resource_name()` in `app/core/kql_templates.py` and `validate_and_escape_kql_string()` in `app/graph/nodes/verify.py`

**Valid Characters**: `a-z`, `A-Z`, `0-9`, `-`, `_`, `.`, `/`, ` ` (space)

### 7. Workflow Graph Not Initialized

**Error Message**:
```
HTTPException: workflow graph not initialized
```

**Cause**: 
The LangGraph workflow failed to build during application startup, often due to:
- Missing dependencies
- Import errors
- Configuration issues

**Solution**:
1. Check the application logs for the initial error:
   ```bash
   # Look for "Failed to initialize workflow graph" in logs
   ```

2. Verify all dependencies are installed:
   ```bash
   uv sync
   # or
   pip install -r requirements.txt
   ```

3. Check for import errors:
   ```bash
   python -c "from app.graph.workflow import build_graph; build_graph()"
   ```

### 8. Metrics API Timeout

**Error Message**:
```
Error fetching CpuPercentage: Request timeout
```

**Cause**: 
Azure Monitor API requests are timing out, possibly due to:
- Network issues
- Large time ranges
- API rate limiting

**Solution**:
- The agent already uses 60-second timeouts
- Reduce the time range if querying large datasets
- Check Azure service health status
- Verify your subscription has proper API access

### 9. Partial Query Results

**Error Message**:
```
Partial Error: Query exceeded allowed execution time
```

**Cause**: 
KQL queries are taking too long to execute, often due to:
- Large time ranges
- Complex queries
- High data volume

**Solution**:
1. Reduce the time range in the query (e.g., from 24h to 1h)
2. Add more specific filters to reduce data scanned
3. Use `summarize` or `sample` to reduce result size
4. Check query performance in Azure Portal → Log Analytics

## Simulation and Testing

### Using the Trigger Script

The `scripts/trigger_alert.py` script allows you to send mock alerts for testing:

```bash
# Use default mock payload (tests/mock_payload.json)
python scripts/trigger_alert.py

# Use a specific mock file
python scripts/trigger_alert.py mock_app_payload.json
```

### Creating Custom Mock Payloads

1. Copy an existing mock file from `tests/`:
   ```bash
   cp tests/mock_payload.json tests/my_custom_alert.json
   ```

2. Modify the alert data:
   ```json
   {
     "schemaId": "azureMonitorCommonAlertSchema",
     "data": {
       "essentials": {
         "alertRule": "My Custom Alert Rule",
         "alertTargetIDs": ["/subscriptions/.../resourceGroups/.../providers/..."],
         ...
       }
     }
   }
   ```

3. Test with your custom payload:
   ```bash
   python scripts/trigger_alert.py my_custom_alert.json
   ```

### Testing Specific Node Paths

To test a specific classification path:

1. **Test Infrastructure Node**: Use an alert with "CPU" or "Memory" in the rule name
2. **Test Database Node**: Use an alert with "SQL" or "Database" in the rule name
3. **Test Application Node**: Use an alert with "Exception" or "Error" in the rule name

Example mock payload for Infrastructure:
```json
{
  "data": {
    "essentials": {
      "alertRule": "High CPU Usage",
      "monitoringService": "Platform",
      ...
    }
  }
}
```

## Debugging Tips

### Enable Verbose Logging

Add logging configuration to see detailed execution flow:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Node Execution

Each node prints debug information:
- `--- TRIAGE NODE: Analyzing Alert ---`
- `--- INFRA NODE: Strict Smart Investigation ---`
- `--- APP NODE: Deep Dive Diagnostic Suite ---`
- `--- VERIFICATION NODE: Checking Active Status ---`
- `--- REPORTER NODE: Synthesizing Report ---`

### Inspect State Between Nodes

Add temporary logging to see state transitions:

```python
# In any node
print(f"Current State: {state}")
```

### Test KQL Queries Directly

Before relying on the agent, test KQL queries in Azure Portal:

1. Go to Azure Portal → Log Analytics workspaces
2. Select your workspace
3. Use the "Logs" query editor
4. Paste the query from `app/core/kql_templates.py`
5. Verify it returns expected results

### Verify Metrics Access

Test metric retrieval directly:

```python
from app.tools.metrics import AzureMetricsTool

tool = AzureMetricsTool()
result = tool.get_metric(
    resource_id="/subscriptions/.../resourceGroups/.../providers/...",
    metric_name="CpuPercentage"
)
print(result)
```

## Getting Help

If you encounter issues not covered here:

1. **Check Application Logs**: Review the full error traceback
2. **Verify Configuration**: Ensure all environment variables are set correctly
3. **Test Components Individually**: Test Ollama, Azure auth, and KQL queries separately
4. **Review Architecture Docs**: Understand the expected flow in [ARCHITECTURE.md](./ARCHITECTURE.md)

## Performance Optimization

### Reduce LLM Latency

- Use smaller models for simple tasks (e.g., `qwen3-vl:4b` for triage)
- Cache LLM responses for similar alerts (future enhancement)
- Run Ollama with GPU acceleration if available

### Optimize KQL Queries

- Use appropriate time ranges (shorter = faster)
- Add filters early in the query
- Use `summarize` to reduce result size
- Consider using `sample` for very large datasets

### Parallelize Operations

The workflow could be enhanced to run independent queries in parallel (e.g., the three app diagnostic queries could run concurrently).

