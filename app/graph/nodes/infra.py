import logging
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.graph.state import AgentState
from app.tools.monitor import AzureLogTool
from app.tools.metrics import AzureMetricsTool
from app.core.kql_templates import get_template


llm = ChatOllama(model="qwen3-vl:4b", temperature=0)
log_tool = AzureLogTool()
metrics_tool = AzureMetricsTool()


# Selector Prompt
selector_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an Azure Investigator. Select the best KQL Template.
    Options:
    - container_logs (Container Apps)
    - sql_errors (SQL)
    Return ONLY the option key."""),
    ("human", "Alert Rule: {alert_rule}\nResource: {resource}")
])

selector_chain = selector_prompt | llm | StrOutputParser()


# Analysis Prompt
analysis_prompt = ChatPromptTemplate.from_messages([
    ("system", """Analyze the technical data provided.
    CRITICAL INSTRUCTIONS:
    - If Logs say "No logs found", it means NO ERRORS were captured.
    - Focus on Metrics if logs are clean.
    """),
    ("human", """
    Alert: {alert_rule}
    
    Metrics Data:
    {metrics}
    
    Log Data:
    {logs}
    
    Root Cause Summary:""")
])

analysis_chain = analysis_prompt | llm | StrOutputParser()


def is_valid_metric_response(metric_str: str) -> bool:
    """Check if a metric response string contains valid data (not an error message)"""
    if not metric_str:
        return False
    error_patterns = ["Error fetching", "No data found", "No recorded values", "No data points"]
    return not any(metric_str.startswith(pattern) or pattern in metric_str for pattern in error_patterns) and "Current:" in metric_str


def parse_metric_value(metric_str: str) -> float:
    """Helper to extract the 'Current' float value from the metric string"""
    try:
        for line in metric_str.split('\n'):
            if "Current:" in line:
                val_str = line.split("Current:")[1].strip().replace('%', '').replace(' Cores', '').replace(' GiB', '').replace(' MiB', '')
                return float(val_str)
    except (ValueError, IndexError, AttributeError) as e:
        logging.warning(f"Failed to parse metric value. Input: {metric_str!r}, Exception: {type(e).__name__}: {e}")
        return -1.0
    return -1.0


async def infra_node(state: AgentState) -> AgentState:
    print("--- INFRA NODE: Strict Smart Investigation ---")
    alert = state["alert_data"]
    
    resource_id = alert.essentials.alertTargetIDs[0] if alert.essentials.alertTargetIDs else "Unknown"
    resource_name = resource_id.split("/")[-1] if "/" in resource_id else resource_id
    
    # A. Check Metrics
    metrics_report = []
    needs_logs = False
    
    if resource_id != "Unknown":
        # 1. CPU (Threshold 90%)
        try:
            cpu_str = metrics_tool.get_metric(resource_id, "CpuPercentage")
            metrics_report.append(cpu_str)
            # Only parse and check thresholds if we got valid data
            if is_valid_metric_response(cpu_str):
                cpu_val = parse_metric_value(cpu_str)
                if cpu_val >= 0 and cpu_val > 90.0:
                    needs_logs = True
        except Exception as e:
            logging.error(f"Failed to get CpuPercentage metric for resource {resource_id}: {type(e).__name__}: {e}")
            metrics_report.append("CpuPercentage: Collection failed")
        
        # 2. Memory (Threshold 90%)
        try:
            mem_str = metrics_tool.get_metric(resource_id, "MemoryPercentage")
            metrics_report.append(mem_str)
            # Only parse and check thresholds if we got valid data
            if is_valid_metric_response(mem_str):
                mem_val = parse_metric_value(mem_str)
                if mem_val >= 0 and mem_val > 90.0:
                    needs_logs = True
        except Exception as e:
            logging.error(f"Failed to get MemoryPercentage metric for resource {resource_id}: {type(e).__name__}: {e}")
            metrics_report.append("MemoryPercentage: Collection failed")

        # 3. Restarts (Always check logs if restarts > 0)
        try:
            restarts_str = metrics_tool.get_metric(resource_id, "RestartCount")
            metrics_report.append(restarts_str)
            # Only parse and check thresholds if we got valid data
            if is_valid_metric_response(restarts_str):
                restarts_val = parse_metric_value(restarts_str)
                if restarts_val >= 0 and restarts_val > 0:
                    needs_logs = True
        except Exception as e:
            logging.error(f"Failed to get RestartCount metric for resource {resource_id}: {type(e).__name__}: {e}")
            metrics_report.append("RestartCount: Collection failed")
        
        # 4. Requests (Context only)
        try:
            reqs_str = metrics_tool.get_metric(resource_id, "Requests")
            metrics_report.append(reqs_str)
        except Exception as e:
            logging.error(f"Failed to get Requests metric for resource {resource_id}: {type(e).__name__}: {e}")
            metrics_report.append("Requests: Collection failed")
        
    metrics_data = "\n".join(metrics_report) if metrics_report else "Not checked."
    print(f"Metrics Collected:\n{metrics_data}")

    # B. Conditional Log Check (STRICT MODE)
    logs = "Logs skipped (Metrics healthy, below 90% threshold)."
    
    if needs_logs:
        print(f"⚠️ Metrics exceed 90% threshold or Restarts detected. Running KQL...")
        try:
            template_key = await selector_chain.ainvoke({
                "alert_rule": alert.essentials.alertRule,
                "resource": resource_name
            })
        except Exception as e:
            logging.error(
                f"Failed to invoke selector chain for alert {alert.essentials.alertId} "
                f"on resource {resource_name}: {type(e).__name__}: {e}"
            )
            template_key = ""
        
        if isinstance(template_key, str):
            template_key = template_key.strip().lower()
        
        try:
            query = get_template(template_key, resource_name)
            print(f"Executing KQL: {query}")
            logs = log_tool.run_query(query)
        except Exception as e:
            logs = f"Template Error: {str(e)}"
            
        steps = ["Checked Metrics", f"Ran Template: {template_key}"]
    else:
        print("✅ Metrics healthy (<90%). Skipping Log Investigation.")
        steps = ["Checked Metrics", "Skipped Logs (Healthy)"]

    # C. Analyze
    report = await analysis_chain.ainvoke({
        "alert_rule": alert.essentials.alertRule,
        "metrics": metrics_data,
        "logs": logs
    })
    
    return {
        "investigation_steps": state["investigation_steps"] + steps,
        "final_report": report
    }
