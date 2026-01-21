// Lab 04: Hosted Agents Infrastructure
// Deploys Microsoft Foundry with Capability Host and ACR for Hosted Agents

targetScope = 'resourceGroup'

@description('Main location for the resources')
param location string = 'northcentralus'

@description('Name for the AI Foundry account')
param foundryAccountName string

@description('Name for the AI Project')
param projectName string

@description('Name for the Azure Container Registry')
param acrName string

@description('Principal ID of the deployer for RBAC')
param deployerPrincipalId string

// Azure Container Registry for agent images
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

// Microsoft Foundry Account (AIServices kind)
resource foundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: foundryAccountName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: foundryAccountName
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }

  // Foundry Project
  resource project 'projects' = {
    name: projectName
    location: location
    identity: {
      type: 'SystemAssigned'
    }
    properties: {
      description: '${projectName} - Hosted Agents Project'
      displayName: projectName
    }
  }

  // Capability Host for Hosted Agents
  // Note: Created via REST API with enablePublicHostingEnvironment: true
  // Bicep schema doesn't support this property yet
  // resource agentsCapabilityHost 'capabilityHosts' = {
  //   name: 'agents'
  //   properties: {
  //     capabilityHostKind: 'Agents'
  //   }
  // }
}

// RBAC: Allow Foundry Project to pull images from ACR
resource acrPullRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '7f951dda-4ed3-4680-a7ca-43fe172d538d' // AcrPull
}

resource aiFoundryProjectCanPullFromAcr 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, foundry::project.id, acrPullRoleDefinition.id)
  properties: {
    roleDefinitionId: acrPullRoleDefinition.id
    principalId: foundry::project.identity.principalId
    principalType: 'ServicePrincipal'
    description: 'Allow AI Foundry Project to pull images from ACR'
  }
}

// RBAC: Allow deployer to push images to ACR
resource acrPushRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '8311e382-0749-4cb8-b61a-304f252e45ec' // AcrPush
}

resource currentUserCanPushToAcr 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, deployerPrincipalId, acrPushRoleDefinition.id)
  properties: {
    roleDefinitionId: acrPushRoleDefinition.id
    principalId: deployerPrincipalId
    principalType: 'User'
    description: 'Allow deployer to push images to ACR'
  }
}

// RBAC: Allow deployer to perform data actions on Foundry
resource azureAiUserRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Azure AI User
}

resource currentUserCanPerformDataActionsOnFoundry 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: foundry
  name: guid(foundry.id, deployerPrincipalId, azureAiUserRoleDefinition.id)
  properties: {
    roleDefinitionId: azureAiUserRoleDefinition.id
    principalId: deployerPrincipalId
    principalType: 'User'
    description: 'Allow deployer to perform Data actions on Foundry resource'
  }
}

// Outputs
output accountName string = foundry.name
output accountEndpoint string = foundry.properties.endpoint
output projectName string = foundry::project.name
output projectId string = foundry::project.id
output projectEndpoint string = 'https://${foundry.name}.services.ai.azure.com/api/projects/${foundry::project.name}'
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
