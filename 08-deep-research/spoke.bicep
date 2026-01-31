// Spoke deployment for Deep Research Lab
// Deploys:
// - Azure AI Search for Foundry IQ knowledge bases
// - Required RBAC permissions
// NOTE: o3-deep-research model is already deployed in Lab 1a Norway East hub

targetScope = 'resourceGroup'

param location string = resourceGroup().location
param deployerPrincipalId string

// Landing Zone parameters (from Lab 1a)
param hubResourceGroup string
param hubAccountName string
param apimName string

// Use subscription ID + RG ID for uniqueness across different users/subscriptions
var suffix = substring(uniqueString(subscription().subscriptionId, resourceGroup().id), 0, 6)
var searchName = 'search-dr-${suffix}'

// Derive Norway East hub name from hub account name pattern
// Lab 1a creates: foundry-hub-{suffix} and foundry-hub-norwayeast-{suffix}
var hubSuffix = substring(hubAccountName, length('foundry-hub-'))
var norwayeastHubName = 'foundry-hub-norwayeast-${hubSuffix}'

// Reference to existing Norway East hub (deployed in Lab 1a with o3-deep-research)
resource norwayeastHub 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: norwayeastHubName
  scope: resourceGroup(hubResourceGroup)
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
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
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

// NOTE: APIM backends and operations for o3-deep-research are already deployed in Lab 1a main.bicep
// No need to redeploy them here - this avoids conflicts and duplication

output searchEndpoint string = 'https://${search.name}.search.windows.net'
output searchName string = search.name
output norwayeastHubEndpoint string = norwayeastHub.properties.endpoint
output norwayeastHubName string = norwayeastHub.name
