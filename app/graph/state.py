from typing import List, Optional, TypedDict
from app.schemas.azure_alerts import AzureAlertData


class AgentState(TypedDict, total=False):
    """State passed between graph nodes."""
    alert_data: AzureAlertData
    investigation_steps: List[str]
    final_report: Optional[str]
    classification: Optional[str]  # Set by triage node

