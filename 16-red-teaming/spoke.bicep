targetScope = 'resourceGroup'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Principal ID of the deployer (for RBAC)')
param deployerPrincipalId string

@description('APIM gateway URL from Landing Zone')
param apimUrl string

@description('Model name available via APIM gateway')
param gatewayModelName string = 'gpt-4.1-mini'

@secure()
@description('APIM subscription key')
param apimSubscriptionKey string

var suffix = substring(uniqueString(resourceGroup().id), 0, 6)
var aiAccountName = 'redteam-spoke-${suffix}'
var projectName = 'redteam-project'
var storageAccountName = 'redteamstor${suffix}'

// Create AI Foundry Account
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

// Create Project under the Account
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: aiAccount
  name: projectName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    description: 'Red Team Lab - Safety evaluation and vulnerability scanning'
    displayName: 'Red Team Project'
  }
}

// Storage Account for evaluation results (required for red teaming)
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

// Blob service for evaluation result storage
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

// Container for red team results
resource redteamContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'redteam-results'
  properties: {
    publicAccess: 'None'
  }
}

// APIM Connection for model access (gateway access)
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

// Grant Project MI the Azure AI User role
resource projectAzureAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, project.id, 'AzureAIUser')
  scope: aiAccount
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b4b97379-85b4-463f-bd4a-6ee4bf5edb04')
  }
}

// Grant deployer Storage Blob Data Owner on storage account
resource deployerStorageBlobDataOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, deployerPrincipalId, 'StorageBlobDataOwner')
  scope: storageAccount
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b')
  }
}

// Grant Project MI Storage Blob Data Owner for evaluation results
resource projectStorageBlobDataOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, project.id, 'StorageBlobDataOwner')
  scope: storageAccount
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b')
  }
}

// Outputs for use in notebooks
output aiAccountName string = aiAccount.name
output aiAccountEndpoint string = aiAccount.properties.endpoint
output projectName string = project.name
output storageAccountName string = storageAccount.name
output storageAccountId string = storageAccount.id
output projectResourceId string = project.id
