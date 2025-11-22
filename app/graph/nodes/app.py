from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.graph.state import AgentState
from app.tools.monitor import AzureLogTool


# Use existing Log Tool (App Insights data is often in Log Analytics workspace now)
log_tool = AzureLogTool()
llm = ChatOllama(model="qwen3-vl:4b", temperature=0)


kql_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an App Insights Expert. Write KQL to find exceptions."),
    ("human", """
    Write a KQL query to find recent exceptions for this alert.
    Alert Rule: {alert_rule}
    
    Query the 'AppExceptions' or 'AppTraces' table.
    Look for the top 5 exceptions by count.
    Return ONLY raw KQL.
    """)
])
kql_chain = kql_prompt | llm | StrOutputParser()


analysis_prompt = ChatPromptTemplate.from_messages([
    ("system", "Analyze these application exceptions."),
    ("human", "Exceptions found:\n{logs}\n\nExplain what is crashing:")
])
analysis_chain = analysis_prompt | llm | StrOutputParser()


async def app_node(state: AgentState) -> AgentState:
    print("--- APP NODE: Checking App Insights ---")
    alert = state["alert_data"]
    
    # 1. Generate KQL
    query = await kql_chain.ainvoke({"alert_rule": alert.essentials.alertRule})
    query = query.replace("```kql", "").replace("```", "").strip()
    
    # 2. Run Query
    logs = log_tool.run_query(query)
    
    # 3. Analyze
    report = await analysis_chain.ainvoke({"logs": logs})

    return {
        "investigation_steps": state["investigation_steps"] + [f"Queried App Insights: {query}"],
        "final_report": report
    }

