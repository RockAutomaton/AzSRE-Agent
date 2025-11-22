from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.graph.state import AgentState
from app.tools.monitor import AzureLogTool
from app.core.kql_templates import get_template


log_tool = AzureLogTool()
llm = ChatOllama(model="qwen3-vl:4b", temperature=0)


analysis_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an App Insights Analyst.
    
    RULES:
    - If 'Exceptions found' contains "No logs found", simply state: "No recent application exceptions detected."
    - Do NOT assume the logging system is broken.
    - Only report specific exceptions if they appear in the text.
    """),
    ("human", "Exceptions found:\n{logs}\n\nExplain what is crashing:")
])
analysis_chain = analysis_prompt | llm | StrOutputParser()


async def app_node(state: AgentState) -> AgentState:
    print("--- APP NODE: Checking App Insights (Templated) ---")
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

    # 1. Get Template
    query = get_template("app_exceptions", resource_name)
    
    # 2. Run Query
    print(f"Executing KQL: {query}")
    logs = log_tool.run_query(query)
    
    # 3. Analyze
    report = await analysis_chain.ainvoke({"logs": logs})

    return {
        "investigation_steps": state["investigation_steps"] + ["Checked AppExceptions (Templated)"],
        "final_report": report
    }
