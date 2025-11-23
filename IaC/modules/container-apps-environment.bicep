@description('The name of the Container Apps Environment')
param environmentName string

@description('The Azure region where resources will be deployed')
param location string

@description('Workload profile name for GPU workloads')
param gpuWorkloadProfileName string = 'ai-age-env-pro'

@description('Enable zone redundancy')
param zoneRedundant bool = false

@description('Enable public network access')
param publicNetworkAccess string = 'Enabled'

resource managedEnvironment 'Microsoft.App/managedEnvironments@2025-02-02-preview' = {
  name: environmentName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    appLogsConfiguration: {}
    zoneRedundant: zoneRedundant
    kedaConfiguration: {}
    daprConfiguration: {}
    customDomainConfiguration: {}
    workloadProfiles: [
      {
        workloadProfileType: 'Consumption'
        name: 'Consumption'
        enableFips: false
      }
      {
        workloadProfileType: 'Consumption-GPU-NC8as-T4'
        name: gpuWorkloadProfileName
        enableFips: false
      }
    ]
    peerAuthentication: {
      mtls: {
        enabled: false
      }
    }
    peerTrafficConfiguration: {
      encryption: {
        enabled: false
      }
    }
    publicNetworkAccess: publicNetworkAccess
  }
}

output id string = managedEnvironment.id
output name string = managedEnvironment.name

