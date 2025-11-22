import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)

# Maximum length for resource names to prevent excessively long inputs
MAX_RESOURCE_NAME_LENGTH = 256


class KQLTemplate(Enum):
    CONTAINER_LOGS = "container_logs"
    UNIFIED_DIAGNOSTICS = "unified_diagnostics"
    DEPENDENCY_FAILURES = "dependency_failures"
    SQL_ERRORS = "sql_errors"


# Templates using placeholders that will be replaced with sanitized and escaped values
TEMPLATES = {
    # Standard Azure Monitor table for Container Apps
    KQLTemplate.CONTAINER_LOGS: """
        ContainerAppConsoleLogs
        | where ContainerAppName has {resource_name}
        | project TimeGenerated, ContainerAppName, Log_s
        | top 20 by TimeGenerated desc
    """,
    
    # NEW: Modern Unified Telemetry Query (Strict Workspace Schema)
    # Unions App* tables. 
    # Note: Time filtering is handled by the API client's 'timespan' parameter, not in KQL.
    KQLTemplate.UNIFIED_DIAGNOSTICS: """
        union isfuzzy=true 
            (AppRequests | extend Type="Request"),
            (AppExceptions | extend Type="Exception"),
            (AppDependencies | extend Type="Dependency"),
            (AppTraces | extend Type="Trace"),
            (AppPageViews | extend Type="PageView"),
            (AppAvailabilityResults | extend Type="Availability"),
            (AppEvents | extend Type="Event")
        | extend 
            RoleName = column_ifexists("AppRoleName", ""),
            Msg = coalesce(column_ifexists("OuterMessage", ""), column_ifexists("Message", ""), column_ifexists("Name", "")),
            ResCode = column_ifexists("ResultCode", ""),
            Dur = column_ifexists("DurationMs", 0.0),
            OpId = column_ifexists("OperationId", "")
        | where RoleName has {resource_name}
        | order by TimeGenerated desc
        | take 100
        | project TimeGenerated, Type, Role=RoleName, Message=Msg, ResultCode=ResCode, DurationMs=Dur, OperationId=OpId
    """,

    # STRATEGY: Correlation
    # Strict Workspace schema for joining Requests and Dependencies.
    KQLTemplate.DEPENDENCY_FAILURES: """
        AppRequests
        | where Success == false
        | where AppRoleName has {resource_name}
        | project OperationId, RequestResult = ResultCode, RequestTime = TimeGenerated
        | join kind=inner (
            AppDependencies
            | where Success == false
            | project OperationId, DependencyType = Type, DependencyTarget = Target, DependencyResult = ResultCode
        ) on OperationId
        | summarize count() by RequestResult, DependencyType, DependencyTarget, DependencyResult
        | top 10 by count_ desc
    """,

    # Azure Diagnostics for SQL (Standard Table)
    KQLTemplate.SQL_ERRORS: """
        AzureDiagnostics
        | where Resource has {resource_name}
        | where Category == "SQLErrors" or Category == "Timeouts"
        | project TimeGenerated, error_number_d, Message
        | top 20 by TimeGenerated desc
    """
}


def sanitize_resource_name(resource_name: str) -> str:
    """
    Sanitizes and validates resource name input to prevent KQL injection.
    """
    if not resource_name:
        logger.warning("KQL sanitization rejected: empty resource name")
        raise ValueError("Resource name cannot be empty")
    
    if len(resource_name) > MAX_RESOURCE_NAME_LENGTH:
        raise ValueError(f"Resource name exceeds maximum length of {MAX_RESOURCE_NAME_LENGTH}")
    
    # Dangerous chars and comment tokens
    dangerous_tokens = ['\n', '\r', '|', '\\', '//', '/*', '*/']
    for token in dangerous_tokens:
        if token in resource_name:
            raise ValueError(f"Resource name contains dangerous token '{token}'")
    
    # Whitelist validation
    whitelist_pattern = re.compile(r'^[a-zA-Z0-9._\s/-]+$')
    if not whitelist_pattern.match(resource_name):
        raise ValueError("Resource name contains invalid characters.")
    
    return resource_name


def get_template(template_key: str, resource_name: str) -> str:
    """
    Returns the rendered KQL query with strong input sanitization.
    """
    # Sanitize first
    try:
        sanitized_resource = sanitize_resource_name(resource_name)
    except ValueError as e:
        logger.error(f"KQL template generation failed: {e}")
        raise
    
    # Lookup Enum
    try:
        key = KQLTemplate(template_key.lower())
    except ValueError:
        # Fallback mapping for old keys or fuzzy matching
        if "unified" in template_key.lower() or "impact" in template_key.lower():
            key = KQLTemplate.UNIFIED_DIAGNOSTICS
        elif "depend" in template_key.lower():
            key = KQLTemplate.DEPENDENCY_FAILURES
        elif "sql" in template_key.lower():
            key = KQLTemplate.SQL_ERRORS
        else:
            # Default to Unified Diagnostics for generic "App" requests
            key = KQLTemplate.UNIFIED_DIAGNOSTICS

    template = TEMPLATES.get(key)
    
    # Escape for KQL
    escaped_resource = sanitized_resource.replace('"', '""')
    escaped_value = f'"{escaped_resource}"'
    
    # Handle "Unknown" resource case specifically for Application Insights tables
    if resource_name.lower() == "unknown":
        escaped_value = '""' # Look for empty strings if unknown, or remove filter

    query = template.format(resource_name=escaped_value).strip()
    return query
