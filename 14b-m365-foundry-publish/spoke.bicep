targetScope = 'resourceGroup'

// ============================================================================
// Lab 14b: Publish Foundry Agents to M365 - Isolated Infrastructure
// 
// This template deploys a self-contained Foundry environment with:
// - AI Services Account with dedicated model deployment
// - Project for agent development
// - RBAC for deployer and project managed identity
// ============================================================================

param location string = resourceGroup().location
param deployerPrincipalId string
param modelName string = 'gpt-4.1-mini'

var suffix = substring(uniqueString(resourceGroup().id), 0, 6)
var aiAccountName = 'foundry-m365-${suffix}'
var projectName = 'm365-project-${suffix}'

// Azure AI User role ID (official from Microsoft Learn docs)
var azureAIUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
// Azure AI Project Manager role ID (to publish agents)
var azureAIProjectManagerRoleId = 'eadc314b-1a2d-4efa-be10-5d325db5065e'

// ============================================================================
// AI Foundry Account with Model Deployment
// ============================================================================
resource aiAccount 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: aiAccountName
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    allowProjectManagement: true
    customSubDomainName: aiAccountName
    publicNetworkAccess: 'Enabled'
  }
}

// Deploy gpt-4.1-mini model directly on the account
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiAccount
  name: modelName
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: '2025-04-14'
    }
  }
}

// ============================================================================
// Project under the Account
// ============================================================================
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: aiAccount
  name: projectName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    description: 'Project for publishing agents to Microsoft 365'
    displayName: 'M365 Agent Publishing Lab'
  }
}

// ============================================================================
// RBAC Role Assignments
// ============================================================================

// Grant deployer Cognitive Services User role on the account
resource deployerCognitiveServicesUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, deployerPrincipalId, 'CognitiveServicesUser')
  scope: aiAccount
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
  }
}

// Grant deployer Azure AI User role on the project
resource deployerAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, deployerPrincipalId, azureAIUserRoleId)
  scope: project
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAIUserRoleId)
  }
}

// Grant deployer Azure AI Project Manager role (to publish agents)
resource deployerProjectManager 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, deployerPrincipalId, azureAIProjectManagerRoleId)
  scope: project
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAIProjectManagerRoleId)
  }
}

// Grant project managed identity Azure AI User role on itself
// Required for agents to function when invoked via published applications
resource projectMIAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, 'projectMI', azureAIUserRoleId, 'self')
  scope: project
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAIUserRoleId)
  }
}

// ============================================================================
// Outputs
// ============================================================================
output accountName string = aiAccount.name
output accountEndpoint string = aiAccount.properties.endpoint
output projectName string = project.name
output projectEndpoint string = 'https://${aiAccountName}.services.ai.azure.com/api/projects/${projectName}'
output modelDeploymentName string = modelDeployment.name
output projectManagedIdentityId string = project.identity.principalId
