@description('The name of the Container App')
param appName string

@description('The Azure region where resources will be deployed')
param location string

@description('The Container Apps Environment resource ID')
param managedEnvironmentId string

@description('The workload profile name')
param workloadProfileName string = 'Consumption'

@description('Container image name')
param image string

@description('Container name')
param containerName string

@description('Target port for ingress')
param targetPort int

@description('Enable external ingress')
param externalIngress bool = true

@description('Allow insecure connections')
param allowInsecure bool = false

@description('Container CPU allocation')
param cpu string | int

@description('Container memory allocation')
param memory string

@description('Environment variables for the container')
param environmentVariables array = []

@description('Minimum number of replicas')
param minReplicas int = 0

@description('Maximum number of replicas')
param maxReplicas int = 10

@description('Cooldown period in seconds')
param cooldownPeriod int = 300

@description('Polling interval in seconds')
param pollingInterval int = 30

@description('Container Registry login server')
param registryServer string

resource containerApp 'Microsoft.App/containerapps@2025-02-02-preview' = {
  name: appName
  location: location
  kind: 'containerapps'
  identity: {
    type: 'None'
  }
  properties: {
    managedEnvironmentId: managedEnvironmentId
    environmentId: managedEnvironmentId
    workloadProfileName: workloadProfileName
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: externalIngress
        targetPort: targetPort
        exposedPort: 0
        transport: 'Auto'
        traffic: [
          {
            weight: 100
            latestRevision: true
          }
        ]
        allowInsecure: allowInsecure
        clientCertificateMode: 'Ignore'
        stickySessions: {
          affinity: 'none'
        }
      }
      registries: [
        {
          server: registryServer
          identity: 'system-environment'
        }
      ]
      identitySettings: []
      maxInactiveRevisions: 100
    }
    template: {
      containers: [
        {
          image: image
          imageType: 'ContainerImage'
          name: containerName
          env: environmentVariables
          resources: {
            cpu: cpu
            memory: memory
          }
          probes: []
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        cooldownPeriod: cooldownPeriod
        pollingInterval: pollingInterval
      }
      volumes: []
    }
  }
}

output id string = containerApp.id
output name string = containerApp.name

