targetScope = 'resourceGroup'

// ============================================================================
// Team Spoke Deployment
// Deploys a Foundry AI Account with projects for a specific team,
// connected to the central Landing Zone via APIM gateway
// ============================================================================

param location string = resourceGroup().location
param deployerPrincipalId string

// Team configuration
param teamName string

// Project configurations (JSON array string)
// Each project should have: name, displayName, description, allowedModels, modelsJson
// modelsJson is pre-computed: '[{"name":"gpt-4.1","properties":{"model":{"name":"gpt-4.1",...}}}]'
param projectsJson string

// APIM connection details from Landing Zone
param apimUrl string
@secure()
param apimSubscriptionKey string

// Parse projects - expects array of objects with modelsJson pre-computed
var projects = json(projectsJson)

var suffix = substring(uniqueString(resourceGroup().id), 0, 6)
var aiAccountName = '${teamName}-${suffix}'

// Connection name - must be unique and passed from deployment script
// This avoids conflicts with soft-deleted resources or connections from previous deployments
param connectionName string

// ============================================================================
// AI Foundry Account for the Team
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

// Grant deployer access to the account
resource deployerCognitiveServicesUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, deployerPrincipalId, 'CognitiveServicesUser')
  scope: aiAccount
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
  }
}

// ============================================================================
// Projects under the Account
// Each project gets its own APIM connection with specific allowed models
// ============================================================================
resource projectResources 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = [for (proj, i) in projects: {
  parent: aiAccount
  name: proj.name
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    description: proj.description
    displayName: proj.displayName
  }
}]

// ============================================================================
// APIM Connections for each Project
// Each connection defines which models are accessible to that project
// ============================================================================
resource apimConnections 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = [for (proj, i) in projects: {
  parent: projectResources[i]
  name: connectionName
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
      // Models list - pre-computed JSON string passed from deployment script
      models: proj.modelsJson
    }
  }
}]

// ============================================================================
// Outputs
// ============================================================================
output accountName string = aiAccount.name
output accountEndpoint string = aiAccount.properties.endpoint
output connectionName string = connectionName
output projectNames array = [for (proj, i) in projects: projectResources[i].name]
output projectEndpoints array = [for (proj, i) in projects: 'https://${aiAccountName}.services.ai.azure.com/api/projects/${projectResources[i].name}']
