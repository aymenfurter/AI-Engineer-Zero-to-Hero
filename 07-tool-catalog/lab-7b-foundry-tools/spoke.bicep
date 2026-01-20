@description('Location for all resources')
param location string = resourceGroup().location

@description('Unique suffix for resource names')
param uniqueSuffix string = uniqueString(resourceGroup().id)

@description('Name of the Foundry account to connect to')
param foundryAccountName string

@description('Name of the existing Foundry project')
param projectName string

@description('Name of the API Center for private tools catalog')
param apiCenterName string = 'tools-catalog-${uniqueSuffix}'

// ============================================================================
// API Center for Private Tools Catalog
// ============================================================================

resource apiCenter 'Microsoft.ApiCenter/services@2024-03-01' = {
  name: apiCenterName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
  tags: {
    purpose: 'foundry-tools-catalog'
    lab: '7b-foundry-tools'
  }
}

// ============================================================================
// Example: Register an MCP Server as an API in API Center
// ============================================================================

// This shows the structure for registering MCP servers in the catalog
// In practice, you would register your own MCP servers

resource exampleMcpApi 'Microsoft.ApiCenter/services/workspaces/apis@2024-03-01' = {
  name: '${apiCenter.name}/default/internal-crm-mcp'
  properties: {
    title: 'Internal CRM MCP Server'
    description: 'MCP server for accessing customer relationship data'
    kind: 'rest'
    lifecycleStage: 'production'
    license: {
      name: 'Internal Use Only'
    }
    externalDocumentation: [
      {
        title: 'MCP Server Documentation'
        url: 'https://docs.contoso.com/mcp/crm'
      }
    ]
    contacts: [
      {
        name: 'Platform Team'
        email: 'platform@contoso.com'
      }
    ]
    customProperties: {
      mcpServerUrl: 'https://crm-mcp.contoso.com/mcp'
      authenticationType: 'key-based'
      requiredScopes: 'crm.read crm.write'
    }
  }
}

// API Version for the MCP server
resource exampleMcpApiVersion 'Microsoft.ApiCenter/services/workspaces/apis/versions@2024-03-01' = {
  name: '${exampleMcpApi.name}/v1'
  properties: {
    title: 'v1.0'
    lifecycleStage: 'production'
  }
}

// ============================================================================
// Key Vault for storing MCP server credentials
// ============================================================================

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-mcp-${uniqueSuffix}'
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
  tags: {
    purpose: 'mcp-credentials'
    lab: '7b-foundry-tools'
  }
}

// Example: Store an API key for an MCP server
resource mcpApiKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'crm-mcp-api-key'
  properties: {
    value: 'placeholder-replace-with-actual-key'
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

// ============================================================================
// Outputs
// ============================================================================

output apiCenterName string = apiCenter.name
output apiCenterId string = apiCenter.id
output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri

output instructions string = '''
Private Tools Catalog Setup Complete!

Next Steps:
1. Assign 'Azure API Center Data Reader' role to developers
2. Register your MCP servers as APIs in API Center
3. Configure authentication in API Center > Governance > Authorization
4. Access your catalog in Foundry Portal > Build > Tools > Catalog

The catalog will appear with the name: ${apiCenterName}
'''
