import os
from datetime import timedelta
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from azure.core.configuration import Configuration
from app.core.auth import get_credential


class AzureLogTool:
    def __init__(self):
        self.credential = get_credential()
        # Configure client with increased timeout (60 seconds)
        config = Configuration()
        config.connection_timeout = 60
        config.read_timeout = 60
        self.client = LogsQueryClient(self.credential, _configuration=config)
        # You must set LOG_WORKSPACE_ID in your .env file
        self.workspace_id = os.getenv("LOG_WORKSPACE_ID")

    def run_query(self, query: str, timespan_minutes: int = 30) -> str:
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
                return f"Partial Error: {response.partial_error.message}"
            
            if response.status == LogsQueryStatus.FAILURE:
                return f"Query Failed: {response.status}"

            if not response.tables:
                return "No tables returned"

            table = response.tables[0]
            results = []
            
            # FIX: Handle cases where columns are strings vs objects
            columns = []
            for col in table.columns:
                if hasattr(col, 'name'):
                    columns.append(col.name)
                else:
                    columns.append(str(col))
            
            for row in table.rows:
                # Create a compact dict for each row
                row_dict = dict(zip(columns, row))
                results.append(str(row_dict))

            if not results:
                return "No logs found."

            return "\n".join(results[:10])

        except Exception as e:
            return f"Execution Error: {str(e)}"
