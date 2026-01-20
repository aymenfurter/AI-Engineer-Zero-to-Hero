// ============================================================================
// Lab 6: Foundry IQ Spoke
// Uses APIM gateway from Landing Zone (no local model deployments)
// Provisions Azure AI Search for knowledge bases
// ============================================================================
targetScope = 'resourceGroup'

param location string = resourceGroup().location
param deployerPrincipalId string
param apimUrl string
param gatewayModelName string = 'gpt-4.1-mini'
@secure()
param apimSubscriptionKey string

var suffix = substring(uniqueString(resourceGroup().id), 0, 6)
var aiAccountName = 'iq-spoke-${suffix}'
var projectName = 'iq-project'
var searchName = 'iq-search-${suffix}'

// ─────────────────────────────────────────────────────────────────────────────
// Azure AI Search (required for Foundry IQ knowledge bases)
// ─────────────────────────────────────────────────────────────────────────────
resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchName
  location: location
  sku: { name: 'basic' }
  identity: { type: 'SystemAssigned' }
  properties: {
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    authOptions: {
      aadOrApiKey: { aadAuthFailureMode: 'http401WithBearerChallenge' }
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// AI Foundry Account (no local models - uses APIM gateway)
// ─────────────────────────────────────────────────────────────────────────────
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

// ─────────────────────────────────────────────────────────────────────────────
// Project
// ─────────────────────────────────────────────────────────────────────────────
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: aiAccount
  name: projectName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    description: 'Foundry IQ Lab - Knowledge retrieval via APIM gateway'
    displayName: 'Foundry IQ Project'
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// APIM Connection (gateway access to Landing Zone models)
// ─────────────────────────────────────────────────────────────────────────────
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

// ─────────────────────────────────────────────────────────────────────────────
// RBAC: Deployer permissions
// ─────────────────────────────────────────────────────────────────────────────

// Cognitive Services User on AI Account
resource deployerCognitiveServicesUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, deployerPrincipalId, 'CognitiveServicesUser')
  scope: aiAccount
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
  }
}

// Search Index Data Contributor on Search
resource deployerSearchContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, deployerPrincipalId, 'SearchIndexDataContributor')
  scope: search
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8ebe5a00-799e-43f5-93ac-243d3dce84a7')
  }
}

// Search Service Contributor on Search
resource deployerSearchServiceContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, deployerPrincipalId, 'SearchServiceContributor')
  scope: search
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// RBAC: Project Managed Identity permissions
// ─────────────────────────────────────────────────────────────────────────────

// Azure AI User on AI Account (required for agents)
resource projectAzureAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, project.id, 'AzureAIUser')
  scope: aiAccount
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}

// Search Index Data Reader on Search (required for knowledge base queries)
resource projectSearchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, project.id, 'SearchIndexDataReader')
  scope: search
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '1407120a-92aa-4202-b7e9-c0e197c71c8f')
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Outputs
// ─────────────────────────────────────────────────────────────────────────────
output accountName string = aiAccount.name
output projectName string = project.name
output projectEndpoint string = 'https://${aiAccountName}.services.ai.azure.com/api/projects/${projectName}'
output projectManagedIdentityId string = project.identity.principalId
output apimConnectionName string = apimConnection.name
output gatewayModelName string = gatewayModelName
output searchEndpoint string = 'https://${search.name}.search.windows.net'
output searchName string = search.name
