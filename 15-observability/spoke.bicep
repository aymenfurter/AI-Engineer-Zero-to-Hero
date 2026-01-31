// Lab 15b: Tracing Infrastructure
// Deploys Microsoft Foundry with Application Insights for comprehensive agent tracing
// 
// This lab demonstrates:
// - Creating an Application Insights resource
// - Linking it to a Foundry account for automatic trace collection
// - Setting up proper RBAC for trace access
//
// Reference: https://learn.microsoft.com/azure/ai-foundry/observability/how-to/trace-agent-setup

targetScope = 'resourceGroup'

@description('Location for the resources')
param location string = resourceGroup().location

@description('Principal ID of the deployer for RBAC')
param deployerPrincipalId string

@description('APIM URL for gateway access (from Lab 1a)')
param apimUrl string

@description('Model name available through the gateway')
param gatewayModelName string = 'gpt-4.1-mini'

@secure()
@description('APIM subscription key for authentication')
param apimSubscriptionKey string

// Use subscription ID + RG ID for uniqueness across different users/subscriptions
var suffix = substring(uniqueString(subscription().subscriptionId, resourceGroup().id), 0, 6)
var aiAccountName = 'tracing-spoke-${suffix}'
var projectName = 'tracing-project'
var logAnalyticsName = 'tracing-logs-${suffix}'
var appInsightsName = 'tracing-insights-${suffix}'

// =============================================================================
// Log Analytics Workspace (required by Application Insights)
// =============================================================================
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 90
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// =============================================================================
// Application Insights (trace storage and visualization)
// =============================================================================
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// =============================================================================
// Microsoft Foundry Account (AIServices kind)
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

// =============================================================================
// Foundry Project
// =============================================================================
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: aiAccount
  name: projectName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    description: 'Tracing Lab - Demonstrates agent observability with Application Insights'
    displayName: 'Tracing Lab Project'
  }
}

// =============================================================================
// Application Insights Connection to Foundry
// This enables automatic trace collection from Foundry-hosted agents
// Reference: https://learn.microsoft.com/azure/ai-foundry/observability/how-to/trace-agent-setup
// =============================================================================
resource appInsightsConnection 'Microsoft.CognitiveServices/accounts/connections@2025-04-01-preview' = {
  name: 'appinsights-connection'
  parent: aiAccount
  properties: {
    category: 'AppInsights'
    target: appInsights.id
    isSharedToAll: true
    authType: 'ApiKey'
    credentials: {
      key: appInsights.properties.ConnectionString
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: appInsights.id
    }
  }
}

// =============================================================================
// APIM Connection for agent invocation (gateway access)
// =============================================================================
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

// =============================================================================
// RBAC Assignments
// =============================================================================

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

// Grant deployer Azure AI User role for Agent Service operations
resource deployerAzureAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, deployerPrincipalId, 'AzureAIUser')
  scope: aiAccount
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}

// Grant Project MI the Azure AI User role (required for agents)
resource projectAzureAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, project.id, 'AzureAIUser')
  scope: aiAccount
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}

// Grant Project MI Cognitive Services OpenAI User (required for model access)
resource projectOpenAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, project.id, 'CognitiveServicesOpenAIUser')
  scope: aiAccount
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  }
}

// Grant deployer Log Analytics Reader for trace queries
resource deployerLogAnalyticsReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(logAnalytics.id, deployerPrincipalId, 'LogAnalyticsReader')
  scope: logAnalytics
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '73c42c96-874c-492b-b04d-ab87d138a893')
  }
}

// Grant deployer Application Insights Component Contributor for dashboards
resource deployerAppInsightsContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appInsights.id, deployerPrincipalId, 'AppInsightsContributor')
  scope: appInsights
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ae349356-3a1b-4a5e-921d-050484c6347e')
  }
}

// =============================================================================
// Outputs
// =============================================================================
output accountName string = aiAccount.name
output accountEndpoint string = aiAccount.properties.endpoint
output projectName string = project.name
output projectEndpoint string = 'https://${aiAccountName}.services.ai.azure.com/api/projects/${projectName}'
output apimConnectionName string = apimConnection.name
output projectManagedIdentityId string = project.identity.principalId

// Tracing-specific outputs
output appInsightsName string = appInsights.name
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
output logAnalyticsName string = logAnalytics.name
output logAnalyticsWorkspaceId string = logAnalytics.properties.customerId
