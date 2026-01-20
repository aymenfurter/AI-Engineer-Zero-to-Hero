// Landing Zone Integration for Content Understanding
// Adds Content Understanding API to the existing Landing Zone APIM
// This enables centralized governance for CU access across teams
//
// Architecture:
//   Teams → Landing Zone APIM → Content Understanding Service
//                ↓
//         Rate limiting, Auth, Logging, CORS

targetScope = 'resourceGroup'

param apimName string
param cuEndpoint string  // e.g., https://foundry-cu-xxx.cognitiveservices.azure.com
param cuResourceId string  // Full resource ID of the CU account for managed identity
param cuResourceGroup string  // Resource group where CU account exists

// Reference existing APIM from Landing Zone
resource apim 'Microsoft.ApiManagement/service@2023-09-01-preview' existing = {
  name: apimName
}

// Create Content Understanding API in APIM
resource cuApi 'Microsoft.ApiManagement/service/apis@2023-09-01-preview' = {
  parent: apim
  name: 'content-understanding-api'
  properties: {
    displayName: 'Content Understanding API'
    description: 'Governed access to Azure AI Content Understanding'
    path: 'cu'
    protocols: ['https']
    serviceUrl: '${cuEndpoint}/contentunderstanding'
    subscriptionRequired: true
    subscriptionKeyParameterNames: {
      header: 'api-key'
      query: 'api-key'
    }
  }
}

// Analyze operation - main CU endpoint
resource analyzeOperation 'Microsoft.ApiManagement/service/apis/operations@2023-09-01-preview' = {
  parent: cuApi
  name: 'analyze'
  properties: {
    displayName: 'Analyze Content'
    method: 'POST'
    urlTemplate: '/analyzers/{analyzer}:analyze'
    description: 'Submit content for analysis using specified analyzer'
    templateParameters: [
      {
        name: 'analyzer'
        type: 'string'
        required: true
        description: 'Analyzer ID (e.g., prebuilt-layout, prebuilt-videoSearch)'
      }
    ]
  }
}

// Get analysis result operation
resource getResultOperation 'Microsoft.ApiManagement/service/apis/operations@2023-09-01-preview' = {
  parent: cuApi
  name: 'get-result'
  properties: {
    displayName: 'Get Analysis Result'
    method: 'GET'
    urlTemplate: '/analyzers/{analyzer}/results/{resultId}'
    description: 'Get the result of an analysis operation'
    templateParameters: [
      {
        name: 'analyzer'
        type: 'string'
        required: true
      }
      {
        name: 'resultId'
        type: 'string'
        required: true
      }
    ]
  }
}

// Catch-all GET for any other paths (handles polling, etc.)
resource catchAllGet 'Microsoft.ApiManagement/service/apis/operations@2023-09-01-preview' = {
  parent: cuApi
  name: 'catch-all-get'
  properties: {
    displayName: 'Catch-All GET'
    method: 'GET'
    urlTemplate: '/*'
    description: 'Catch-all for GET requests'
  }
}

// Catch-all POST for any other paths
resource catchAllPost 'Microsoft.ApiManagement/service/apis/operations@2023-09-01-preview' = {
  parent: cuApi
  name: 'catch-all-post'
  properties: {
    displayName: 'Catch-All POST'
    method: 'POST'
    urlTemplate: '/*'
    description: 'Catch-all for POST requests'
  }
}

// List analyzers operation
resource listAnalyzersOperation 'Microsoft.ApiManagement/service/apis/operations@2023-09-01-preview' = {
  parent: cuApi
  name: 'list-analyzers'
  properties: {
    displayName: 'List Analyzers'
    method: 'GET'
    urlTemplate: '/analyzers'
    description: 'List available analyzers'
  }
}

// Get defaults operation
resource getDefaultsOperation 'Microsoft.ApiManagement/service/apis/operations@2023-09-01-preview' = {
  parent: cuApi
  name: 'get-defaults'
  properties: {
    displayName: 'Get Defaults'
    method: 'GET'
    urlTemplate: '/defaults'
    description: 'Get CU default model configuration'
  }
}

// Patch defaults operation (admin only)
resource patchDefaultsOperation 'Microsoft.ApiManagement/service/apis/operations@2023-09-01-preview' = {
  parent: cuApi
  name: 'patch-defaults'
  properties: {
    displayName: 'Update Defaults'
    method: 'PATCH'
    urlTemplate: '/defaults'
    description: 'Update CU default model configuration (admin)'
  }
}

// API-level policy with governance controls
resource cuApiPolicy 'Microsoft.ApiManagement/service/apis/policies@2023-09-01-preview' = {
  parent: cuApi
  name: 'policy'
  properties: {
    format: 'xml'
    value: '''<policies>
    <inbound>
        <base />
        
        <!-- Rate limiting: 30 calls per minute per subscription -->
        <rate-limit-by-key 
            calls="30" 
            renewal-period="60" 
            counter-key="@(context.Subscription.Id)" />
        
        <!-- Quota: 1000 calls per day per subscription -->
        <quota-by-key
            calls="1000"
            renewal-period="86400"
            counter-key="@(context.Subscription.Id)" />
        
        <!-- Add correlation ID for tracing -->
        <set-header name="X-Correlation-Id" exists-action="override">
            <value>@(context.RequestId.ToString())</value>
        </set-header>
        
        <!-- Add api-version if not present -->
        <set-query-parameter name="api-version" exists-action="skip">
            <value>2025-11-01</value>
        </set-query-parameter>
        
        <!-- Authenticate with managed identity to CU backend -->
        <authentication-managed-identity resource="https://cognitiveservices.azure.com" />
        
        <!-- CORS for browser-based access -->
        <cors>
            <allowed-origins>
                <origin>*</origin>
            </allowed-origins>
            <allowed-methods>
                <method>GET</method>
                <method>POST</method>
                <method>PATCH</method>
                <method>OPTIONS</method>
            </allowed-methods>
            <allowed-headers>
                <header>*</header>
            </allowed-headers>
        </cors>
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
        <!-- Tag responses as coming through the AI Gateway -->
        <set-header name="X-AI-Gateway" exists-action="override">
            <value>foundry-landing-zone-cu-1.0</value>
        </set-header>
    </outbound>
    <on-error>
        <base />
    </on-error>
</policies>'''
  }
}

// Grant APIM managed identity access to the CU service
// This enables the authentication-managed-identity policy to work
module apimCuRbac 'apim-cu-rbac.bicep' = {
  name: 'apim-cu-rbac'
  scope: resourceGroup(cuResourceGroup)
  params: {
    cuResourceId: cuResourceId
    apimPrincipalId: apim.identity.principalId
  }
}

// Update the foundry-gateway subscription to cover all APIs (not just openai)
// This allows the existing API key to work with both /openai and /cu endpoints
resource foundryGatewaySubscription 'Microsoft.ApiManagement/service/subscriptions@2023-09-01-preview' = {
  parent: apim
  name: 'foundry-gateway'
  properties: {
    displayName: 'Foundry Gateway Access'
    scope: '/apis'  // All APIs instead of just /apis/openai
    state: 'active'
  }
}

output apiId string = cuApi.name
output apiPath string = cuApi.properties.path
output gatewayUrl string = '${apim.properties.gatewayUrl}/${cuApi.properties.path}'
