targetScope = 'resourceGroup'

param location string = resourceGroup().location
param deployerPrincipalId string

// Landing Zone parameters (from Lab 1a .env)
param hubResourceGroup string
param hubAccountName string
param apimName string = ''  // Optional - only needed if adding APIM operations

var suffix = substring(uniqueString(resourceGroup().id), 0, 6)
var searchName = 'search-dr-${suffix}'

// Get APIM principal ID for RBAC (if APIM name provided)
resource existingApim 'Microsoft.ApiManagement/service@2024-06-01-preview' existing = if (!empty(apimName)) {
  name: apimName
  scope: resourceGroup(hubResourceGroup)
}

// Deploy secondary hub in norwayeast for o3-deep-research
// This model requires specific regions - demonstrates multi-region Landing Zone pattern
module norwayeastHub 'norwayeast-hub.bicep' = {
  name: 'deploy-norwayeast-hub'
  params: {
    location: 'norwayeast'
    deployerPrincipalId: deployerPrincipalId
    apimPrincipalId: !empty(apimName) ? existingApim.identity.principalId : ''
  }
}

// Azure AI Search for Foundry IQ
resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchName
  location: location
  sku: { name: 'basic' }
  identity: { type: 'SystemAssigned' }
  properties: {
    hostingMode: 'default'
    partitionCount: 1
    replicaCount: 1
    semanticSearch: 'standard'
    publicNetworkAccess: 'enabled'
    authOptions: {
      aadOrApiKey: { aadAuthFailureMode: 'http401WithBearerChallenge' }
    }
  }
}

// Grant deployer Search Index Data Contributor
resource deployerSearchContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, deployerPrincipalId, 'SearchIndexDataContributor')
  scope: search
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8ebe5a00-799e-43f5-93ac-243d3dce84a7') // Search Index Data Contributor
  }
}

// Grant deployer Search Service Contributor  
resource deployerSearchServiceContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, deployerPrincipalId, 'SearchServiceContributor')
  scope: search
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7ca78c08-252a-4471-8644-bb5ff32d4ba0') // Search Service Contributor
  }
}

// Add Responses API operation to APIM for Deep Research with norwayeast backend
module apimResponsesApi 'apim-responses-api.bicep' = if (!empty(apimName)) {
  name: 'add-responses-api'
  scope: resourceGroup(hubResourceGroup)
  params: {
    apimName: apimName
    norwayeastEndpoint: norwayeastHub.outputs.aiEndpoint
  }
}

output searchEndpoint string = 'https://${search.name}.search.windows.net'
output searchName string = search.name
output deepResearchModel string = norwayeastHub.outputs.modelName
output norwayeastHubEndpoint string = norwayeastHub.outputs.aiEndpoint
output norwayeastHubName string = norwayeastHub.outputs.aiAccountName
