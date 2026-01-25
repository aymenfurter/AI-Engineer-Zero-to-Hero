targetScope = 'resourceGroup'

param location string = resourceGroup().location
param deployerPrincipalId string

var suffix = substring(uniqueString(resourceGroup().id), 0, 6)
var aiAccountName = 'foundry-hub-${suffix}'
var storageName = 'foundryhub${suffix}'
var apimName = 'foundry-apim-${suffix}'
var norwayeastHubName = 'foundry-hub-norwayeast-${suffix}'

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
}

// =============================================================================
// PRIMARY HUB (eastus2) - gpt-4.1-mini, text-embedding-3-large
// =============================================================================

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

resource model 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiAccount
  name: 'gpt-4.1-mini'
  sku: { name: 'GlobalStandard', capacity: 30 }
  properties: {
    model: { name: 'gpt-4.1-mini', format: 'OpenAI', version: '2025-04-14' }
  }
}

resource embeddingModel 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiAccount
  name: 'text-embedding-3-large'
  sku: { name: 'Standard', capacity: 350 }
  properties: {
    model: { name: 'text-embedding-3-large', format: 'OpenAI', version: '1' }
  }
  dependsOn: [model]
}

// =============================================================================
// SECONDARY HUB (norwayeast) - o3-deep-research (region-specific model)
// =============================================================================

resource norwayeastHub 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: norwayeastHubName
  location: 'norwayeast'
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    allowProjectManagement: true
    customSubDomainName: norwayeastHubName
    publicNetworkAccess: 'Enabled'
  }
}

resource deepResearchModel 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: norwayeastHub
  name: 'o3-deep-research'
  sku: { name: 'GlobalStandard', capacity: 2700 }
  properties: {
    model: { 
      name: 'o3-deep-research'
      format: 'OpenAI'
      version: '2025-06-26'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

// StandardV2 tier required for BYO AI Gateway feature with Foundry Agents
resource apim 'Microsoft.ApiManagement/service@2024-06-01-preview' = {
  name: apimName
  location: location
  sku: { name: 'StandardV2', capacity: 1 }
  identity: { type: 'SystemAssigned' }
  properties: {
    publisherEmail: 'admin@contoso.com'
    publisherName: 'Contoso AI'
  }
}

// Grant APIM managed identity access to primary hub (eastus2)
resource apimCognitiveServicesUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, apim.id, 'CognitiveServicesUser')
  scope: aiAccount
  properties: {
    principalId: apim.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908') // Cognitive Services User
  }
}

// Grant APIM managed identity access to Norway East hub (for o3-deep-research)
resource apimCognitiveServicesUserNorwayeast 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(norwayeastHub.id, apim.id, 'CognitiveServicesUser')
  scope: norwayeastHub
  properties: {
    principalId: apim.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908') // Cognitive Services User
  }
}

// Grant deploying user access to primary hub
resource deployerCognitiveServicesUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, deployerPrincipalId, 'CognitiveServicesUser')
  scope: aiAccount
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908') // Cognitive Services User
  }
}

// Grant deploying user access to Norway East hub
resource deployerCognitiveServicesUserNorwayeast 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(norwayeastHub.id, deployerPrincipalId, 'CognitiveServicesUser')
  scope: norwayeastHub
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908') // Cognitive Services User
  }
}

resource backend 'Microsoft.ApiManagement/service/backends@2024-06-01-preview' = {
  parent: apim
  name: 'openai'
  properties: {
    url: '${aiAccount.properties.endpoint}openai'
    protocol: 'http'
  }
}

// Backend for Norway East hub (o3-deep-research)
resource norwayeastBackend 'Microsoft.ApiManagement/service/backends@2024-06-01-preview' = {
  parent: apim
  name: 'openai-norwayeast'
  properties: {
    url: '${norwayeastHub.properties.endpoint}openai'
    protocol: 'http'
    description: 'Norway East hub for o3-deep-research model'
  }
}

resource api 'Microsoft.ApiManagement/service/apis@2024-06-01-preview' = {
  parent: apim
  name: 'openai'
  properties: {
    displayName: 'OpenAI'
    path: 'openai'
    protocols: ['https']
    subscriptionRequired: true
    subscriptionKeyParameterNames: {
      header: 'api-key'
      query: 'api-key'
    }
    serviceUrl: '${aiAccount.properties.endpoint}openai'
  }
}

