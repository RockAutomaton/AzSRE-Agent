import json
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from app.graph.state import AgentState
from app.core.ollama_config import get_ollama_base_url, get_ollama_model_reporter
from app.schemas.report import IncidentReport


# Initialize LLM
llm = ChatOllama(model=get_ollama_model_reporter(), temperature=0, base_url=get_ollama_base_url())

# Create the structured LLM
structured_llm = llm.with_structured_output(IncidentReport)


reporter_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an Expert Site Reliability Engineer. 
    Analyze the provided investigation data and generate a structured Incident Report.
    
    Guidelines:
    - Be precise and technical.
    - If the logs show 'BadArgumentError', identify it as a Configuration Error.
    - If no errors are found, state that the system appears healthy but the alert might be a false positive.
    - Provide specific evidence items with clear sources and findings.
    - Recommendations should be actionable and prioritized.
    """),
    ("human", """
    Alert Rule: {alert_rule}
    Initial Classification: {classification}
    Investigation Steps: {steps}
    Technical Findings (Logs):
    {raw_report}
    """)
])


# Create the chain
reporter_chain = reporter_prompt | structured_llm


async def reporter_node(state: AgentState) -> AgentState:
    print("--- REPORTER NODE: Synthesizing Structured Report ---")
    
    alert = state["alert_data"]
    steps = state.get("investigation_steps", [])
    steps_str = "\n".join([f"- {s}" for s in steps]) if steps else "No investigation steps recorded."
    
    try:
        # Get raw report - should be a string from investigation nodes, but handle both cases
        raw_report = state.get("final_report", "No technical findings recorded.")
        if isinstance(raw_report, dict):
            # If somehow it's already a dict, convert to string for the prompt
            raw_report = json.dumps(raw_report, indent=2)
        elif not isinstance(raw_report, str):
            raw_report = str(raw_report)
        
        report_object = await reporter_chain.ainvoke({
            "alert_rule": alert.essentials.alertRule,
            "classification": state.get("classification", "UNKNOWN"),
            "steps": steps_str,
            "raw_report": raw_report  # This should be the raw logs string from investigation nodes
        })
        
        # Convert Pydantic model to dict for state storage
        report_dict = report_object.model_dump()
        
        print(f"Generated Structured Report: {report_dict['summary']}")
        print(f"  Classification: {report_dict['classification']}")
        print(f"  Evidence Items: {len(report_dict['evidence'])}")
        
        return {
            "final_report": report_dict
        }
        
    except Exception as e:
        print(f"❌ Reporting Failed: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to a basic error report if the LLM fails to structure it
        fallback = {
            "classification": "UNKNOWN",
            "summary": f"Failed to generate report: {str(e)}",
            "root_cause": "LLM Generation Error",
            "evidence": [],
            "recommendations": ["Check LLM logs", "Verify Ollama connection"]
        }
        return {"final_report": fallback}

