"""
Azure Table Storage database helper.
Provides a Table Client for persisting alert history.
"""
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import HttpResponseError
import os
import logging

logger = logging.getLogger(__name__)

# We need a Storage Account URL
# e.g., "https://<your-storage-account>.table.core.windows.net"
TABLE_ENDPOINT = os.getenv("AZURE_STORAGE_TABLE_ENDPOINT")
TABLE_NAME = "AlertHistory"


def get_table_client():
    """
    Get a Table Client for Azure Table Storage.
    
    Returns:
        TableClient or None: The table client if configured, None otherwise
    """
    if not TABLE_ENDPOINT:
        logger.warning("⚠️ AZURE_STORAGE_TABLE_ENDPOINT not set. Persistence disabled.")
        return None
        
    try:
        credential = DefaultAzureCredential()
        service_client = TableServiceClient(endpoint=TABLE_ENDPOINT, credential=credential)
        
        # Try to create the table if it doesn't exist
        # Note: This may require 'Storage Account Contributor' role,
        # but data operations require 'Storage Table Data Contributor'
        try:
            service_client.create_table_if_not_exists(table_name=TABLE_NAME)
        except HttpResponseError as create_error:
            # If table creation fails due to permissions, we can still try to use the table
            # (it might already exist, or we might have data permissions but not create permissions)
            if "AuthorizationPermissionMismatch" in str(create_error) or create_error.status_code == 403:
                logger.warning(
                    "⚠️ Could not create table (may need 'Storage Account Contributor' role). "
                    "Attempting to use existing table..."
                )
            else:
                logger.warning(f"⚠️ Could not create table: {create_error}")
        
        table_client = service_client.get_table_client(table_name=TABLE_NAME)
        return table_client
        
    except HttpResponseError as e:
        if "AuthorizationPermissionMismatch" in str(e) or e.status_code == 403:
            logger.error("❌ RBAC Error: Missing 'Storage Table Data Contributor' role.")
            logger.error("   Action: Go to Azure Portal -> Storage Account -> IAM -> Add Role Assignment.")
            logger.error("   Role: 'Storage Table Data Contributor'")
            logger.error("   Assignee: Your User Account (local) or Managed Identity (cloud).")
            logger.error("   See docs/PERMISSIONS.md for detailed instructions.")
        else:
            logger.error(f"❌ Failed to initialize Table Client: {e}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Unexpected error initializing Table Client: {e}", exc_info=True)
        return None

