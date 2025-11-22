import asyncio
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.graph.state import AgentState
from app.tools.monitor import AzureLogTool
from app.core.kql_templates import get_template


log_tool = AzureLogTool()
llm = ChatOllama(model="gemma3:27b", temperature=0)


# Updated Prompt with Safety Rail for KQL Errors
analysis_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a Senior Application Reliability Engineer.
    You have been provided with a Deep Dive Diagnostic Report containing three sections.
    
    CRITICAL INSTRUCTION:
    - If the logs contain "BadArgumentError", "Query Failed", or "Scalar expression", it means the Monitoring Agent failed to run the query. 
    - Do NOT interpret this as an application failure. Report it as: "Agent Configuration Error: Unable to query logs."
    
    Sections:
    1. IMPACT ANALYSIS: High-fidelity grouping. Look at 'DistinctOps' to judge severity.
       - High DistinctOps = Systemic Failure across many transactions.
       - High RawCount but Low DistinctOps = Retry Loop / Localized to few transactions.
    
    2. INTELLIGENT PATTERN RECOGNITION: Machine learning analysis of failed requests segments.
       - Look for specific segments (e.g., "Browser=Chrome", "City=London").
       
    3. DEPENDENCY FAILURES: Downstream causes.
       - If you see SQL or HTTP dependencies failing, that is likely the Root Cause.
    
    Analyze these logs and provide a Root Cause Analysis.
    """),
    ("human", "Diagnostic Data:\n{logs}\n\nRoot Cause Analysis:")
])
analysis_chain = analysis_prompt | llm | StrOutputParser()


async def app_node(state: AgentState) -> AgentState:
    print("--- APP NODE: Deep Dive Diagnostic Suite ---")
    alert = state["alert_data"]
    
    # Safely extract resource_name
    resource_id = "Unknown"
    if (hasattr(alert.essentials, 'alertTargetIDs') and 
        alert.essentials.alertTargetIDs):
        resource_id = alert.essentials.alertTargetIDs[0]
    
    if isinstance(resource_id, str) and "/" in resource_id:
        resource_name = resource_id.rsplit("/", maxsplit=1)[-1]
    else:
        resource_name = str(resource_id)

    # Execute Diagnostic Suite (3 Distinct Strategies)
    # 1. Impact Analysis (Signal vs Noise)
    q1 = get_template("app_impact_analysis", resource_name)
    
    # 2. ML Pattern Matching (Autocluster)
    q2 = get_template("app_patterns", resource_name)
    
    # 3. Dependency Correlation (Root Cause)
    q3 = get_template("dependency_failures", resource_name)
    
    print(f"Executing Diagnostic Suite for {resource_name}...")
    
    # Run queries (could be async parallelized for speed, sequential for simplicity here)
    # Using the tool directly (which is sync) wrapped in asyncio.to_thread if needed, 
    # or just sequential calls since the tool seems synchronous in provided code.
    
    results_impact = log_tool.run_query(q1)
    results_patterns = log_tool.run_query(q2)
    results_deps = log_tool.run_query(q3)
    
    combined_logs = f"""
    === SECTION 1: IMPACT ANALYSIS (Exceptions by Operation Breadth) ===
    {results_impact}
    
    === SECTION 2: INTELLIGENT PATTERN RECOGNITION (ML Autocluster) ===
    {results_patterns}
    
    === SECTION 3: DEPENDENCY FAILURES (Downstream Correlation) ===
    {results_deps}
    """

    # Analyze
    report = await analysis_chain.ainvoke({"logs": combined_logs})

    return {
        "investigation_steps": state["investigation_steps"] + [
            "Ran Impact Analysis (ProblemId grouping)",
            "Ran Intelligent Pattern Recognition",
            "Checked Dependency Failures"
        ],
        "final_report": report
    }
