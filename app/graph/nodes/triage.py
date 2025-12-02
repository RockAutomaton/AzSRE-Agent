from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.graph.state import AgentState
from app.core.ollama_config import get_ollama_base_url, get_ollama_model_triage


llm = ChatOllama(
    model=get_ollama_model_triage(),
    temperature=0,
    base_url=get_ollama_base_url(),
)


# Improved Prompt with stronger examples
triage_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a Senior Site Reliability Engineer. Classify the Azure Alert into one of these categories:

    1. INFRA
       - CPU, Memory, Disk, Network I/O
       - VM stopped, Container crashed, Node unhealthy
       - Keywords: "CPU", "Memory", "Percentage", "System"
    
    2. DATABASE
       - SQL, CosmosDB, Redis, Storage Accounts
       - DTU usage, connection timeouts, deadlocks
    
    3. APP
       - Application-level failures
       - HTTP 500/403 errors, Exceptions, Latency (Response Time)
       - Keywords: "Exception", "Failed Requests", "Response Time"
    
    4. NETWORK
       - DNS, Load Balancer, VNET, Firewall
    
    INSTRUCTIONS:
    - Return ONLY the category name (e.g., "INFRA").
    - If the metric is "CPU Usage" or "Memory Working Set", it is ALWAYS "INFRA", even if the resource is an App Service.
    """),
    ("human", """
    Alert Rule: {alert_rule}
    Description: {description}
    Target Resource: {target_resource}
    
    Category:""")
])


triage_chain = triage_prompt | llm | StrOutputParser()


async def triage_node(state: AgentState) -> AgentState:
    print("--- TRIAGE NODE: Analyzing Alert ---")
    alert = state["alert_data"]
    rule_name = alert.essentials.alertRule
    description = alert.essentials.description or ""
    
    # Extract target resource type for context
    target_id = alert.essentials.alertTargetIDs[0] if alert.essentials.alertTargetIDs else ""
    resource_type = "Unknown"
    if "/providers/" in target_id:
        try:
            resource_type = target_id.split("/providers/")[1].split("/")[0]
        except:
            pass

    # Extract metric name from alert context if available (most reliable indicator)
    metric_name = ""
    if alert.alertContext and alert.alertContext.condition:
        condition = alert.alertContext.condition
        # Check for metricName in various possible locations
        if isinstance(condition, dict):
            # Check direct metricName field
            metric_name = condition.get("metricName", "") or condition.get("metric_name", "")
            # Check in allOf array (common structure)
            if not metric_name and "allOf" in condition:
                all_of = condition.get("allOf", [])
                if isinstance(all_of, list) and len(all_of) > 0:
                    first_condition = all_of[0] if isinstance(all_of[0], dict) else {}
                    metric_name = first_condition.get("metricName", "") or first_condition.get("metric_name", "")
    
    # Extract monitoring service for context
    monitoring_service = alert.essentials.monitoringService or ""
    signal_type = alert.essentials.signalType or ""
    
    # Prepare text for keyword matching (include metric name for most accurate classification)
    rule_lower = rule_name.lower()
    desc_lower = description.lower()
    metric_lower = metric_name.lower() if metric_name else ""
    combined_text = f"{rule_lower} {desc_lower} {metric_lower}".strip()
    
    print(f"  Rule: {rule_name}")
    print(f"  Metric: {metric_name}" if metric_name else "  Metric: (not found)")
    print(f"  Resource Type: {resource_type}")
    print(f"  Monitoring Service: {monitoring_service}")
    
    # Application-specific keywords that should NOT be classified as INFRA
    app_keywords = ["exception", "failed requests", "error", "500", "403", "404", "timeout", "anomaly", "smart detection"]
    
    # Specific infrastructure metric names (these are definitive)
    infra_metric_names = [
        "cpu usage", "cpuusage", "cpu percentage", "cpupercentage", "cpupercentage",
        "memory usage", "memoryusage", "memory percentage", "memorypercentage", 
        "memory working set", "working set", "disk usage", "diskusage",
        "cpupercentage", "memorypercentage", "processor time", "processor time percentage"
    ]
    
    # General infrastructure keywords (less specific, need context)
    infra_keywords = ["vm", "node", "capacity", "container crashed", "node unhealthy"]
    
    database_keywords = ["sql", "cosmos", "redis", "dtu", "database", "db"]
    network_keywords = ["dns", "vnet", "firewall", "ip", "load balancer"]
    
    # 0. PRE-CHECK: Only force classification for very specific cases
    # Priority 1: Check for application keywords first (these override infrastructure)
    if any(keyword in combined_text for keyword in app_keywords):
        # If it's Application Insights with app keywords, it's definitely APP
        if "application insights" in monitoring_service.lower() or "application" in monitoring_service.lower():
            print(f"🔧 Application keyword detected with Application Insights. Forcing APP classification.")
            classification = "APP"
        # Otherwise let LLM decide, but lean towards APP
        else:
            classification = None  # Let LLM decide
    # Priority 2: Check for specific infrastructure metric names (most reliable)
    elif metric_name and any(infra_metric in metric_lower for infra_metric in infra_metric_names):
        # Only force INFRA if monitoring service is Platform (not Application Insights)
        if "platform" in monitoring_service.lower() or "infrastructure" in monitoring_service.lower():
            print(f"🔧 Infrastructure metric '{metric_name}' detected with Platform monitoring. Forcing INFRA.")
            classification = "INFRA"
        else:
            classification = None  # Let LLM decide
    # Priority 3: Check for database keywords
    elif any(keyword in combined_text for keyword in database_keywords):
        print(f"🔧 Database keyword detected. Forcing DATABASE classification.")
        classification = "DATABASE"
    # Priority 4: Check for network keywords
    elif any(keyword in combined_text for keyword in network_keywords):
        print(f"🔧 Network keyword detected. Forcing NETWORK classification.")
        classification = "NETWORK"
    # Priority 5: Check for general infrastructure keywords (only if Platform monitoring)
    elif any(keyword in combined_text for keyword in infra_keywords):
        if "platform" in monitoring_service.lower() or "infrastructure" in monitoring_service.lower():
            print(f"🔧 Infrastructure keyword with Platform monitoring. Forcing INFRA.")
            classification = "INFRA"
        else:
            classification = None  # Let LLM decide
    else:
        classification = None  # Let LLM decide
    
    # 1. Try LLM Classification (if pre-check didn't force a classification)
    if classification is None:
        try:
            classification = await triage_chain.ainvoke({
                "alert_rule": rule_name,
                "description": description,
                "target_resource": resource_type
            })
            classification = classification.strip().upper()
            # Remove any punctuation the LLM might add
            classification = classification.replace(".", "").replace(":", "")
            print(f"🤖 LLM classified as: {classification}")
        except Exception as e:
            print(f"LLM Triage Failed: {e}")
            classification = "UNKNOWN"

    valid_categories = ["INFRA", "DATABASE", "NETWORK", "APP"]
    
    # 2. Heuristic Validation (Safety Net for invalid LLM responses)
    if classification not in valid_categories:
        print(f"⚠️ Invalid category '{classification}'. Using Keyword Fallback.")
        
        # Priority 1: Application keywords (if Application Insights)
        if any(x in combined_text for x in app_keywords) and "application" in monitoring_service.lower():
            classification = "APP"
        
        # Priority 2: Explicit Database Keywords
        elif any(x in combined_text for x in database_keywords):
            classification = "DATABASE"
        
        # Priority 3: Specific infrastructure metrics (only with Platform monitoring)
        elif metric_name and any(infra_metric in metric_lower for infra_metric in infra_metric_names):
            if "platform" in monitoring_service.lower():
                classification = "INFRA"
            else:
                classification = "APP"  # If Application Insights, default to APP
            
        # Priority 4: Network
        elif any(x in combined_text for x in network_keywords):
            classification = "NETWORK"
            
        # Priority 5: Application (Default for Application Insights or unknown)
        elif "application" in monitoring_service.lower():
            classification = "APP"
            
        # Priority 6: Default fallback
        else:
            classification = "APP"

    print(f"--- CLASSIFIED AS: {classification} ---")
    
    return {
        "classification": classification,
        "investigation_steps": state.get("investigation_steps", []) + [f"Triaged as {classification} (Resource: {resource_type})"]
    }
