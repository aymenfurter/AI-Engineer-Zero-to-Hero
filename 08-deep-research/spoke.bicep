// Lab 8: Deep Research - Spoke Resources
// Deploys Azure AI Search for Foundry IQ knowledge bases
// o3-deep-research model is deployed in Landing Zone (Lab 1a) and accessed via APIM

targetScope = 'resourceGroup'

param location string = resourceGroup().location
param deployerPrincipalId string

var suffix = substring(uniqueString(resourceGroup().id), 0, 6)
var searchName = 'search-dr-${suffix}'

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

output searchEndpoint string = 'https://${search.name}.search.windows.net'
output searchName string = search.name
