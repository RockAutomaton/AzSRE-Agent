@description('The name of the Log Analytics Workspace')
param workspaceName string

@description('The Azure region where resources will be deployed')
param location string

@description('The SKU name for the workspace')
param skuName string = 'PerGB2018'

@description('Retention in days')
param retentionInDays int = 30

@description('Daily quota in GB (-1 for unlimited)')
param dailyQuotaGb int = -1

@description('Enable public network access for ingestion')
param publicNetworkAccessForIngestion string = 'Enabled'

@description('Enable public network access for query')
param publicNetworkAccessForQuery string = 'Enabled'

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2025-02-01' = {
  name: workspaceName
  location: location
  properties: {
    sku: {
      name: skuName
    }
    retentionInDays: retentionInDays
    features: {
      legacy: 0
      searchVersion: 1
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    workspaceCapping: {
      dailyQuotaGb: json(string(dailyQuotaGb))
    }
    publicNetworkAccessForIngestion: publicNetworkAccessForIngestion
    publicNetworkAccessForQuery: publicNetworkAccessForQuery
  }
}

output id string = logAnalyticsWorkspace.id
output name string = logAnalyticsWorkspace.name
output customerId string = logAnalyticsWorkspace.properties.customerId

