from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.graph.state import AgentState
from app.tools.monitor import AzureLogTool
from app.tools.metrics import AzureMetricsTool
from app.core.kql_templates import get_template


llm = ChatOllama(model="gemma3:27b", temperature=0)
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


def parse_metric_value(metric_str: str) -> float:
    """Helper to extract the 'Current' float value from the metric string"""
    try:
        for line in metric_str.split('\n'):
            if "Current:" in line:
                val_str = line.split("Current:")[1].strip().replace('%', '').replace(' Cores', '').replace(' GiB', '').replace(' MiB', '')
                return float(val_str)
    except:
        return 0.0
    return 0.0


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
        cpu_str = metrics_tool.get_metric(resource_id, "CpuPercentage")
        metrics_report.append(cpu_str)
        if parse_metric_value(cpu_str) > 90.0: 
            needs_logs = True 
        
        # 2. Memory (Threshold 90%)
        mem_str = metrics_tool.get_metric(resource_id, "MemoryPercentage")
        metrics_report.append(mem_str)
        if parse_metric_value(mem_str) > 90.0: 
            needs_logs = True

        # 3. Restarts (Threshold > 0)
        restarts_str = metrics_tool.get_metric(resource_id, "RestartCount")
        metrics_report.append(restarts_str)
        if parse_metric_value(restarts_str) > 0: 
            needs_logs = True
        
        # 4. Requests
        reqs_str = metrics_tool.get_metric(resource_id, "Requests")
        metrics_report.append(reqs_str)
        
    metrics_data = "\n".join(metrics_report)
    print(f"Metrics Collected:\n{metrics_data}")

    # B. Logic Branch: Healthy vs Unhealthy
    if not needs_logs:
        # SHORT CIRCUIT: Skip LLM entirely if metrics are fine
        print("✅ Metrics healthy (<90%). Short-circuiting investigation.")
        report = (f"Infrastructure is HEALTHY.\n\nMetrics:\n{metrics_data}\n\n"
                  "No active CPU/Memory pressure or restarts detected. Skipping log analysis.")
        
        return {
            "investigation_steps": state["investigation_steps"] + ["Checked Metrics", "Skipped Logs (Healthy)"],
            "final_report": report
        }

    # C. Deep Investigation (Only runs if issues found)
    print(f"⚠️ Metrics exceed thresholds. Starting Deep Dive...")
    template_key = await selector_chain.ainvoke({
        "alert_rule": alert.essentials.alertRule,
        "resource": resource_name
    })
    template_key = template_key.strip().lower()
    
    logs = ""
    try:
        query = get_template(template_key, resource_name)
        print(f"Executing KQL: {query}")
        logs = log_tool.run_query(query)
    except Exception as e:
        logs = f"Template Error: {str(e)}"

    # D. LLM Analysis
    report = await analysis_chain.ainvoke({
        "alert_rule": alert.essentials.alertRule,
        "metrics": metrics_data,
        "logs": logs
    })
    
    return {
        "investigation_steps": state["investigation_steps"] + ["Checked Metrics (Flagged)", f"Ran Template: {template_key}"],
        "final_report": report
    }
