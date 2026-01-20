targetScope = 'resourceGroup'

// This Bicep module adds Model Router to an existing Landing Zone
// Run this AFTER lab-1a-landing-zone to add the model-router deployment

var suffix = substring(uniqueString(resourceGroup().id), 0, 6)
var aiAccountName = 'foundry-hub-${suffix}'
var apimName = 'foundry-apim-${suffix}'

// Reference the existing AI Account from lab-1a
resource aiAccount 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: aiAccountName
}

// Reference existing APIM from lab-1a
resource apim 'Microsoft.ApiManagement/service@2024-06-01-preview' existing = {
  name: apimName
}

// Reference existing OpenAI API from lab-1a
resource api 'Microsoft.ApiManagement/service/apis@2024-06-01-preview' existing = {
  parent: apim
  name: 'openai'
}

// Deploy Model Router - intelligent model selection
resource modelRouter 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiAccount
  name: 'model-router'
  sku: { name: 'GlobalStandard', capacity: 30 }
  properties: {
    model: { name: 'model-router', format: 'OpenAI', version: '2025-05-19' }
  }
}

// Add APIM operation for Model Router chat completions
// This enables the spoke projects to access model-router via APIM gateway
resource modelRouterOp 'Microsoft.ApiManagement/service/apis/operations@2024-06-01-preview' = {
  parent: api
  name: 'model-router-chat'
  properties: {
    displayName: 'Model Router Chat Completions'
    method: 'POST'
    urlTemplate: '/deployments/model-router/chat/completions'
  }
}

output aiAccountName string = aiAccount.name
output aiEndpoint string = aiAccount.properties.endpoint
output modelRouterName string = modelRouter.name
output apimName string = apim.name
