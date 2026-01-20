// RBAC assignment for APIM to access Content Understanding
// Grants Cognitive Services User role to APIM managed identity

targetScope = 'resourceGroup'

param cuResourceId string
param apimPrincipalId string

// Extract resource name from full resource ID
var cuAccountName = last(split(cuResourceId, '/'))

// Reference the CU account
resource cuAccount 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: cuAccountName
}

// Grant APIM managed identity Cognitive Services User role on CU account
resource apimCuRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cuAccount.id, apimPrincipalId, 'CognitiveServicesUser')
  scope: cuAccount
  properties: {
    principalId: apimPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
  }
}
