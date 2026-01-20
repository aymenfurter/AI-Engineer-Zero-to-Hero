// Spoke deployment for Content Understanding Lab
// Demonstrates Azure AI Content Understanding capabilities:
// - Document analysis (invoices, reports, technical documents)
// - Video analysis (keyframes, transcripts, chapter segments)
// - Image analysis (descriptions, metadata extraction)
// - Audio analysis (transcription, speaker diarization)
//
// Content Understanding requires model deployments in the same resource for default model configuration
// This spoke deploys its own AI Services account with required model deployments

targetScope = 'resourceGroup'

param location string = resourceGroup().location
param deployerPrincipalId string

// Landing Zone parameters (from Lab 1a .env) - for APIM connection
param hubResourceGroup string = ''
param hubAccountName string = ''
param apimName string = ''
param apimSubscriptionKey string = ''

var suffix = substring(uniqueString(resourceGroup().id), 0, 6)
var aiAccountName = 'foundry-cu-${suffix}'
var projectName = 'content-understanding-${suffix}'

// Create AI Foundry Account with Content Understanding support
// Note: Content Understanding requires specific model deployments in the same account
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

// Deploy GPT-4.1 for Content Understanding (required for document/video analysis)
resource gpt41Deployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiAccount
  name: 'gpt-4-1'
  sku: {
    name: 'Standard'
    capacity: 50
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1'
      version: '2025-04-14'
    }
  }
}

// Deploy GPT-4.1-mini for Content Understanding (cost-effective option)
resource gpt41MiniDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiAccount
  name: 'gpt-4-1-mini'
  sku: {
    name: 'Standard'
    capacity: 50
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1-mini'
      version: '2025-04-14'
    }
  }
  dependsOn: [gpt41Deployment]
}

// Deploy text-embedding-3-large for Content Understanding (required for embeddings)
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiAccount
  name: 'text-embedding-3-large'
  sku: {
    name: 'Standard'
    capacity: 50
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-large'
      version: '1'
    }
  }
  dependsOn: [gpt41MiniDeployment]
}

// Create Project under the Account
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: aiAccount
  name: projectName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    description: 'Content Understanding project for document and video analysis'
    displayName: 'Content Understanding Lab'
  }
}

// Optional: APIM Connection for gateway access (if APIM parameters provided)
resource apimConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = if (!empty(apimName) && !empty(apimSubscriptionKey)) {
  parent: project
  name: 'landing-zone-apim'
  properties: {
    category: 'ApiManagement'
    target: 'https://${apimName}.azure-api.net/openai'
    authType: 'ApiKey'
    credentials: {
      key: apimSubscriptionKey
    }
    metadata: {
      deploymentInPath: 'true'
      inferenceAPIVersion: '2024-10-21'
      models: '[{"name":"gpt-4.1-mini","properties":{"model":{"name":"gpt-4.1-mini","version":"","format":"OpenAI"}}}]'
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

// Grant deployer Cognitive Services Contributor for Content Understanding operations
resource deployerCognitiveServicesContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, deployerPrincipalId, 'CognitiveServicesContributor')
  scope: aiAccount
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68')
  }
}

output accountName string = aiAccount.name
output accountEndpoint string = aiAccount.properties.endpoint
output projectName string = project.name
output projectEndpoint string = 'https://${aiAccountName}.services.ai.azure.com/api/projects/${projectName}'
output contentUnderstandingEndpoint string = 'https://${aiAccountName}.cognitiveservices.azure.com'
output gpt41Deployment string = gpt41Deployment.name
output gpt41MiniDeployment string = gpt41MiniDeployment.name
output embeddingDeployment string = embeddingDeployment.name
output apimConnectionName string = !empty(apimName) && !empty(apimSubscriptionKey) ? apimConnection.name : ''
