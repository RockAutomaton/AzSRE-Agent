from typing import List, Optional, TypedDict, Any, Dict, Union
from app.schemas.azure_alerts import AzureAlertData


class AgentState(TypedDict, total=False):
    """State passed between graph nodes."""
    alert_data: AzureAlertData
    investigation_steps: List[str]
    # final_report can be a string (raw findings from investigation nodes) 
    # or a dict (structured report from reporter node)
    final_report: Optional[Union[str, Dict[str, Any]]]
    classification: Optional[str]  # Set by triage node

