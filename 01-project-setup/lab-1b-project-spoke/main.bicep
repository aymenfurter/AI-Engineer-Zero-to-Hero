targetScope = 'resourceGroup'

param location string = resourceGroup().location
param deployerPrincipalId string
param apimUrl string
param modelName string = 'gpt-4.1-mini'
@secure()
param apimSubscriptionKey string

var suffix = substring(uniqueString(resourceGroup().id), 0, 6)
var aiAccountName = 'foundry-spoke-${suffix}'
var projectName = 'project-${suffix}'

// Create AI Foundry Account (no model deployments - uses APIM gateway)
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
    description: 'Project team spoke connecting to central landing zone via APIM'
    displayName: 'Team Spoke Project'
  }
}

// APIM Connection with API Key auth and static model list
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
      models: '[{"name":"${modelName}","properties":{"model":{"name":"${modelName}","version":"","format":"OpenAI"}}}]'
    }
  }
}

// Grant deployer access to the project
resource deployerCognitiveServicesUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, deployerPrincipalId, 'CognitiveServicesUser')
  scope: aiAccount
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
  }
}

output accountName string = aiAccount.name
output accountEndpoint string = aiAccount.properties.endpoint
output projectName string = project.name
output projectEndpoint string = 'https://${aiAccountName}.services.ai.azure.com/api/projects/${projectName}'
output apimConnectionName string = apimConnection.name
