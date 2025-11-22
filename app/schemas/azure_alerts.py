from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field


class AlertEssentials(BaseModel):
    alertId: str
    alertRule: str
    severity: str
    signalType: str
    monitorCondition: str
    monitoringService: str
    alertTargetIDs: List[str]
    originAlertId: Optional[str] = None
    firedDateTime: str
    description: Optional[str] = None
    essentialsVersion: str
    alertContextVersion: str


class AlertContext(BaseModel):
    # This is dynamic depending on the alert type (Log Alert vs Metric Alert)
    # We capture it as a dict to be flexible
    conditionType: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    conditionParameters: Optional[Dict[str, Any]] = None


class AzureAlertData(BaseModel):
    essentials: AlertEssentials
    alertContext: Optional[AlertContext] = None
    customProperties: Optional[Dict[str, str]] = None


class AzureWebhookPayload(BaseModel):
    """
    The top-level wrapper sent by Azure Action Groups.
    Usually contains a 'schemaId' and 'data'.
    """

    schemaId: str
    data: AzureAlertData
