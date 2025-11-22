from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes.triage import triage_node
from app.graph.nodes.infra import infra_node
from app.graph.nodes.database import db_node
from app.graph.nodes.app import app_node
from app.graph.nodes.reporter import reporter_node
from app.graph.nodes.verify import verify_node


def network_placeholder_node(state: AgentState) -> AgentState:
    """Placeholder node for network investigation pending implementation.
    
    Returns consistent state structure matching other specialist nodes,
    including investigation_result and status fields for downstream routing.
    """
    return {
        "investigation_steps": state["investigation_steps"] + ["Network investigation skipped (pending implementation)"],
        "final_report": "Network investigation pending implementation",
        "investigation_result": "Network investigation pending implementation",
        "status": "skipped"
    }


def build_graph():
    workflow = StateGraph(AgentState)

    # Nodes
    workflow.add_node("triage", triage_node)
    workflow.add_node("investigate_infra", infra_node)
    workflow.add_node("investigate_db", db_node)
    workflow.add_node("investigate_app", app_node)
    workflow.add_node("investigate_network", network_placeholder_node)
    
    workflow.add_node("verify", verify_node)
    workflow.add_node("reporter", reporter_node)

    # Routing Logic
    def route_alert(state: AgentState):
        cat = state.get("classification", "")
        if not cat:
            # Fallback to alert rule analysis if classification not set
            alert = state["alert_data"]
            if "SQL" in alert.essentials.alertRule or "Database" in alert.essentials.alertRule:
                return "investigate_db"
            elif "Application" in alert.essentials.alertRule or "App" in alert.essentials.alertRule:
                return "investigate_app"
            elif alert.essentials.monitoringService in ["Platform", "Infrastructure"]:
                return "investigate_infra"
            return "investigate_app"
        
        if "INFRA" in cat.upper():
            return "investigate_infra"
        if "DATABASE" in cat.upper() or "SQL" in cat.upper():
            return "investigate_db"
        if "NETWORK" in cat.upper():
            return "investigate_network"
        return "investigate_app"

    workflow.set_entry_point("triage")
    
    # Triage -> Specialist
    workflow.add_conditional_edges(
        "triage",
        route_alert,
        {
            "investigate_infra": "investigate_infra",
            "investigate_db": "investigate_db",
            "investigate_network": "investigate_network",
            "investigate_app": "investigate_app"
        }
    )
    
    # Specialist -> Verify (Fan In)
    workflow.add_edge("investigate_infra", "verify")
    workflow.add_edge("investigate_db", "verify")
    workflow.add_edge("investigate_app", "verify")
    workflow.add_edge("investigate_network", "verify")
    
    # Verify -> Reporter
    workflow.add_edge("verify", "reporter")
    
    # Reporter -> End
    workflow.add_edge("reporter", END)

    return workflow.compile()
