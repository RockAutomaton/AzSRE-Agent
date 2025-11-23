from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.graph.state import AgentState
from app.core.ollama_config import get_ollama_base_url, get_ollama_model_reporter


llm = ChatOllama(model=get_ollama_model_reporter(), temperature=0, base_url=get_ollama_base_url())


reporter_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an Incident Manager. 
    Write a clean, professional Incident Report based on the investigation logs.
    
    Format:
    **Classification:** [Category]
    **Summary:** [2 sentences on what happened]
    **Evidence:** [Key logs or metrics found]
    **Recommendation:** [Actionable next step]
    """),
    ("human", """
    Alert Rule: {alert_rule}
    Classification: {classification}
    Investigation Steps: {steps}
    Technical Findings: {raw_report}
    """)
])


reporter_chain = reporter_prompt | llm | StrOutputParser()


async def reporter_node(state: AgentState) -> AgentState:
    print("--- REPORTER NODE: Synthesizing Report ---")
    
    alert = state["alert_data"]
    
    # Format steps into a bulleted list
    steps = state.get("investigation_steps", [])
    if steps:
        steps_str = "- " + "\n- ".join(steps)
    else:
        steps_str = "No investigation steps recorded."
    
    # Get classification, default to "UNKNOWN" if not set
    classification = state.get("classification", "UNKNOWN")
    
    final_summary = await reporter_chain.ainvoke({
        "alert_rule": alert.essentials.alertRule,
        "classification": classification,
        "steps": steps_str,
        "raw_report": state.get("final_report", "No technical findings recorded.")
    })
    
    print(f"Final Report Generated:\n{final_summary}")
    
    # Overwrite the raw technical report with the polished summary
    return {
        "final_report": final_summary
    }

