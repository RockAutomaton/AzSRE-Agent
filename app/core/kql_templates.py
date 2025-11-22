from enum import Enum


class KQLTemplate(Enum):
    CONTAINER_LOGS = "container_logs"
    APP_EXCEPTIONS = "app_exceptions"
    SQL_ERRORS = "sql_errors"


TEMPLATES = {
    # Standard Azure Monitor table for Container Apps (No _CL suffix)
    KQLTemplate.CONTAINER_LOGS: """
        ContainerAppConsoleLogs
        | where TimeGenerated > ago(1h)
        | where ContainerAppName has "{resource_name}"
        | project TimeGenerated, ContainerAppName, Log_s
        | top 20 by TimeGenerated desc
    """,
    
    # App Insights Exceptions (Standard Table)
    KQLTemplate.APP_EXCEPTIONS: """
        AppExceptions
        | where TimeGenerated > ago(24h)
        | where AppRoleName has "{resource_name}" or "{resource_name}" == "Unknown"
        | summarize Count=count() by ProblemId, OuterMessage
        | top 5 by Count desc
    """,

    # Azure Diagnostics for SQL (Standard Table)
    # Filters for SQL Errors and Timeouts specifically
    KQLTemplate.SQL_ERRORS: """
        AzureDiagnostics
        | where TimeGenerated > ago(1h)
        | where Resource has "{resource_name}"
        | where Category == "SQLErrors" or Category == "Timeouts"
        | project TimeGenerated, error_number_d, Message
        | top 20 by TimeGenerated desc
    """
}


def get_template(template_key: str, resource_name: str) -> str:
    """
    Returns the rendered KQL query.
    """
    # Normalize key to match Enum
    try:
        # Handle case-insensitive string lookup to Enum
        key = KQLTemplate(template_key.lower())
    except ValueError:
        # Fallback logic if the agent guesses a slightly wrong name
        if "container" in template_key.lower():
            key = KQLTemplate.CONTAINER_LOGS
        elif "app" in template_key.lower():
            key = KQLTemplate.APP_EXCEPTIONS
        elif "sql" in template_key.lower():
            key = KQLTemplate.SQL_ERRORS
        else:
            key = KQLTemplate.CONTAINER_LOGS  # Default to Container

    template = TEMPLATES.get(key)
    
    # Clean inputs to prevent KQL injection
    clean_resource = resource_name.replace("'", "").replace('"', "")
    return template.format(resource_name=clean_resource).strip()
