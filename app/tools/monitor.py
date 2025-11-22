import os
from datetime import timedelta
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from app.core.auth import get_credential


class AzureLogTool:
    def __init__(self):
        self.credential = get_credential()
        self.client = LogsQueryClient(self.credential)
        # You must set LOG_WORKSPACE_ID in your .env file
        self.workspace_id = os.getenv("LOG_WORKSPACE_ID")

    def run_query(self, query: str, timespan_minutes: int = 15) -> str:
        """
        Executes a KQL query and returns the results as a string table.
        """
        if not self.workspace_id:
            return "Error: LOG_WORKSPACE_ID is not set in environment."

        try:
            response = self.client.query_workspace(
                workspace_id=self.workspace_id,
                query=query,
                timespan=timedelta(minutes=timespan_minutes)
            )

            if response.status == LogsQueryStatus.PARTIAL:
                error = response.partial_error
                return f"Partial Error: {error.message}"
            
            if response.status == LogsQueryStatus.FAILURE:
                return f"Query Failed: {response.status}"

            # Format results into a readable string for the LLM
            table = response.tables[0]
            results = []
            columns = [col.name for col in table.columns]
            
            for row in table.rows:
                # Create a compact dict for each row
                row_dict = dict(zip(columns, row))
                results.append(str(row_dict))

            return "\n".join(results[:10])  # Limit to 10 rows to save context window

        except Exception as e:
            return f"Execution Error: {str(e)}"