// Chat Completions operation
resource chatOp 'Microsoft.ApiManagement/service/apis/operations@2024-06-01-preview' = {
  parent: api
  name: 'chat'
  properties: {
    displayName: 'Chat Completions'
    method: 'POST'
    urlTemplate: '/deployments/{deployment-id}/chat/completions'
    templateParameters: [
      { name: 'deployment-id', required: true, type: 'string' }
    ]
  }
}

// Chat Completions for o3-deep-research (routes to Norway East backend)
resource chatNorwayeastOp 'Microsoft.ApiManagement/service/apis/operations@2024-06-01-preview' = {
  parent: api
  name: 'chat-norwayeast'
  properties: {
    displayName: 'Chat Completions (Norway East - Deep Research)'
    method: 'POST'
    urlTemplate: '/deployments/o3-deep-research/chat/completions'
  }
}

// Policy to route o3-deep-research chat to Norway East backend
resource chatNorwayeastPolicy 'Microsoft.ApiManagement/service/apis/operations/policies@2024-06-01-preview' = {
  parent: chatNorwayeastOp
  name: 'policy'
  properties: {
    format: 'xml'
    value: '<policies><inbound><base /><set-backend-service backend-id="openai-norwayeast" /><authentication-managed-identity resource="https://cognitiveservices.azure.com" output-token-variable-name="msi-access-token" ignore-error="false" /><set-header name="Authorization" exists-action="override"><value>@("Bearer " + (string)context.Variables["msi-access-token"])</value></set-header></inbound><backend><base /></backend><outbound><base /></outbound></policies>'
  }
}

// Responses API operation (for Agents)
resource responsesOp 'Microsoft.ApiManagement/service/apis/operations@2024-06-01-preview' = {
  parent: api
  name: 'responses'
  properties: {
    displayName: 'Responses'
    method: 'POST'
    urlTemplate: '/responses'
  }
}

// Embeddings operation (for vector search)
resource embeddingsOp 'Microsoft.ApiManagement/service/apis/operations@2024-06-01-preview' = {
  parent: api
  name: 'embeddings'
  properties: {
    displayName: 'Embeddings'
    method: 'POST'
    urlTemplate: '/deployments/{deployment-id}/embeddings'
    templateParameters: [
      { name: 'deployment-id', required: true, type: 'string' }
    ]
  }
}

// APIM Policy:
// - Adds default api-version (required for Azure AI Search knowledge base integration)
// - Uses managed identity to authenticate with Cognitive Services backend
// - Rate limits to 100 calls per 60 seconds
resource policy 'Microsoft.ApiManagement/service/apis/policies@2024-06-01-preview' = {
  parent: api
  name: 'policy'
  properties: {
    format: 'xml'
    value: '<policies><inbound><base /><set-query-parameter name="api-version" exists-action="skip"><value>2024-10-21</value></set-query-parameter><authentication-managed-identity resource="https://cognitiveservices.azure.com" output-token-variable-name="msi-access-token" ignore-error="false" /><set-header name="Authorization" exists-action="override"><value>@("Bearer " + (string)context.Variables["msi-access-token"])</value></set-header><rate-limit calls="100" renewal-period="60" /></inbound><backend><base /></backend><outbound><base /></outbound></policies>'
  }
}

// Create a subscription for API key access
resource apimSubscription 'Microsoft.ApiManagement/service/subscriptions@2024-06-01-preview' = {
  parent: apim
  name: 'foundry-gateway'
  properties: {
    displayName: 'Foundry Gateway Access'
    scope: '/apis/${api.name}'
    state: 'active'
  }
}

output aiEndpoint string = aiAccount.properties.endpoint
output apimUrl string = '${apim.properties.gatewayUrl}/openai'
output apimName string = apim.name
output apimSubscriptionName string = apimSubscription.name
output modelName string = model.name
output embeddingModelName string = embeddingModel.name
output deepResearchModelName string = deepResearchModel.name
output norwayeastHubEndpoint string = norwayeastHub.properties.endpoint
