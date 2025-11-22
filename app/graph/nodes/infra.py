from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.graph.state import AgentState
from app.tools.monitor import AzureLogTool


# Initialize 4B model
llm = ChatOllama(model="qwen3-vl:4b", temperature=0)
log_tool = AzureLogTool()


# Prompt to generate KQL
kql_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert in Kusto Query Language (KQL). Return ONLY the raw KQL query. No markdown, no explanations."),
    ("human", """
    Write a KQL query to investigate this alert context:
    Alert Rule: {alert_rule}
    Resource: {resource}
    
    If it is a Container App, query 'ContainerAppConsoleLogs_CL'.
    If it is a VM, query 'Syslog' or 'Event'.
    If unsure, query 'AppServiceConsoleLogs'.
    
    Take the top 10 logs ordered by TimeGenerated desc.
    """)
])

kql_chain = kql_prompt | llm | StrOutputParser()


# Prompt to analyze the logs
analysis_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a Site Reliability Engineer. Analyze these logs and identify the root cause."),
    ("human", """
    Alert: {alert_rule}
    Logs Retrieved:
    {logs}
    
    Summarize the root cause in 2 sentences.
    """)
])

analysis_chain = analysis_prompt | llm | StrOutputParser()


async def infra_node(state: AgentState) -> AgentState:
    print("--- INFRA NODE: Investigating ---")
    alert = state["alert_data"]
    
    # 1. Generate KQL
    query = await kql_chain.ainvoke({
        "alert_rule": alert.essentials.alertRule,
        "resource": alert.essentials.alertTargetIDs[0] if alert.essentials.alertTargetIDs else "Unknown"
    })
    
    # Clean the query (remove markdown code blocks if the LLM added them)
    query = query.replace("```kql", "").replace("```", "").strip()
    print(f"Generated KQL: {query}")
    
    # 2. Execute KQL
    logs = log_tool.run_query(query)
    
    # 3. Analyze Findings
    report = await analysis_chain.ainvoke({
        "alert_rule": alert.essentials.alertRule,
        "logs": logs
    })
    
    return {
        "investigation_steps": state["investigation_steps"] + [f"Ran KQL: {query}", "Logs analyzed"],
        "final_report": report
    }

