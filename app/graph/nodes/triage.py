from app.graph.state import AgentState


async def triage_node(state: AgentState) -> AgentState:
    """
    Placeholder triage node.
    Replace this with your actual triage implementation.
    """
    print("--- TRIAGE NODE: Classifying alert ---")
    # Placeholder: just pass through for now
    return {
        "investigation_steps": state.get("investigation_steps", []) + ["Alert triaged"],
    }

