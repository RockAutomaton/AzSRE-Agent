import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)

# Maximum length for resource names to prevent excessively long inputs
MAX_RESOURCE_NAME_LENGTH = 256


class KQLTemplate(Enum):
    CONTAINER_LOGS = "container_logs"
    APP_FAILURES = "app_failures"  # Renamed from APP_EXCEPTIONS
    SQL_ERRORS = "sql_errors"


# Templates using placeholders that will be replaced with sanitized and escaped values
TEMPLATES = {
    # Standard Azure Monitor table for Container Apps (No _CL suffix)
    KQLTemplate.CONTAINER_LOGS: """
        ContainerAppConsoleLogs
        | where TimeGenerated > ago(1h)
        | where ContainerAppName has {resource_name}
        | project TimeGenerated, ContainerAppName, Log_s
        | top 20 by TimeGenerated desc
    """,
    
    # UPGRADED: Comprehensive Application Failure View
    # Combines Crashes (Exceptions), HTTP Failures (Requests), and Error Logs (Traces)
    KQLTemplate.APP_FAILURES: """
        union 
            (AppExceptions 
             | where TimeGenerated > ago(1h)
             | project TimeGenerated, Type='Crash', Message=OuterMessage, Details=Method, AppRoleName),
            (AppRequests 
             | where TimeGenerated > ago(1h) and Success == false 
             | project TimeGenerated, Type='HTTP Failure', Message=strcat(ResultCode, ' - ', Url), Details=Name, AppRoleName),
            (AppTraces 
             | where TimeGenerated > ago(1h) and SeverityLevel >= 3 
             | project TimeGenerated, Type='Error Log', Message=Message, Details=OperationName, AppRoleName)
        | where AppRoleName has {resource_name}
        | top 20 by TimeGenerated desc
    """,
    
    # App Insights Failures - for Unknown resource (empty/missing AppRoleName)
    "APP_FAILURES_UNKNOWN": """
        union 
            (AppExceptions 
             | where TimeGenerated > ago(1h)
             | project TimeGenerated, Type='Crash', Message=OuterMessage, Details=Method, AppRoleName),
            (AppRequests 
             | where TimeGenerated > ago(1h) and Success == false 
             | project TimeGenerated, Type='HTTP Failure', Message=strcat(ResultCode, ' - ', Url), Details=Name, AppRoleName),
            (AppTraces 
             | where TimeGenerated > ago(1h) and SeverityLevel >= 3 
             | project TimeGenerated, Type='Error Log', Message=Message, Details=OperationName, AppRoleName)
        | where isempty(AppRoleName)
        | top 20 by TimeGenerated desc
    """,

    # Azure Diagnostics for SQL (Standard Table)
    # Filters for SQL Errors and Timeouts specifically
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
    
    Uses a whitelist approach: allows only alphanumerics, spaces, dashes,
    underscores, dots, and forward slashes (for resource paths).
    
    Rejects inputs containing dangerous characters:
    - Newlines (\\n, \\r)
    - Pipe characters (|)
    - Backslashes (\\)
    - Comment tokens (//, /*, */)
    
    Args:
        resource_name: The resource name to sanitize
        
    Returns:
        Sanitized resource name (same as input if valid)
        
    Raises:
        ValueError: If the input is empty, too long, or contains invalid/dangerous characters
    """
    if not resource_name:
        logger.warning("KQL sanitization rejected: empty resource name")
        raise ValueError("Resource name cannot be empty")
    
    # Check length limit
    if len(resource_name) > MAX_RESOURCE_NAME_LENGTH:
        logger.warning(
            f"KQL sanitization rejected: resource name too long "
            f"(length: {len(resource_name)}, max: {MAX_RESOURCE_NAME_LENGTH}): {resource_name[:50]}..."
        )
        raise ValueError(
            f"Resource name exceeds maximum length of {MAX_RESOURCE_NAME_LENGTH} characters"
        )
    
    # Check for dangerous characters that could be used for injection
    dangerous_chars = ['\n', '\r', '|', '\\']
    for char in dangerous_chars:
        if char in resource_name:
            log_value = resource_name[:100] + "..." if len(resource_name) > 100 else resource_name
            logger.warning(
                f"KQL sanitization rejected: resource name contains dangerous character '{char}': {log_value}"
            )
            raise ValueError(
                f"Resource name contains dangerous character '{char}'. "
                f"Only alphanumerics, spaces, dashes (-), underscores (_), dots (.), and forward slashes (/) are allowed."
            )
    
    # Check for comment tokens
    comment_tokens = ['//', '/*', '*/']
    for token in comment_tokens:
        if token in resource_name:
            log_value = resource_name[:100] + "..." if len(resource_name) > 100 else resource_name
            logger.warning(
                f"KQL sanitization rejected: resource name contains comment token '{token}': {log_value}"
            )
            raise ValueError(
                f"Resource name contains comment token '{token}'. "
                f"Only alphanumerics, spaces, dashes (-), underscores (_), dots (.), and forward slashes (/) are allowed."
            )
    
    # Whitelist validation: only allow alphanumerics, spaces, dashes, underscores, dots, and forward slashes
    whitelist_pattern = re.compile(r'^[a-zA-Z0-9._\s/-]+$')
    if not whitelist_pattern.match(resource_name):
        # Log the rejected input for debugging (truncate if too long)
        log_value = resource_name[:100] + "..." if len(resource_name) > 100 else resource_name
        logger.warning(
            f"KQL sanitization rejected: resource name contains invalid characters: {log_value}"
        )
        raise ValueError(
            f"Resource name contains invalid characters. "
            f"Only alphanumerics, spaces, dashes (-), underscores (_), dots (.), and forward slashes (/) are allowed."
        )
    
    return resource_name


def get_template(template_key: str, resource_name: str) -> str:
    """
    Returns the rendered KQL query with strong input sanitization to prevent injection.
    Handles "Unknown" resource_name by using a query that filters for empty/missing AppRoleName.
    
    Inputs are validated using a whitelist approach and sanitized before being used.
    The sanitized value is properly escaped for KQL string literals (double quotes).
    
    Note: The Azure Monitor Query client doesn't support separate parameter passing,
    so we use strong sanitization + proper escaping instead of parameterized queries.
    """
    # Handle "Unknown" resource_name case before template selection
    # This prevents the WHERE clause from always being true
    if resource_name.lower() == "unknown":
        # For APP_FAILURES, use the template that filters for empty AppRoleName
        if "app" in template_key.lower():
            return TEMPLATES.get("APP_FAILURES_UNKNOWN", "").strip()
        # For other templates, we may want to handle Unknown differently
        # For now, we'll still use the regular template but the caller should be aware
    
    # Sanitize and validate resource name before use
    try:
        sanitized_resource = sanitize_resource_name(resource_name)
    except ValueError as e:
        logger.error(f"KQL template generation failed due to invalid resource name: {e}")
        raise
    
    # Normalize key to match Enum
    try:
        # Handle case-insensitive string lookup to Enum
        key = KQLTemplate(template_key.lower())
    except ValueError:
        # Fallback logic if the agent guesses a slightly wrong name
        if "container" in template_key.lower():
            key = KQLTemplate.CONTAINER_LOGS
        elif "app" in template_key.lower():
            key = KQLTemplate.APP_FAILURES
        elif "sql" in template_key.lower():
            key = KQLTemplate.SQL_ERRORS
        else:
            key = KQLTemplate.CONTAINER_LOGS  # Default to Container

    template = TEMPLATES.get(key)
    
    # Properly escape the sanitized value for KQL string literals
    # KQL uses double quotes for string literals, and escapes them by doubling
    escaped_resource = sanitized_resource.replace('"', '""')
    # Wrap in double quotes for the KQL 'has' operator
    escaped_value = f'"{escaped_resource}"'
    
    # Replace the placeholder with the escaped value
    query = template.format(resource_name=escaped_value).strip()
    
    return query
