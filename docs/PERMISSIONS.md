# Azure Permissions Guide

This guide explains what Azure permissions your account needs to run the Azure SRE Agent locally.

## Services Accessed

The application accesses three Azure services:

1. **Azure Log Analytics Workspace** - Query logs using KQL
2. **Azure Monitor Metrics** - Retrieve resource metrics (CPU, Memory, etc.)
3. **Azure Table Storage** - Store alert history

## Required Permissions

### For Local Development (Azure CLI)

When running locally with `az login`, your account needs the following **RBAC roles**:

#### 1. Log Analytics Workspace

**Required Role**: `Log Analytics Reader` or `Reader`

**Scope**: Log Analytics Workspace (or Resource Group/Subscription)

**What it allows**:
- Read logs from the workspace
- Execute KQL queries
- Access Application Insights data

**How to assign**:
```bash
# Get your workspace resource ID
WORKSPACE_ID=$(az monitor log-analytics workspace show \
  --workspace-name <your-workspace-name> \
  --resource-group <your-resource-group> \
  --query id -o tsv)

# Get your user principal name or object ID
USER_EMAIL=$(az account show --query user.name -o tsv)

# Assign the role
az role assignment create \
  --role "Log Analytics Reader" \
  --assignee "$USER_EMAIL" \
  --scope "$WORKSPACE_ID"
```

#### 2. Monitor Metrics

**Required Role**: `Monitoring Reader` or `Reader`

**Scope**: Subscription or Resource Groups (depending on which resources you monitor)

**What it allows**:
- Read metrics from Azure resources
- Access Monitor API

**How to assign**:
```bash
# Get your subscription ID
SUB_ID=$(az account show --query id -o tsv)

# Assign the role at subscription level (applies to all resources)
az role assignment create \
  --role "Monitoring Reader" \
  --assignee "$USER_EMAIL" \
  --scope "/subscriptions/$SUB_ID"
```

**Alternative**: If you only need access to specific resource groups:
```bash
# Assign at resource group level
az role assignment create \
  --role "Monitoring Reader" \
  --assignee "$USER_EMAIL" \
  --scope "/subscriptions/$SUB_ID/resourceGroups/<your-resource-group>"
```

#### 3. Table Storage

**Required Role**: `Storage Table Data Contributor` or `Storage Table Data Reader` + `Storage Account Contributor`

**Scope**: Storage Account

**What it allows**:
- Create/read/write entities in Table Storage
- Create tables if they don't exist

**How to assign**:
```bash
# Get your storage account resource ID
STORAGE_ACCOUNT_ID=$(az storage account show \
  --name <your-storage-account-name> \
  --resource-group <your-resource-group> \
  --query id -o tsv)

# Assign the role
az role assignment create \
  --role "Storage Table Data Contributor" \
  --assignee "$USER_EMAIL" \
  --scope "$STORAGE_ACCOUNT_ID"
```

## Quick Setup Script

Here's a script to assign all required permissions at once:

```bash
#!/bin/bash
# assign_permissions.sh

# Get current user and subscription
USER_EMAIL=$(az account show --query user.name -o tsv)
SUB_ID=$(az account show --query id -o tsv)

# Set your resource names
WORKSPACE_NAME="your-workspace-name"
WORKSPACE_RG="your-workspace-resource-group"
STORAGE_ACCOUNT_NAME="your-storage-account-name"
STORAGE_RG="your-storage-resource-group"

# Get resource IDs
WORKSPACE_ID=$(az monitor log-analytics workspace show \
  --workspace-name "$WORKSPACE_NAME" \
  --resource-group "$WORKSPACE_RG" \
  --query id -o tsv)

STORAGE_ACCOUNT_ID=$(az storage account show \
  --name "$STORAGE_ACCOUNT_NAME" \
  --resource-group "$STORAGE_RG" \
  --query id -o tsv)

# Assign Log Analytics Reader
echo "Assigning Log Analytics Reader role..."
az role assignment create \
  --role "Log Analytics Reader" \
  --assignee "$USER_EMAIL" \
  --scope "$WORKSPACE_ID" \
  --output none

# Assign Monitoring Reader at subscription level
echo "Assigning Monitoring Reader role..."
az role assignment create \
  --role "Monitoring Reader" \
  --assignee "$USER_EMAIL" \
  --scope "/subscriptions/$SUB_ID" \
  --output none

# Assign Storage Table Data Contributor
echo "Assigning Storage Table Data Contributor role..."
az role assignment create \
  --role "Storage Table Data Contributor" \
  --assignee "$USER_EMAIL" \
  --scope "$STORAGE_ACCOUNT_ID" \
  --output none

echo "✅ All permissions assigned!"
```

