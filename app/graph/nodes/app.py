from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.graph.state import AgentState
from app.tools.monitor import AzureLogTool
from app.core.kql_templates import get_template


log_tool = AzureLogTool()
llm = ChatOllama(model="gemma3:27b", temperature=0)


# Updated Prompt to handle mixed failure types
analysis_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an Application Support Engineer.
    You are looking at a timeline of recent failures (Crashes, HTTP 500s, Error Logs).
    
    INSTRUCTIONS:
    - Identify if the issue is a Code Crash (Type='Crash') or an API Failure (Type='HTTP Failure').
    - Look for patterns: Are specific URLs failing? Is it the same exception repeating?
    - If the log says "No logs found", report: "No active application failures detected."
    """),
    ("human", "Failure Timeline:\n{logs}\n\nRoot Cause Analysis:")
])
analysis_chain = analysis_prompt | llm | StrOutputParser()


async def app_node(state: AgentState) -> AgentState:
    print("--- APP NODE: Checking Failures & Exceptions ---")
    alert = state["alert_data"]
    
    # Safely extract resource_id with validation
    resource_id = "Unknown"
    if (hasattr(alert.essentials, 'alertTargetIDs') and 
        alert.essentials.alertTargetIDs and 
        len(alert.essentials.alertTargetIDs) > 0 and
        isinstance(alert.essentials.alertTargetIDs[0], str) and
        alert.essentials.alertTargetIDs[0].strip()):
        resource_id = alert.essentials.alertTargetIDs[0]
    
    # Safely extract resource_name using rsplit
    if isinstance(resource_id, str) and "/" in resource_id:
        parts = resource_id.rsplit("/", maxsplit=1)
        resource_name = parts[-1] if parts and parts[-1] else "Unknown"
    else:
        resource_name = resource_id if isinstance(resource_id, str) and resource_id else "Unknown"

    # 1. Get Template (New Failures Template)
    query = get_template("app_failures", resource_name)
    
    # 2. Run Query
    print(f"Executing KQL: {query}")
    logs = log_tool.run_query(query)
    
    # 3. Analyze
    report = await analysis_chain.ainvoke({"logs": logs})

    return {
        "investigation_steps": state["investigation_steps"] + ["Checked App Failures (Requests + Exceptions)"],
        "final_report": report
    }
