// Add Responses API operations to APIM for Deep Research
// Demonstrates multi-backend APIM pattern for AI Landing Zone

param apimName string
param norwayeastEndpoint string

resource apim 'Microsoft.ApiManagement/service@2024-06-01-preview' existing = {
  name: apimName
}

resource api 'Microsoft.ApiManagement/service/apis@2024-06-01-preview' existing = {
  parent: apim
  name: 'openai'
}

// Backend for norwayeast hub (o3-deep-research)
resource norwayeastBackend 'Microsoft.ApiManagement/service/backends@2024-06-01-preview' = {
  parent: apim
  name: 'openai-norwayeast'
  properties: {
    url: '${norwayeastEndpoint}openai'
    protocol: 'http'
    description: 'Norway East hub for o3-deep-research model'
  }
}

// Chat completions for o3-deep-research (routes to Norway East)
resource chatNorwayeastOp 'Microsoft.ApiManagement/service/apis/operations@2024-06-01-preview' = {
  parent: api
  name: 'chat-norwayeast'
  properties: {
    displayName: 'Chat Completions (Norway East - Deep Research)'
    method: 'POST'
    urlTemplate: '/deployments/o3-deep-research/chat/completions'
  }
}

// Policy to route o3-deep-research chat to norwayeast backend
resource chatNorwayeastPolicy 'Microsoft.ApiManagement/service/apis/operations/policies@2024-06-01-preview' = {
  parent: chatNorwayeastOp
  name: 'policy'
  properties: {
    format: 'xml'
    value: '''
<policies>
  <inbound>
    <base />
    <set-backend-service backend-id="openai-norwayeast" />
    <authentication-managed-identity resource="https://cognitiveservices.azure.com" output-token-variable-name="msi-access-token" ignore-error="false" />
    <set-header name="Authorization" exists-action="override">
      <value>@("Bearer " + (string)context.Variables["msi-access-token"])</value>
    </set-header>
  </inbound>
  <backend><base /></backend>
  <outbound><base /></outbound>
</policies>'''
  }
}

resource responsesV1Op 'Microsoft.ApiManagement/service/apis/operations@2024-06-01-preview' = {
  parent: api
  name: 'responses-v1'
  properties: {
    displayName: 'Responses API v1 (Deep Research)'
    method: 'POST'
    urlTemplate: '/v1/responses'
  }
}

// Policy to route responses to norwayeast backend
resource responsesV1Policy 'Microsoft.ApiManagement/service/apis/operations/policies@2024-06-01-preview' = {
  parent: responsesV1Op
  name: 'policy'
  properties: {
    format: 'xml'
    value: '''
<policies>
  <inbound>
    <base />
    <set-backend-service backend-id="openai-norwayeast" />
  </inbound>
  <backend><base /></backend>
  <outbound><base /></outbound>
</policies>'''
  }
}

resource responsesGetOp 'Microsoft.ApiManagement/service/apis/operations@2024-06-01-preview' = {
  parent: api
  name: 'responses-get'
  properties: {
    displayName: 'Get Response (Deep Research)'
    method: 'GET'
    urlTemplate: '/v1/responses/{response-id}'
    templateParameters: [
      { name: 'response-id', required: true, type: 'string' }
    ]
  }
}

// Policy to route GET responses to norwayeast backend
resource responsesGetPolicy 'Microsoft.ApiManagement/service/apis/operations/policies@2024-06-01-preview' = {
  parent: responsesGetOp
  name: 'policy'
  properties: {
    format: 'xml'
    value: '''
<policies>
  <inbound>
    <base />
    <set-backend-service backend-id="openai-norwayeast" />
  </inbound>
  <backend><base /></backend>
  <outbound><base /></outbound>
</policies>'''
  }
}
