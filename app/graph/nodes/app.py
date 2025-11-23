import asyncio
import os
import re
import urllib.parse
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


def generate_portal_link(subscription_id, resource_group, resource_name, operation_id):
    """
    Constructs a deep link to the Transaction Search blade in Azure Portal.
    Note: This is a simplified approximation; deep linking to specific transactions is complex.
    We link to the 'Search' blade pre-filtered by the OperationId.
    """
    if not operation_id or operation_id == "Unknown":
        return "N/A"
        
    # Encode the query
    query = f'union * | where operation_Id == "{operation_id}"'
    query_encoded = urllib.parse.quote(query)
    
    # Construct URL (Generic Logs Blade Link)
    # Requires the full resource ID structure. Assuming standard structure for now.
    # You might need to pass the full ID from alert_data instead of rebuilding it.
    full_resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/microsoft.insights/components/{resource_name}"
    encoded_rid = urllib.parse.quote(full_resource_id)
    
    return f"https://portal.azure.com/#blade/Microsoft_Azure_Monitoring_Logs/LogsBlade/resourceId/{encoded_rid}/source/LogsBlade.AnalyticsShareLinkToQuery/q/{query_encoded}"


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

    # Execute Diagnostic Suite (4 Distinct Strategies)
    # 1. Impact Analysis (Signal vs Noise)
    q1 = get_template("app_impact_analysis", resource_name)
    
    # 2. ML Pattern Matching (Autocluster)
    q2 = get_template("app_patterns", resource_name)
    
    # 3. Dependency Correlation (Root Cause)
    q3 = get_template("dependency_failures", resource_name)
    
    # 4. Recent Configuration Changes (Deployment Correlation)
    q4 = get_template("recent_changes", resource_name)
    
    print(f"Executing Diagnostic Suite for {resource_name}...")
    
    # Run queries (could be async parallelized for speed, sequential for simplicity here)
    # Using the tool directly (which is sync) wrapped in asyncio.to_thread if needed, 
    # or just sequential calls since the tool seems synchronous in provided code.
    
    results_impact = log_tool.run_query(q1)
    results_patterns = log_tool.run_query(q2)
    results_deps = log_tool.run_query(q3)
    results_changes = log_tool.run_query(q4)
    
    # Extract a sample OperationId for the link (simple parsing)
    sample_op_id = "Unknown"
    if "OperationId" in results_impact or "operation_Id" in results_impact:
        # Extremely naive parse for demo purposes. 
        # Ideally, use a structured parser or LLM extraction.
        try:
            # Look for a GUID-like string in the text block (OperationId is typically a GUID)
            # Also check for 32 hex chars (trace IDs)
            guid_pattern = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
            hex_pattern = r'[a-f0-9]{32}'
            match = re.search(guid_pattern, results_impact, re.IGNORECASE) or re.search(hex_pattern, results_impact, re.IGNORECASE)
            if match:
                sample_op_id = match.group(0)
        except:
            pass

    # Generate Link
    # We need sub_id and rg from the alert essentials or env vars
    # For now, using placeholders or extraction if available in alert_data
    sub_id = os.getenv("AZURE_SUBSCRIPTION_ID", "YOUR_SUB_ID")
    # Try to extract RG from ID: /subscriptions/X/resourceGroups/Y/...
    rg = "YOUR_RG"
    if "/resourceGroups/" in str(resource_id):
        try:
            rg = str(resource_id).split("/resourceGroups/")[1].split("/")[0]
        except:
            pass
            
    portal_link = generate_portal_link(sub_id, rg, resource_name, sample_op_id)
    
    combined_logs = f"""
    === SECTION 1: IMPACT ANALYSIS (Exceptions by Operation Breadth) ===
    {results_impact}
    
    === SECTION 2: INTELLIGENT PATTERN RECOGNITION (ML Autocluster) ===
    {results_patterns}
    
    === SECTION 3: DEPENDENCY FAILURES (Downstream Correlation) ===
    {results_deps}
    
    === SECTION 4: RECENT CONFIG CHANGES (Deployment Correlation) ===
    {results_changes}
    
    === METADATA ===
    Sample Trace ID: {sample_op_id}
    Investigate Link: {portal_link}
    """

    # Analyze
    report = await analysis_chain.ainvoke({"logs": combined_logs})

    return {
        "investigation_steps": state["investigation_steps"] + [
            "Ran Impact Analysis (ProblemId grouping)",
            "Ran Intelligent Pattern Recognition",
            "Checked Dependency Failures",
            "Checked Recent Configuration Changes"
        ],
        "final_report": report
    }
