// ============================================================================
// Lab 7c: Web Search Tool Spoke
// ============================================================================
// Uses the built-in Web Search Preview Tool in Foundry Agent Service.
// No separate Bing resource needed - web search is a native capability.
// This template deploys:
// - AI Foundry Account with local chat model (required for web search)
// - APIM connection for agent invocation
// ============================================================================
targetScope = 'resourceGroup'

param location string = resourceGroup().location
param deployerPrincipalId string
param apimUrl string
param gatewayModelName string = 'gpt-4.1-mini'
param localChatModel string = 'gpt-4.1-mini'
@secure()
param apimSubscriptionKey string

var suffix = substring(uniqueString(resourceGroup().id), 0, 6)
var aiAccountName = 'websearch-spoke-${suffix}'
var projectName = 'websearch-project'

// ─────────────────────────────────────────────────────────────────────────────
// AI Foundry Account with local model (required for web search tool)
// ─────────────────────────────────────────────────────────────────────────────
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

// Local chat model - REQUIRED for web search tool internal processing
resource chatModel 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiAccount
  name: localChatModel
  sku: { name: 'GlobalStandard', capacity: 30 }
  properties: {
    model: { name: localChatModel, format: 'OpenAI', version: '2025-04-14' }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Project
// ─────────────────────────────────────────────────────────────────────────────
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: aiAccount
  name: projectName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    description: 'Web Search Lab - Real-time web search for agents'
    displayName: 'Web Search Project'
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// APIM Connection (gateway access for agent invocation)
// ─────────────────────────────────────────────────────────────────────────────
resource apimConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: 'landing-zone-apim'
  properties: {
    category: 'ApiManagement'
    target: apimUrl
    authType: 'ApiKey'
    credentials: {
      key: apimSubscriptionKey
    }
    metadata: {
      deploymentInPath: 'true'
      inferenceAPIVersion: '2024-10-21'
      models: '[{"name":"${gatewayModelName}","properties":{"model":{"name":"${gatewayModelName}","version":"","format":"OpenAI"}}}]'
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// RBAC: Deployer permissions
// ─────────────────────────────────────────────────────────────────────────────

// Cognitive Services User on AI Account
resource deployerCognitiveServicesUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, deployerPrincipalId, 'CognitiveServicesUser')
  scope: aiAccount
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// RBAC: Project Managed Identity permissions
// ─────────────────────────────────────────────────────────────────────────────

// Azure AI User on AI Account (required for agents)
resource projectAzureAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, project.id, 'AzureAIUser')
  scope: aiAccount
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}

// Cognitive Services OpenAI User (required for web search tool)
resource projectOpenAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, project.id, 'CognitiveServicesOpenAIUser')
  scope: aiAccount
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Outputs
// ─────────────────────────────────────────────────────────────────────────────
output accountName string = aiAccount.name
output projectName string = project.name
output projectEndpoint string = 'https://${aiAccountName}.services.ai.azure.com/api/projects/${projectName}'
output projectManagedIdentityId string = project.identity.principalId
output apimConnectionName string = apimConnection.name
output gatewayModelName string = gatewayModelName
output localChatModel string = chatModel.name
