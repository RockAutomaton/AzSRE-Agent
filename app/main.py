# Load environment variables from .env file first
from dotenv import load_dotenv
load_dotenv()

import json
import logging
import traceback
import uuid
import re
from datetime import datetime
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.schemas import AzureWebhookPayload
from app.graph.workflow import build_graph
from app.graph.state import AgentState
from app.core.ollama_config import get_ollama_base_url, get_ollama_model_main
from app.core.database import get_table_client
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

# Configure logging
logger = logging.getLogger(__name__)


def sanitize_row_key(alert_id: str) -> str:
    """
    Sanitize alert ID for use as Azure Table Storage RowKey.
    
    Azure Table Storage RowKey constraints:
    - Max 1 KB
    - Cannot contain: /, \\, #, ?
    - Must be a valid string
    
    Args:
        alert_id: The alert ID (may be a full resource path)
    
    Returns:
        Sanitized string safe for use as RowKey
    """
    # Extract just the alert ID part (last segment after /)
    if "/" in alert_id:
        alert_id = alert_id.rsplit("/", 1)[-1]
    
    # Replace invalid characters with underscores
    # Azure Table Storage doesn't allow: /, \, #, ?
    sanitized = re.sub(r'[/\\#?]', '_', alert_id)
    
    # Truncate to ensure we're under 1KB (leaving room for UUID suffix)
    # UUID hex[:8] is 8 chars, plus '-' is 1 char = 9 chars
    # So we limit to ~1000 chars to be safe
    max_length = 1000
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def validate_row_key(row_key: str) -> bool:
    """
    Validate row_key against a safe whitelist pattern to prevent OData injection.
    
    Args:
        row_key: The row key to validate
    
    Returns:
        True if the row_key matches the safe pattern, False otherwise
    """
    # Safe pattern: only alphanumerics, hyphens, underscores, and dots
    # This matches the format used in sanitize_row_key and UUID hex patterns
    safe_pattern = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
    return bool(safe_pattern.match(row_key))


def escape_odata_string(value: str) -> str:
    """
    Escape a string value for safe use in OData filter expressions.
    Per OData rules, single quotes must be doubled.
    
    Args:
        value: The string value to escape
    
    Returns:
        Escaped string safe for OData filter interpolation
    """
    # OData string literals: single quotes must be doubled
    return value.replace("'", "''")

# 1. Initialize the FastAPI App
app = FastAPI(title="Azure Alert Agent")

