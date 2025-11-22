import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)

# Maximum length for resource names to prevent excessively long inputs
MAX_RESOURCE_NAME_LENGTH = 256


class KQLTemplate(Enum):
    CONTAINER_LOGS = "container_logs"
    # Replaced generic APP_FAILURES with specialized analytical queries
    APP_IMPACT_ANALYSIS = "app_impact_analysis" 
    APP_PATTERNS = "app_patterns"
    DEPENDENCY_FAILURES = "dependency_failures"
    SQL_ERRORS = "sql_errors"


# Templates using placeholders that will be replaced with sanitized and escaped values
TEMPLATES = {
    # Standard Azure Monitor table for Container Apps
    KQLTemplate.CONTAINER_LOGS: """
        ContainerAppConsoleLogs
        | where TimeGenerated > ago(1h)
        | where ContainerAppName has {resource_name}
        | project TimeGenerated, ContainerAppName, Log_s
        | top 20 by TimeGenerated desc
    """,
    
    # STRATEGY: Signal vs Noise (Section 5.1 & 8.2)
    # Distinguishes "loud" errors (retry loops) from "wide" errors (systemic).
    # Uses OperationId instead of User_Id to be schema-safe (works even if user tracking is off).
    KQLTemplate.APP_IMPACT_ANALYSIS: """
        AppExceptions
        | where TimeGenerated > ago(24h)
        | where AppRoleName has {resource_name}
        | summarize 
            RawCount = count(), 
            DistinctOps = dcount(OperationId),
            MostRecent = max(TimeGenerated),
            ExampleMessage = any(OuterMessage)
            by ProblemId, OuterType, OuterMethod
        | extend SignalToNoiseRatio = DistinctOps * 1.0 / RawCount
        | order by DistinctOps desc
        | top 10 by DistinctOps desc
    """,

    # STRATEGY: Machine Learning / Pattern Mining (Section 6.1)
    # Uses autocluster to find common attributes in failed requests (e.g., specific browsers, OS, or cities)
    KQLTemplate.APP_PATTERNS: """
        AppRequests
        | where TimeGenerated > ago(24h)
        | where Success == false and AppRoleName has {resource_name}
        | project ResultCode, Url, ClientCity, ClientOS, ClientBrowser
        | evaluate autocluster()
    """,

    # STRATEGY: Correlation (Section 9.1)
    # Joins Requests with Dependencies to find the downstream root cause of 5xx errors.
    KQLTemplate.DEPENDENCY_FAILURES: """
        AppRequests
        | where TimeGenerated > ago(1h) and Success == false and ResultCode startswith "5"
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
        | where TimeGenerated > ago(1h)
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
        if "impact" in template_key.lower():
            key = KQLTemplate.APP_IMPACT_ANALYSIS
        elif "pattern" in template_key.lower():
            key = KQLTemplate.APP_PATTERNS
        elif "depend" in template_key.lower():
            key = KQLTemplate.DEPENDENCY_FAILURES
        elif "sql" in template_key.lower():
            key = KQLTemplate.SQL_ERRORS
        else:
            # Default to Impact Analysis for generic "App" requests
            key = KQLTemplate.APP_IMPACT_ANALYSIS

    template = TEMPLATES.get(key)
    
    # Escape for KQL
    escaped_resource = sanitized_resource.replace('"', '""')
    escaped_value = f'"{escaped_resource}"'
    
    # Handle "Unknown" resource case specifically for Application Insights tables
    if resource_name.lower() == "unknown":
        escaped_value = '""' # Look for empty strings if unknown, or remove filter

    query = template.format(resource_name=escaped_value).strip()
    return query
