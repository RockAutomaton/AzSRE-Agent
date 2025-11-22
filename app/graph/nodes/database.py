from app.graph.state import AgentState
from app.tools.metrics import AzureMetricsTool

# We don't necessarily need an LLM for basic metric checks, 
# but we use one to synthesize the report.
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


llm = ChatOllama(model="qwen3-vl:4b", temperature=0)
metrics_tool = AzureMetricsTool()


report_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a Database Administrator. Summarize these metrics."),
    ("human", "Alert: {alert}\nMetrics Findings: {metrics}\n\nSummary:")
])
report_chain = report_prompt | llm | StrOutputParser()


async def db_node(state: AgentState) -> AgentState:
    print("--- DATABASE NODE: Checking Metrics ---")
    alert = state["alert_data"]
    resource_id = alert.essentials.alertTargetIDs[0] if alert.essentials.alertTargetIDs else None

    findings = []
    
    if resource_id:
        # Check common SQL metrics
        dtu = metrics_tool.get_metric(resource_id, "dtu_consumption_percent")
        cpu = metrics_tool.get_metric(resource_id, "cpu_percent")
        storage = metrics_tool.get_metric(resource_id, "storage_percent")
        
        findings = [dtu, cpu, storage]
    else:
        findings = ["No Resource ID found in alert to check metrics."]

    findings_str = "\n".join(findings)
    print(f"DB Metrics: {findings_str}")

    # Generate Report
    report = await report_chain.ainvoke({
        "alert": alert.essentials.alertRule,
        "metrics": findings_str
    })

    return {
        "investigation_steps": state["investigation_steps"] + ["Checked SQL Metrics (DTU, CPU)"],
        "final_report": report
    }