## Verify Permissions

Check if you have the required permissions:

```bash
# Check Log Analytics permissions
az role assignment list \
  --assignee "$(az account show --query user.name -o tsv)" \
  --scope "$WORKSPACE_ID" \
  --query "[].roleDefinitionName" -o tsv

# Check Monitor permissions
az role assignment list \
  --assignee "$(az account show --query user.name -o tsv)" \
  --scope "/subscriptions/$(az account show --query id -o tsv)" \
  --query "[?roleDefinitionName=='Monitoring Reader'].roleDefinitionName" -o tsv

# Check Storage permissions
az role assignment list \
  --assignee "$(az account show --query user.name -o tsv)" \
  --scope "$STORAGE_ACCOUNT_ID" \
  --query "[].roleDefinitionName" -o tsv
```

## Common Permission Errors

### Error: "The client does not have authorization to perform action"

**Cause**: Missing RBAC role assignment

**Solution**: Assign the appropriate role using the commands above

### Error: "Operation returned an invalid status 'Forbidden'"

**Cause**: Insufficient permissions or wrong scope

**Solution**: 
1. Verify the role is assigned at the correct scope
2. Wait a few minutes for role propagation
3. Re-authenticate: `az login`

### Error: "DefaultAzureCredential failed to retrieve a token"

**Cause**: Not authenticated with Azure CLI

**Solution**:
```bash
az login
az account show  # Verify authentication
```

## Minimum Required Roles Summary

| Service | Minimum Role | Scope |
|---------|-------------|-------|
| Log Analytics | `Log Analytics Reader` | Workspace |
| Monitor Metrics | `Monitoring Reader` | Subscription/Resource Group |
| Table Storage | `Storage Table Data Contributor` | Storage Account |

## Alternative: Custom Role

If you need more granular permissions, you can create a custom role with only the specific actions needed:

```json
{
  "Name": "SRE Agent Custom Role",
  "Description": "Minimal permissions for Azure SRE Agent",
  "Actions": [
    "Microsoft.OperationalInsights/workspaces/query/read",
    "Microsoft.Insights/metrics/read",
    "Microsoft.Storage/storageAccounts/tableServices/tables/read",
    "Microsoft.Storage/storageAccounts/tableServices/tables/write",
    "Microsoft.Storage/storageAccounts/tableServices/tables/entities/read",
    "Microsoft.Storage/storageAccounts/tableServices/tables/entities/write"
  ],
  "AssignableScopes": ["/subscriptions/<your-subscription-id>"]
}
```

## For Production (Managed Identity)

When running in Azure (e.g., Container Apps), use **Managed Identity** instead of Azure CLI:

1. Enable Managed Identity on your resource
2. Assign the same RBAC roles to the Managed Identity
3. The application will automatically use Managed Identity (via `DefaultAzureCredential`)

```bash
# Get Managed Identity principal ID
MI_PRINCIPAL_ID=$(az containerapp show \
  --name <your-app-name> \
  --resource-group <your-rg> \
  --query identity.principalId -o tsv)

# Assign roles to Managed Identity (same as above, but use $MI_PRINCIPAL_ID instead of $USER_EMAIL)
az role assignment create \
  --role "Log Analytics Reader" \
  --assignee "$MI_PRINCIPAL_ID" \
  --scope "$WORKSPACE_ID"
```

## Troubleshooting

### Check Current Permissions

```bash
# List all your role assignments
az role assignment list \
  --assignee "$(az account show --query user.name -o tsv)" \
  --all \
  --query "[].{Role:roleDefinitionName, Scope:scope}" -o table
```

### Test Access

```bash
# Test Log Analytics access
az monitor log-analytics workspace query \
  --workspace <your-workspace-name> \
  --analytics-query "AzureActivity | take 1"

# Test Metrics access
az monitor metrics list \
  --resource <resource-id> \
  --metric "Percentage CPU"

# Test Table Storage access
az storage table exists \
  --name "AlertHistory" \
  --account-name <your-storage-account>
```

## Notes

- **Role Propagation**: RBAC role assignments can take up to 5 minutes to propagate
- **Subscription vs Resource Group**: Assigning at subscription level gives access to all resources, but may be too broad for production
- **Storage Account Keys**: The application uses Azure AD authentication (not storage account keys), so RBAC roles are required
- **Table Storage Endpoint**: Make sure `AZURE_STORAGE_TABLE_ENDPOINT` in your `.env` points to the correct storage account