# --- CORS Configuration ---
origins = [
    "http://localhost:3000",  # Next.js Frontend
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Setup the Local LLM (Ollama)
ollama_base_url = get_ollama_base_url()
ollama_model = get_ollama_model_main()
logger.info(f"Connecting to Ollama at: {ollama_base_url} with model: {ollama_model}")
llm = ChatOllama(
    model=ollama_model,
    temperature=0,  # Keep it deterministic for alerts
    base_url=ollama_base_url,
)

# 3. Initialize the workflow graph
try:
    graph = build_graph()
except Exception as e:
    logger.error(
        f"Failed to initialize workflow graph: {str(e)}\n"
        f"Traceback:\n{traceback.format_exc()}",
        exc_info=True
    )
    graph = None

# --- Context Helper ---
def get_recent_alerts_context(limit=10) -> str:
    """
    Fetches recent alerts from Table Storage and formats them as a context string.
    """
    try:
        table_client = get_table_client()
        if not table_client:
            return "System: Database connection unavailable. No alert history found."
            
        # Fetch all (inefficient for large DBs, but fine for <1000 rows)
        # Production improvement: Use OData filter for timestamp
        entities = list(table_client.list_entities())
        
        # Sort by CreatedAt descending
        sorted_alerts = sorted(entities, key=lambda x: x.get("CreatedAt", ""), reverse=True)[:limit]
        
        if not sorted_alerts:
            return "System: No alerts have been recorded yet."

        context_lines = ["Here is a summary of the most recent alerts processed by the agent:"]
        for alert in sorted_alerts:
            # Parse report summary if available
            summary = alert.get('ReportSummary', 'No summary available')
            timestamp = alert.get('CreatedAt', 'Unknown time')
            severity = alert.get('Severity', 'Unknown')
            rule = alert.get('RuleName', 'Unknown Rule')
            classification = alert.get('PartitionKey', 'UNKNOWN')
            
            line = f"- [{timestamp}] {severity} {classification}: {rule} | Summary: {summary}"
            context_lines.append(line)
            
        return "\n".join(context_lines)
    except Exception as e:
        logger.error(f"Context fetch error: {e}")
        return f"System: Error retrieving alert history: {e}"


def detect_alert_type_from_query(query: str) -> str | None:
    """
    Detects if the query is asking about patterns in a specific alert type.
    Returns the alert type (e.g., 'APP', 'INFRA', 'DATABASE', 'NETWORK') if detected, None otherwise.
    """
    query_upper = query.upper()
    
    # Common patterns: "common patterns in APP alerts", "patterns in APP", etc.
    alert_types = ['APP', 'INFRA', 'DATABASE', 'DB', 'SQL', 'NETWORK']
    
    for alert_type in alert_types:
        # Check for patterns like "APP alerts", "APP type", "in APP", etc.
        if f"{alert_type} ALERT" in query_upper or \
           f"PATTERNS IN {alert_type}" in query_upper or \
           f"COMMON PATTERNS IN {alert_type}" in query_upper or \
           (f" {alert_type} " in query_upper and ("PATTERN" in query_upper or "COMMON" in query_upper)):
            # Normalize DB/SQL to DATABASE
            if alert_type in ['DB', 'SQL']:
                return 'DATABASE'
            return alert_type
    
    return None


def get_pattern_analysis_for_type(alert_type: str, limit=50) -> str:
    """
    Analyzes patterns across alerts of a specific type by examining their reports.
    Returns a detailed context string with common patterns, root causes, and trends.
    """
    try:
        table_client = get_table_client()
        if not table_client:
            return f"System: Database connection unavailable. Cannot analyze {alert_type} alert patterns."
        
        # Fetch all alerts
        entities = list(table_client.list_entities())
        
        # Filter by alert type (PartitionKey)
        filtered_alerts = [a for a in entities if a.get('PartitionKey', '').upper() == alert_type.upper()]
        
        if not filtered_alerts:
            return f"System: No {alert_type} alerts found in the history. Cannot analyze patterns."
        
        # Sort by CreatedAt descending and limit
        sorted_alerts = sorted(filtered_alerts, key=lambda x: x.get("CreatedAt", ""), reverse=True)[:limit]
        
        # Build detailed context with full report data
        context_lines = [
            f"=== PATTERN ANALYSIS: {alert_type} ALERTS ===",
            f"Total {alert_type} alerts analyzed: {len(sorted_alerts)}",
            "",
            "DETAILED ALERT DATA:"
        ]
        
        # Collect all report data for pattern analysis
        all_summaries = []
        all_reports = []
        rule_names = []
        severities = []
        
        for alert in sorted_alerts:
            timestamp = alert.get('CreatedAt', 'Unknown time')
            severity = alert.get('Severity', 'Unknown')
            rule = alert.get('RuleName', 'Unknown Rule')
            summary = alert.get('ReportSummary', 'No summary available')
            report_json_str = alert.get('ReportJson', '{}')
            
            # Parse ReportJson if available
            report_data = {}
            try:
                if isinstance(report_json_str, str):
                    report_data = json.loads(report_json_str)
                elif isinstance(report_json_str, dict):
                    report_data = report_json_str
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse ReportJson as JSON: {e}. Alert: {alert.get('RuleName', 'Unknown')}")
                report_data = {}
            except TypeError as e:
                logger.warning(f"Unexpected type for ReportJson: {type(report_json_str)}. Error: {e}. Alert: {alert.get('RuleName', 'Unknown')}")
                report_data = {}
            
            # Collect data for pattern analysis
            all_summaries.append(summary)
            all_reports.append(report_data)
            rule_names.append(rule)
            severities.append(severity)
            
            # Add detailed entry
            context_lines.append(f"\n--- Alert: {rule} [{severity}] @ {timestamp} ---")
            context_lines.append(f"Summary: {summary}")
            
            # Add structured report data if available
            if report_data:
                if isinstance(report_data, dict):
                    if 'root_cause' in report_data:
                        context_lines.append(f"Root Cause: {report_data.get('root_cause', 'N/A')}")
                    if 'recommendations' in report_data:
                        recs = report_data.get('recommendations', [])
                        if recs:
                            context_lines.append(f"Recommendations: {', '.join(recs) if isinstance(recs, list) else str(recs)}")
                    if 'evidence' in report_data:
                        evidence = report_data.get('evidence', [])
                        if evidence:
                            context_lines.append(f"Evidence: {len(evidence)} items found")
        
        # Add pattern summary section
        context_lines.append("\n=== PATTERN SUMMARY ===")
        context_lines.append(f"Most common rule names: {', '.join(set(rule_names[:5]))}")
        context_lines.append(f"Severity distribution: {', '.join(set(severities))}")
        context_lines.append(f"\nAll summaries for pattern detection:")
        for i, summary in enumerate(all_summaries, 1):
            context_lines.append(f"{i}. {summary}")
        
        return "\n".join(context_lines)
        
    except Exception as e:
        logger.error(f"Pattern analysis error for {alert_type}: {e}")
        return f"System: Error analyzing {alert_type} alert patterns: {e}"


def get_smart_context(query: str, default_limit=10) -> str:
    """
    Intelligently determines what context to provide based on the query.
    If the query asks about patterns in a specific alert type, returns detailed pattern analysis.
    Otherwise, returns general recent alerts context.
    """
    # Check if this is a pattern query for a specific alert type
    alert_type = detect_alert_type_from_query(query)
    
    if alert_type:
        logger.info(f"Detected pattern query for alert type: {alert_type}")
        return get_pattern_analysis_for_type(alert_type, limit=50)
    else:
        # Default to recent alerts
        return get_recent_alerts_context(limit=default_limit)

# 4. Define the Chain with Context
# We create a prompt that includes alert history context
chat_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are the Azure SRE Agent Assistant, specialized in analyzing alerts and incidents.

    CONTEXT:
    {alert_context}
    
    YOUR SCOPE:
    You ONLY answer questions related to:
    - Azure alerts and incidents (from the context above)
    - Alert history and investigations
    - KQL query syntax and Azure Monitor queries
    - Troubleshooting Azure resources based on alert data
    - Root cause analysis of incidents
    - Recommendations for resolving alert issues
    - **Pattern analysis across alert types** (e.g., "What are common patterns in APP alerts?")
    
    RESTRICTIONS:
    - Do NOT answer general questions about Azure services, pricing, or features
    - Do NOT answer questions unrelated to alerts, monitoring, or incidents
    - Do NOT provide general Azure tutorials or documentation
    - If asked an off-topic question, politely redirect: "I specialize in analyzing alerts and incidents. I can help you with questions about alert history, KQL queries, or troubleshooting based on the alerts we've processed."
    
    INSTRUCTIONS:
    - Use the Alert History context above to answer questions about recent incidents.
    - **For pattern analysis queries** (e.g., "What are common patterns in APP alerts?"):
      * Analyze the detailed alert data provided in the context
      * Identify common root causes, error patterns, and trends
      * Group similar issues together
      * Provide actionable insights and recommendations
      * Highlight the most frequent patterns first
    - If the user asks about a specific alert, summarize the findings from the history.
    - **FORMATTING**: Use Markdown. Use **bold** for key terms, `code blocks` for KQL/Commands, and lists for readability.
      * For pattern analysis, use clear sections with headers (## Common Patterns, ## Root Causes, ## Recommendations)
    - If the answer is not in the context but is alert-related, use your knowledge of Azure monitoring and troubleshooting.
    - Be professional, concise, and helpful.
    """),
    ("user", "{input}"),
])
chat_chain = chat_prompt | llm | StrOutputParser()


# 5. Define Input Data Model
class ChatRequest(BaseModel):
    message: str


# 6. Azure Webhook Endpoint
@app.post("/webhook/azure")
async def azure_webhook(payload: AzureWebhookPayload):
    """
    Receives Azure Monitor alerts and processes them through the agent workflow.
    """
    # Verify graph is initialized before any graph-dependent logic
    if graph is None:
        logger.error("Workflow graph not initialized - cannot process alert")
        raise HTTPException(
            status_code=503,
            detail="workflow graph not initialized"
        )
    
    # Initialize state
    initial_state: AgentState = {
        "alert_data": payload.data,
        "investigation_steps": [],
        "final_report": None,
        "classification": None,
    }
    
    # Run the workflow
    final_state = await graph.ainvoke(initial_state)
    
    # Save to Azure Table Storage
    try:
        table_client = get_table_client()
        if table_client:
            # Sanitize the alert ID for use as RowKey
            sanitized_alert_id = sanitize_row_key(payload.data.essentials.alertId)
            row_key = f"{sanitized_alert_id}-{uuid.uuid4().hex[:8]}"
            
            # Handle structured report (dict) vs legacy string format
            final_report = final_state.get("final_report", {})
            if isinstance(final_report, dict):
                # New structured format
                report_summary = final_report.get("summary", "No summary")
                report_json = json.dumps(final_report, default=str)
            else:
                # Legacy string format (fallback)
                report_summary = str(final_report) if final_report else "No report"
                report_json = json.dumps({"summary": report_summary}, default=str)
            
            alert_entity = {
                "PartitionKey": final_state.get("classification", "UNKNOWN"),
                "RowKey": row_key,
                "AlertId": payload.data.essentials.alertId,
                "RuleName": payload.data.essentials.alertRule,
                "Severity": payload.data.essentials.severity,
                "FiredTime": payload.data.essentials.firedDateTime,
                "ReportSummary": report_summary,  # Short summary for list view
                "ReportJson": report_json,        # Full structured report
                "RawData": json.dumps(payload.model_dump(), default=str),
                "CreatedAt": datetime.utcnow().isoformat()
            }
            table_client.create_entity(entity=alert_entity)
            logger.info(f"✅ Alert saved to Table Storage: {alert_entity['RowKey']}")
    except HttpResponseError as e:
        if e.status_code == 403:
            logger.error("❌ 403 Forbidden saving to DB. Check 'Storage Table Data Contributor' role.")
            logger.error("   See docs/PERMISSIONS.md for remediation steps.")
        else:
            logger.error(f"❌ Azure Table Error: {e}")
    except Exception as e:
        logger.error(f"❌ Failed to save to Table Storage: {e}", exc_info=True)
    
    # Return the results
    # Handle both structured (dict) and legacy (string) report formats
    final_report = final_state.get("final_report", {})
    if isinstance(final_report, dict):
        # Return structured report
        return {
            "classification": final_state.get("classification", "UNKNOWN"),
            "report": final_report,  # Full structured report
            "steps": final_state.get("investigation_steps", []),
        }
    else:
        # Legacy string format
        return {
            "classification": final_state.get("classification", "UNKNOWN"),
            "report": str(final_report) if final_report else "No report generated",
            "steps": final_state.get("investigation_steps", []),
        }


# 7. Standard Endpoint (Waits for full response)
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Simple endpoint that waits for the LLM to finish generating
    the entire response before sending it back.
    """
    # Fetch smart context based on query type
    context_str = get_smart_context(request.message, default_limit=10)
    response = await chat_chain.ainvoke({
        "input": request.message,
        "alert_context": context_str
    })
    return {"response": response}


# 8. Streaming Endpoint (Real-time chunks)
@app.post("/stream")
async def stream_endpoint(request: ChatRequest):
    """
    Advanced endpoint that streams the response token-by-token.
    This prevents the webhook from timing out on long generations.
    Includes alert history context for RAG.
    """
    # 1. Fetch smart context based on query type
    context_str = get_smart_context(request.message, default_limit=10)
    
    async def generate():
        # 2. Pass context to chain
        async for chunk in chat_chain.astream({
            "input": request.message,
            "alert_context": context_str
        }):
            yield chunk
            
    return StreamingResponse(generate(), media_type="text/event-stream")


# 9. History Endpoint
@app.get("/api/history")
async def get_history():
    """
    Fetch recent alerts from Azure Table Storage.
    """
    try:
        table_client = get_table_client()
        if not table_client:
            return []
        
        # List all entities (In prod, use OData filter for timestamp)
        entities = table_client.list_entities()
        # Sort in memory by CreatedAt desc
        sorted_alerts = sorted(entities, key=lambda x: x.get("CreatedAt", ""), reverse=True)
        return sorted_alerts[:50]  # Limit to 50
    except Exception as e:
        logger.error(f"Error fetching history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# 10. Single Alert Endpoint
@app.get("/api/alerts/{row_key}")
async def get_alert(row_key: str, partition_key: str | None = None):
    """
    Fetch a single alert entity by RowKey.
    
    Args:
        row_key: The RowKey of the alert entity
        partition_key: Optional PartitionKey for efficient direct lookup using get_entity.
                      If provided, uses parameterized access (preferred). If not provided,
                      validates and safely queries by RowKey.
    """
    try:
        table_client = get_table_client()
        if not table_client:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Validate row_key against safe whitelist pattern to prevent injection
        if not validate_row_key(row_key):
            raise HTTPException(
                status_code=400,
                detail="Invalid row_key format. Only alphanumerics, hyphens, underscores, and dots are allowed."
            )
        
        # Preferred: Use parameterized get_entity if partition_key is provided
        if partition_key:
            # Validate partition_key as well
            if not validate_row_key(partition_key):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid partition_key format. Only alphanumerics, hyphens, underscores, and dots are allowed."
                )
            try:
                entity = table_client.get_entity(partition_key=partition_key, row_key=row_key)
                return entity
            except ResourceNotFoundError:
                raise HTTPException(status_code=404, detail="Alert not found")
        
        # Fallback: Use OData filter with proper escaping
        # Escape single quotes by doubling them per OData rules
        escaped_row_key = escape_odata_string(row_key)
        filter_query = f"RowKey eq '{escaped_row_key}'"
        entities = list(table_client.query_entities(query_filter=filter_query))
        
        if not entities:
            raise HTTPException(status_code=404, detail="Alert not found")
            
        return entities[0]
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error fetching alert {row_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 11. Run the Server
if __name__ == "__main__":
    # Run with: python main.py
    uvicorn.run(app, host="0.0.0.0", port=8000)
