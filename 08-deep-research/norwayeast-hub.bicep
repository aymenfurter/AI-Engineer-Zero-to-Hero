param location string = 'norwayeast'
param deployerPrincipalId string
param apimPrincipalId string = ''  // Optional: APIM managed identity for backend auth

var suffix = substring(uniqueString(resourceGroup().id), 0, 6)
var aiAccountName = 'foundry-hub-norwayeast-${suffix}'

// AI Services account in westus for o3-deep-research
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

// Deploy o3-deep-research model (only available in specific regions)
resource deepResearchModel 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiAccount
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

// Grant deploying user access to AI Services
resource deployerCognitiveServicesUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, deployerPrincipalId, 'CognitiveServicesUser')
  scope: aiAccount
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
  }
}

// Grant APIM managed identity access (if provided)
resource apimCognitiveServicesUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(apimPrincipalId)) {
  name: guid(aiAccount.id, apimPrincipalId, 'CognitiveServicesUser')
  scope: aiAccount
  properties: {
    principalId: apimPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
  }
}

output aiEndpoint string = aiAccount.properties.endpoint
output aiAccountName string = aiAccount.name
output modelName string = deepResearchModel.name
