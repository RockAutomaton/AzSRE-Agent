@description('Azure subscription ID')
param subscriptionId string

@description('Azure region for resource deployment')
@allowed([
  'UK South'
  'uksouth'
  'eastus'
  'westus'
  'westeurope'
  'northeurope'
])
param location string

@description('Name of the Container Apps Environment')
param containerAppsEnvironmentName string

@description('Name of the Container Registry')
param containerRegistryName string

@description('Name of the main Container App (AzSRE Agent)')
param mainContainerAppName string

@description('Name of the Ollama Container App')
param ollamaContainerAppName string

@description('Name of the Application Insights component')
param applicationInsightsName string

@description('Name of the Log Analytics Workspace')
param logAnalyticsWorkspaceName string

@description('Log Analytics Workspace ID (customer ID)')
param logWorkspaceId string

@description('Container image name for the main app')
param mainAppImageName string

@description('Container image tag')
param imageTag string

@description('Ollama model name for triage')
param ollamaModelTriage string

@description('Ollama model name for analysis')
param ollamaModelAnalysis string

@description('Ollama model name for database')
param ollamaModelDatabase string

@description('Ollama model name for reporter')
param ollamaModelReporter string

@description('Ollama model name for main')
param ollamaModelMain string

@description('Workload profile name for GPU workloads')
param gpuWorkloadProfileName string

@description('Main app container CPU allocation (e.g., "0.5", "1", "2")')
param mainAppCpu string

@description('Main app container memory allocation')
param mainAppMemory string

@description('Main app target port')
param mainAppTargetPort int

@description('Ollama app container CPU allocation')
param ollamaAppCpu int

@description('Ollama app container memory allocation')
param ollamaAppMemory string

@description('Ollama app target port')
param ollamaAppTargetPort int

@description('Minimum number of replicas for container apps')
param minReplicas int

@description('Maximum number of replicas for container apps')
param maxReplicas int

@description('Main app container name')
param mainContainerName string

// Normalize location format (some resources use 'uksouth', others use 'UK South')
var normalizedLocation = location == 'UK South' ? 'uksouth' : location
var registryLoginServer = '${containerRegistryName}.azurecr.io'
var mainAppImage = '${registryLoginServer}/${mainAppImageName}:${imageTag}'
var ollamaAppImage = '${registryLoginServer}/azsre-${ollamaContainerAppName}:${imageTag}'

// Container Apps Environment
module containerAppsEnvironment 'modules/container-apps-environment.bicep' = {
  name: 'containerAppsEnvironment'
  params: {
    environmentName: containerAppsEnvironmentName
    location: location
    gpuWorkloadProfileName: gpuWorkloadProfileName
  }
}

// Container Registry
module containerRegistry 'modules/container-registry.bicep' = {
  name: 'containerRegistry'
  params: {
    registryName: containerRegistryName
    location: normalizedLocation
  }
}

// Log Analytics Workspace
module logAnalyticsWorkspace 'modules/log-analytics-workspace.bicep' = {
  name: 'logAnalyticsWorkspace'
  params: {
    workspaceName: logAnalyticsWorkspaceName
    location: normalizedLocation
  }
}

// Application Insights
module applicationInsights 'modules/application-insights.bicep' = {
  name: 'applicationInsights'
  params: {
    componentName: applicationInsightsName
    location: normalizedLocation
    workspaceResourceId: logAnalyticsWorkspace.outputs.id
  }
}

// Main Container App (AzSRE Agent)
module mainContainerApp 'modules/container-app.bicep' = {
  name: 'mainContainerApp'
  params: {
    appName: mainContainerAppName
    location: location
    managedEnvironmentId: containerAppsEnvironment.outputs.id
    workloadProfileName: gpuWorkloadProfileName
    image: mainAppImage
    containerName: mainContainerName
    targetPort: mainAppTargetPort
    externalIngress: true
    allowInsecure: false
    cpu: mainAppCpu
    memory: mainAppMemory
    registryServer: registryLoginServer
    minReplicas: minReplicas
    maxReplicas: maxReplicas
    environmentVariables: [
      {
        name: 'AZURE_SUBSCRIPTION_ID'
        value: subscriptionId
      }
      {
        name: 'LOG_WORKSPACE_ID'
        value: logWorkspaceId
      }
      {
        name: 'OLLAMA_BASE_URL'
        value: 'http://${ollamaContainerAppName}'
      }
      {
        name: 'OLLAMA_MODEL_TRIAGE'
        value: ollamaModelTriage
      }
      {
        name: 'OLLAMA_MODEL_ANALYSIS'
        value: ollamaModelAnalysis
      }
      {
        name: 'OLLAMA_MODEL_DATABASE'
        value: ollamaModelDatabase
      }
      {
        name: 'OLLAMA_MODEL_REPORTER'
        value: ollamaModelReporter
      }
      {
        name: 'OLLAMA_MODEL_MAIN'
        value: ollamaModelMain
      }
    ]
  }
}

// Ollama Container App
module ollamaContainerApp 'modules/container-app.bicep' = {
  name: 'ollamaContainerApp'
  params: {
    appName: ollamaContainerAppName
    location: location
    managedEnvironmentId: containerAppsEnvironment.outputs.id
    workloadProfileName: gpuWorkloadProfileName
    image: ollamaAppImage
    containerName: ollamaContainerAppName
    targetPort: ollamaAppTargetPort
    externalIngress: false
    allowInsecure: true
    cpu: ollamaAppCpu
    memory: ollamaAppMemory
    registryServer: registryLoginServer
    minReplicas: minReplicas
    maxReplicas: maxReplicas
  }
}

// Outputs
output containerAppsEnvironmentId string = containerAppsEnvironment.outputs.id
output containerAppsEnvironmentName string = containerAppsEnvironment.outputs.name
output containerRegistryId string = containerRegistry.outputs.id
output containerRegistryLoginServer string = containerRegistry.outputs.loginServer
output logAnalyticsWorkspaceId string = logAnalyticsWorkspace.outputs.id
output logAnalyticsWorkspaceCustomerId string = logAnalyticsWorkspace.outputs.customerId
output applicationInsightsId string = applicationInsights.outputs.id
output applicationInsightsInstrumentationKey string = applicationInsights.outputs.instrumentationKey
output applicationInsightsAppId string = applicationInsights.outputs.appId
output mainContainerAppId string = mainContainerApp.outputs.id
output ollamaContainerAppId string = ollamaContainerApp.outputs.id
