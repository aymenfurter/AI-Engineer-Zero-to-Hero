targetScope = 'resourceGroup'

param location string = resourceGroup().location
param deployerPrincipalId string
param apimUrl string
param gatewayModelName string = 'gpt-4.1-mini'
param localChatModel string = 'gpt-4.1-mini'
param embeddingModelName string = 'text-embedding-3-small'
@secure()
param apimSubscriptionKey string

var suffix = substring(uniqueString(resourceGroup().id), 0, 6)
var aiAccountName = 'memory-spoke-${suffix}'
var projectName = 'memory-project'

// Create AI Foundry Account with local models for Memory API
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

// Local chat model for Memory API internal processing
// Memory API needs direct model access for summarization and fact extraction
resource chatModel 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiAccount
  name: localChatModel
  sku: { name: 'GlobalStandard', capacity: 30 }
  properties: {
    model: { name: localChatModel, format: 'OpenAI', version: '2025-04-14' }
  }
}

// Local embedding model for Memory API semantic search
resource embeddingModel 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiAccount
  name: embeddingModelName
  sku: { name: 'Standard', capacity: 30 }
  properties: {
    model: { name: embeddingModelName, format: 'OpenAI', version: '1' }
  }
  dependsOn: [chatModel]
}

// Create Project under the Account
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: aiAccount
  name: projectName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    description: 'Memory Lab - Spoke with gateway for agents, local models for memory'
    displayName: 'Memory Lab Project'
  }
}

// APIM Connection for agent invocation (gateway access)
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

// Grant deployer Cognitive Services User on the account
resource deployerCognitiveServicesUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, deployerPrincipalId, 'CognitiveServicesUser')
  scope: aiAccount
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
  }
}

// Grant Project MI the Azure AI User role (required for Memory API)
resource projectAzureAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, project.id, 'AzureAIUser')
  scope: aiAccount
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}

// Grant Project MI Cognitive Services OpenAI User (required for Memory API)
resource projectOpenAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, project.id, 'CognitiveServicesOpenAIUser')
  scope: aiAccount
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  }
}

output accountName string = aiAccount.name
output accountEndpoint string = aiAccount.properties.endpoint
output projectName string = project.name
output projectEndpoint string = 'https://${aiAccountName}.services.ai.azure.com/api/projects/${projectName}'
output apimConnectionName string = apimConnection.name
output localChatModel string = chatModel.name
output embeddingModelName string = embeddingModel.name
output projectManagedIdentityId string = project.identity.principalId
