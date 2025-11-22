from app.graph.state import AgentState
from app.tools.metrics import AzureMetricsTool
from app.tools.monitor import AzureLogTool


# Initialize Tools
metrics_tool = AzureMetricsTool()
log_tool = AzureLogTool()


async def verify_node(state: AgentState) -> AgentState:
    print("--- VERIFICATION NODE: Checking Active Status ---")
    alert = state["alert_data"]
    
    # FIX: Safely handle None classification
    classification = state.get("classification") or "UNKNOWN"
    
    resource_id = alert.essentials.alertTargetIDs[0] if alert.essentials.alertTargetIDs else None
    resource_name = resource_id.split("/")[-1] if resource_id else "Unknown"
    
    # Sanitize resource name to prevent KQL injection
    clean_resource = resource_name.replace("'", "").replace('"', "")
    
    status_report = "Could not verify current status."

    try:
        # Strategy 1: If it's INFRA, check CPU/Memory Metrics (Real-time)
        if "INFRA" in classification and resource_id:
            # FIX: Use valid Azure metric names (CpuPercentage, MemoryPercentage)
            cpu_status = metrics_tool.get_metric(resource_id, "CpuPercentage", minutes=5)
            mem_status = metrics_tool.get_metric(resource_id, "MemoryPercentage", minutes=5)
            status_report = f"Current Infrastructure Status (5m):\n{cpu_status}\n{mem_status}"
            
        # Strategy 2: If it's APP/SQL, check for recent logs
        elif clean_resource != "Unknown":
            # Construct a "Count" query
            table = "AzureDiagnostics" if "SQL" in classification else "AppExceptions"
            where_clause = f'where Resource has "{clean_resource}"' if "SQL" in classification else f'where AppRoleName has "{clean_resource}"'
            
            query = f"""
                {table}
                | where TimeGenerated > ago(5m)
                | {where_clause}
                | count
            """
            
            print(f"Verifying with KQL: {query}")
            count_result = log_tool.run_query(query)
            
            # Robust check: If result contains a number > 0, it's active
            if "No logs found" in count_result:
                status_report = "✅ No active errors detected in the last 5 minutes."
            elif "0" in count_result and "Count" in count_result: 
                 status_report = "✅ No active errors detected in the last 5 minutes."
            else:
                status_report = f"⚠️ Alert Condition matches active logs in last 5m.\nResult: {count_result}"

    except Exception as e:
        status_report = f"Verification Failed: {str(e)}"

    print(f"Verification Result: {status_report}")
    
    return {
        "investigation_steps": state["investigation_steps"] + [f"Verification: {status_report}"]
    }
