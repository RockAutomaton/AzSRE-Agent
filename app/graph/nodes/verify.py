import asyncio
import re
from app.graph.state import AgentState
from app.tools.metrics import AzureMetricsTool
from app.tools.monitor import AzureLogTool


# Initialize Tools
metrics_tool = AzureMetricsTool()
log_tool = AzureLogTool()


def validate_and_escape_kql_string(value: str) -> str:
    """
    Validates and safely escapes a string for use in KQL queries.
    
    Args:
        value: The string to validate and escape
        
    Returns:
        A safely escaped string wrapped in double quotes, or raises ValueError if invalid
        
    Raises:
        ValueError: If the value doesn't match the whitelist pattern
    """
    # Strict whitelist: Azure resource names typically contain:
    # - Alphanumeric characters (a-z, A-Z, 0-9)
    # - Hyphens (-)
    # - Underscores (_)
    # - Dots (.)
    # - Forward slashes (/) for resource paths
    # Maximum reasonable length for a resource name
    if not value or len(value) > 256:
        raise ValueError("Resource name is empty or too long")
    
    # Validate against strict whitelist pattern
    whitelist_pattern = re.compile(r'^[a-zA-Z0-9._/-]+$')
    if not whitelist_pattern.match(value):
        raise ValueError(f"Resource name contains invalid characters: {value}")
    
    # Escape double quotes by doubling them (KQL escaping)
    # Then wrap in double quotes for the has operator
    escaped = value.replace('"', '""')
    return f'"{escaped}"'


async def verify_node(state: AgentState) -> AgentState:
    print("--- VERIFICATION NODE: Checking Active Status ---")
    alert = state["alert_data"]
    
    # FIX: Safely handle None classification
    classification = state.get("classification") or "UNKNOWN"
    
    resource_id = alert.essentials.alertTargetIDs[0] if alert.essentials.alertTargetIDs else None
    resource_name = resource_id.split("/")[-1] if resource_id else "Unknown"
    
    status_report = "Could not verify current status."

    try:
        # Strategy 1: If it's INFRA, check CPU/Memory Metrics (Real-time)
        if "INFRA" in classification and resource_id:
            # FIX: Use valid Azure metric names (CpuPercentage, MemoryPercentage)
            # Run blocking calls off the event loop concurrently
            try:
                cpu_status, mem_status = await asyncio.gather(
                    asyncio.to_thread(metrics_tool.get_metric, resource_id, "CpuPercentage", 5),
                    asyncio.to_thread(metrics_tool.get_metric, resource_id, "MemoryPercentage", 5)
                )
                status_report = f"Current Infrastructure Status (5m):\n{cpu_status}\n{mem_status}"
            except Exception as metric_error:
                status_report = f"Error fetching metrics: {str(metric_error)}"
            
        # Strategy 2: If it's APP/SQL, check for recent logs
        elif resource_name != "Unknown":
            try:
                # Validate and safely escape the resource name to prevent KQL injection
                safe_resource = validate_and_escape_kql_string(resource_name)
                
                # Construct a "Count" query with safe parameterization
                table = "AzureDiagnostics" if "SQL" in classification else "AppExceptions"
                field_name = "Resource" if "SQL" in classification else "AppRoleName"
                
                # Build query with safely escaped value
                query = f"""
                    {table}
                    | where TimeGenerated > ago(5m)
                    | where {field_name} has {safe_resource}
                    | count
                """
                
                print(f"Verifying with KQL: {query}")
                # Run blocking query call off the event loop
                count_result = await asyncio.to_thread(log_tool.run_query, query, 5)
                
                # Robust check: If result contains a number > 0, it's active
                if "No logs found" in count_result:
                    status_report = "✅ No active errors detected in the last 5 minutes."
                elif "0" in count_result and "Count" in count_result: 
                    status_report = "✅ No active errors detected in the last 5 minutes."
                else:
                    status_report = f"⚠️ Alert Condition matches active logs in last 5m.\nResult: {count_result}"
            except ValueError as validation_error:
                status_report = f"Verification Failed: Invalid resource name - {str(validation_error)}"
                print(f"Validation error: {validation_error}")

    except Exception as e:
        status_report = f"Verification Failed: {str(e)}"

    print(f"Verification Result: {status_report}")
    
    return {
        "investigation_steps": state["investigation_steps"] + [f"Verification: {status_report}"]
    }
