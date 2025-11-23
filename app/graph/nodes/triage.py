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


triage_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an Azure DevOps expert. Classify the alert into:
    1. INFRA (CPU, Memory, Disk, VM, Container, Crash)
    2. DATABASE (SQL, CosmosDB, Timeout, DTU)
    3. NETWORK (VNET, DNS, Load Balancer)
    4. APP (Exception, 500 Error, Performance, Latency)
    
    Return ONLY the category name."""),
    ("human", "Alert Rule: {alert_rule}\nDescription: {description}\n\nCategory:")
])


triage_chain = triage_prompt | llm | StrOutputParser()


async def triage_node(state: AgentState) -> AgentState:
    print("--- TRIAGE NODE: Analyzing Alert ---")
    alert = state["alert_data"]
    rule_name = alert.essentials.alertRule
    description = alert.essentials.description or ""
    
    # 1. Try LLM Classification
    try:
        classification = await triage_chain.ainvoke({
            "alert_rule": rule_name,
            "description": description
        })
        classification = classification.strip().upper()
    except Exception as e:
        print(f"LLM Triage Failed: {e}")
        classification = "UNKNOWN"

    # 2. Validate & Fallback (Heuristics)
    # Small models (4B) often fail or hallucinate. We trust keywords over the LLM for obvious cases.
    valid_categories = ["INFRA", "DATABASE", "NETWORK", "APP"]
    
    if classification not in valid_categories:
        print(f"⚠️ LLM returned invalid category '{classification}'. Using Keyword Fallback.")
        
        rule_lower = rule_name.lower()
        
        if any(x in rule_lower for x in ["cpu", "memory", "disk", "container", "node", "vm", "restarted"]):
            classification = "INFRA"
        elif any(x in rule_lower for x in ["sql", "database", "cosmos", "dtu", "storage"]):
            classification = "DATABASE"
        elif any(x in rule_lower for x in ["net", "dns", "ip", "firewall"]):
            classification = "NETWORK"
        else:
            classification = "APP"  # Default to App if we really don't know

    print(f"--- CLASSIFIED AS: {classification} ---")
    
    return {
        "classification": classification,
        "investigation_steps": state.get("investigation_steps", []) + [f"Triaged as {classification}"]
    }
