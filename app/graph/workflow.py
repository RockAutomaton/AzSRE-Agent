from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes.triage import triage_node
from app.graph.nodes.infra import infra_node
from app.graph.nodes.database import db_node
from app.graph.nodes.app import app_node
from app.graph.nodes.reporter import reporter_node


def build_graph():
    workflow = StateGraph(AgentState)

    # 1. Add Nodes
    workflow.add_node("triage", triage_node)
    workflow.add_node("investigate_infra", infra_node)
    workflow.add_node("investigate_db", db_node)
    workflow.add_node("investigate_app", app_node)
    
    # Placeholder for network still
    async def network_placeholder(state: AgentState) -> AgentState:
        return {
            "investigation_steps": state.get("investigation_steps", []) + ["Network investigation placeholder"],
            "final_report": "Network check skipped."
        }
    workflow.add_node("investigate_network", network_placeholder)
    workflow.add_node("reporter", reporter_node)

    # 2. Define Routing
    def route_alert(state: AgentState) -> str:
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

    # 3. Build Edges
    workflow.set_entry_point("triage")
    
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
    
    # 4. Fan-in to Reporter (Instead of END)
    workflow.add_edge("investigate_infra", "reporter")
    workflow.add_edge("investigate_db", "reporter")
    workflow.add_edge("investigate_app", "reporter")
    workflow.add_edge("investigate_network", "reporter")
    
    # 5. Final End
    workflow.add_edge("reporter", END)

    return workflow.compile()

