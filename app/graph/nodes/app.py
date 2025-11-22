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
    
    resource_id = alert.essentials.alertTargetIDs[0] if alert.essentials.alertTargetIDs else "Unknown"
    resource_name = resource_id.split("/")[-1] if "/" in resource_id else resource_id

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
