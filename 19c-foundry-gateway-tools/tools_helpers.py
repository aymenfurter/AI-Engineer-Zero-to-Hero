"""
Tool Gateway Helpers

This module provides functions to manage MCP tools with the Built-In AI Gateway:
- List MCP tools in APIM (tools routed via AI Gateway)
- List tool connections in Foundry project
- Register tools via AI Gateway
- Compare direct vs AI Gateway tool routing

Uses Azure ARM APIs - no portal-specific APIs.
"""

import os
import json
import re
import subprocess
import secrets
import hashlib
from typing import Optional
from dataclasses import dataclass
from pathlib import Path


def mask_resource_name(name: str) -> str:
    """
    Mask unique suffixes in Azure resource names for privacy.
    
    Examples:
        foundry-hub-lagivk -> foundry-hub-******
        foundry-spoke-h6cmx3 -> foundry-spoke-******
        contoso-team-kmqsp7 -> contoso-team-******
        project-h6cmx3 -> project-******
    """
    if not name:
        return name
    
    # Pattern: word-word-uniqueid (e.g., foundry-hub-lagivk)
    pattern = r'^(.+-)([a-z0-9]{5,8})$'
    match = re.match(pattern, name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}******"
    
    return name


def mask_url(url: str) -> str:
    """Mask resource names within URLs."""
    if not url:
        return url
    
    # Mask account names in Azure AI URLs (e.g., foundry-spoke-h6cmx3.services.ai.azure.com)
    url = re.sub(
        r'(https?://[a-z]+-[a-z]+-)[a-z0-9]{5,8}(\.)',
        r'\1******\2',
        url,
        flags=re.IGNORECASE
    )
    
    # Mask APIM names (e.g., foundry-apim-lagivk.azure-api.net)
    url = re.sub(
        r'(https?://[a-z]+-[a-z]+-)[a-z0-9]{5,8}(\.azure-api\.net)',
        r'\1******\2',
        url,
        flags=re.IGNORECASE
    )
    
    return url


def mask_subscription(sub_id: str) -> str:
    """Mask subscription ID, keeping first 8 chars."""
    if not sub_id or len(sub_id) < 8:
        return sub_id
    return f"{sub_id[:8]}..."


@dataclass
class MCPTool:
    """An MCP tool registered in the system."""
    name: str
    display_name: str
    endpoint: str
    backend_url: str
    is_gateway_routed: bool
    connection_id: Optional[str] = None
    apim_api_name: Optional[str] = None
    metadata_type: str = "custom_MCP"


def load_env(path: str) -> bool:
    """Load .env file into os.environ."""
    if Path(path).exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value.strip('"').strip("'")
        return True
    return False


def az_rest(method: str, url: str, body: dict = None, silent: bool = False) -> dict | None:
    """Execute az rest command and return parsed JSON."""
    import tempfile
    
    cmd = ["az", "rest", "--method", method, "--url", url, "-o", "json"]
    
    temp_file = None
    if body:
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(body, temp_file)
        temp_file.close()
        cmd.extend(["--body", f"@{temp_file.name}"])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if temp_file:
        os.unlink(temp_file.name)
    
    if result.returncode == 0:
        output = result.stdout.strip().lstrip('\ufeff')
        if output:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return {}
        return {}
    else:
        if not silent:
            error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
            if error_msg:
                first_line = error_msg.split('\n')[0]
                print(f"    ERROR [{method}]: {first_line[:200]}")
        return None


def get_subscription_id() -> str:
    """Get current Azure subscription ID."""
    result = subprocess.run(
        'az account show --query id -o tsv',
        shell=True, capture_output=True, text=True
    )
    return result.stdout.strip()


# =============================================================================
# APIM MCP TOOLS (Tools routed via AI Gateway)
# =============================================================================

def list_apim_mcp_tools(subscription: str, apim_rg: str, apim_name: str) -> list[MCPTool]:
    """
    List MCP tools registered in APIM.
    
    MCP tools are identified by type='mcp' on APIM APIs.
    These tools have their traffic routed through the AI Gateway.
    
    Uses ARM API:
    GET https://management.azure.com/.../Microsoft.ApiManagement/service/{apim}/apis
    """
    url = (
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
        f"/providers/Microsoft.ApiManagement/service/{apim_name}/apis"
        f"?api-version=2024-06-01-preview&$filter=properties/type eq 'mcp'"
    )
    
    response = az_rest("GET", url)
    
    if not response or "error" in response:
        return []
    
    tools = []
    gateway_url = f"https://{apim_name}.azure-api.net"
    
    for api in response.get('value', []):
        props = api.get('properties', {})
        
        # Extract MCP endpoint from mcpProperties
        mcp_props = props.get('mcpProperties', {})
        mcp_endpoint = mcp_props.get('endpoints', {}).get('mcp', {}).get('uriTemplate', '/mcp')
        
        tools.append(MCPTool(
            name=api.get('name', ''),
            display_name=props.get('displayName', ''),
            endpoint=f"{gateway_url}/{props.get('path', '')}{mcp_endpoint}",
            backend_url=props.get('serviceUrl', ''),
            is_gateway_routed=True,
            apim_api_name=api.get('name', '')
        ))
    
    return tools


def get_apim_mcp_tool(
    subscription: str, 
    apim_rg: str, 
    apim_name: str, 
    api_name: str
) -> MCPTool | None:
    """Get details for a specific MCP tool in APIM."""
    url = (
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
        f"/providers/Microsoft.ApiManagement/service/{apim_name}/apis/{api_name}"
        f"?api-version=2024-06-01-preview"
    )
    
    response = az_rest("GET", url)
    
    if not response or "error" in response:
        return None
    
    props = response.get('properties', {})
    gateway_url = f"https://{apim_name}.azure-api.net"
    mcp_props = props.get('mcpProperties', {})
    mcp_endpoint = mcp_props.get('endpoints', {}).get('mcp', {}).get('uriTemplate', '/mcp')
    
    return MCPTool(
        name=response.get('name', ''),
        display_name=props.get('displayName', ''),
        endpoint=f"{gateway_url}/{props.get('path', '')}{mcp_endpoint}",
        backend_url=props.get('serviceUrl', ''),
        is_gateway_routed=True,
        apim_api_name=response.get('name', '')
    )


# =============================================================================
# FOUNDRY TOOL CONNECTIONS (Project-level tool catalog)
# =============================================================================

def list_tool_connections(
    subscription: str,
    rg: str,
    account_name: str,
    project_name: str
) -> list[MCPTool]:
    """
    List MCP tool connections in a Foundry project.
    
    Tool connections are identified by:
    - category: "RemoteTool"
    - metadata.type: "custom_MCP" or "catalog_MCP"
    
    Uses ARM API:
    GET https://management.azure.com/.../accounts/{account}/projects/{project}/connections
    """
    url = (
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{rg}"
        f"/providers/Microsoft.CognitiveServices/accounts/{account_name}"
        f"/projects/{project_name}/connections?api-version=2025-04-01-preview"
    )
    
    response = az_rest("GET", url)
    
    if not response or "error" in response:
        return []
    
    tools = []
    
    for conn in response.get('value', []):
        props = conn.get('properties', {})
        category = props.get('category', '')
        metadata_type = props.get('metadata', {}).get('type', '')
        
        # Only include MCP tools (RemoteTool with custom_MCP or catalog_MCP metadata)
        if category == 'RemoteTool' and metadata_type in ('custom_MCP', 'catalog_MCP'):
            target = props.get('target', '')
            
            # Determine if routed via AI Gateway (APIM URL pattern)
            is_gateway = 'azure-api.net' in target
            
            tools.append(MCPTool(
                name=conn.get('name', ''),
                display_name=conn.get('name', ''),
                endpoint=target,
                backend_url=target if not is_gateway else '',  # Direct URL for non-gateway
                is_gateway_routed=is_gateway,
                connection_id=conn.get('id', ''),
                metadata_type=metadata_type
            ))
    
    return tools


def get_tool_connection(
    subscription: str,
    rg: str,
    account_name: str,
    project_name: str,
    connection_name: str
) -> MCPTool | None:
    """Get details for a specific tool connection."""
    url = (
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{rg}"
        f"/providers/Microsoft.CognitiveServices/accounts/{account_name}"
        f"/projects/{project_name}/connections/{connection_name}?api-version=2025-04-01-preview"
    )
    
    response = az_rest("GET", url)
    
    if not response or "error" in response:
        return None
    
    props = response.get('properties', {})
    target = props.get('target', '')
    is_gateway = 'azure-api.net' in target
    
    return MCPTool(
        name=response.get('name', ''),
        display_name=response.get('name', ''),
        endpoint=target,
        backend_url=target if not is_gateway else '',
        is_gateway_routed=is_gateway,
        connection_id=response.get('id', ''),
        metadata_type=props.get('metadata', {}).get('type', 'custom_MCP')
    )


# =============================================================================
# REGISTER TOOLS WITH AI GATEWAY
# =============================================================================

def register_tool_in_apim(
    subscription: str,
    apim_rg: str,
    apim_name: str,
    project_name: str,
    tool_url: str,
    display_name: str = None
) -> dict:
    """
    Register an MCP tool in APIM for AI Gateway routing.
    
    This creates:
    1. An APIM backend pointing to the MCP server
    2. An APIM API with type='mcp' and MCP properties
    
    Uses ARM API:
    PUT https://management.azure.com/.../backends/{backend}
    PUT https://management.azure.com/.../apis/{api}
    """
    import hashlib
    
    # Generate deterministic names based on URL
    url_hash = hashlib.sha256(tool_url.encode()).hexdigest()[:16]
    
    # Create API name from URL (same pattern as portal)
    # tool-project-{project}-{sanitized-url}
    sanitized = tool_url.replace('https://', '').replace('http://', '')
    sanitized = ''.join(c if c.isalnum() or c == '-' else '-' for c in sanitized)
    sanitized = '-'.join(filter(None, sanitized.split('-')))[:50]
    api_name = f"tool-{project_name}-{sanitized}"
    
    # Create backend
    backend_name = f"backend-{url_hash}"
    backend_url = (
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
        f"/providers/Microsoft.ApiManagement/service/{apim_name}/backends/{backend_name}"
        f"?api-version=2024-05-01"
    )
    
    backend_result = az_rest("PUT", backend_url, {
        "properties": {
            "title": display_name or tool_url,
            "url": tool_url,
            "protocol": "http"
        }
    })
    
    if backend_result is None:
        return {"error": "Failed to create backend"}
    
    # Create MCP API
    api_url_full = (
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
        f"/providers/Microsoft.ApiManagement/service/{apim_name}/apis/{api_name}"
        f"?api-version=2024-06-01-preview"
    )
    
    api_result = az_rest("PUT", api_url_full, {
        "properties": {
            "displayName": api_name,
            "description": f"MCP tool: {tool_url}",
            "path": api_name,
            "protocols": ["https"],
            "subscriptionRequired": False,
            "serviceUrl": tool_url,
            "backendId": backend_name,
            "type": "mcp",
            "mcpProperties": {
                "endpoints": {
                    "mcp": {
                        "uriTemplate": "/mcp"
                    }
                }
            }
        }
    })
    
    if api_result is None:
        return {"error": "Failed to create API"}
    
    gateway_url = f"https://{apim_name}.azure-api.net"
    
    return {
        "success": True,
        "api_name": api_name,
        "backend_name": backend_name,
        "gateway_endpoint": f"{gateway_url}/{api_name}",
        "backend_url": tool_url
    }


def create_tool_connection(
    subscription: str,
    rg: str,
    account_name: str,
    project_name: str,
    connection_name: str,
    target_url: str,
    auth_type: str = "None",
    credentials: dict = None
) -> dict:
    """
    Create a tool connection in the Foundry project catalog.
    
    This is the connection that agents reference when using the tool.
    If target_url points to APIM, the tool is AI Gateway enabled.
    
    Uses ARM API:
    PUT https://management.azure.com/.../connections/{name}
    """
    url = (
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{rg}"
        f"/providers/Microsoft.CognitiveServices/accounts/{account_name}"
        f"/projects/{project_name}/connections/{connection_name}"
        f"?api-version=2025-04-01-preview"
    )
    
    body = {
        "properties": {
            "category": "RemoteTool",
            "authType": auth_type,
            "target": target_url,
            "metadata": {
                "type": "custom_MCP"
            }
        }
    }
    
    if credentials:
        body["properties"]["credentials"] = {"keys": credentials}
        body["properties"]["authType"] = "CustomKeys"
    
    result = az_rest("PUT", url, body)
    
    if result is None:
        return {"error": "Failed to create connection"}
    
    return {
        "success": True,
        "connection_name": connection_name,
        "connection_id": result.get('id', ''),
        "target_url": target_url,
        "is_gateway_routed": 'azure-api.net' in target_url
    }


def delete_tool_connection(
    subscription: str,
    rg: str,
    account_name: str,
    project_name: str,
    connection_name: str
) -> dict:
    """Delete a tool connection from the Foundry project catalog."""
    url = (
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{rg}"
        f"/providers/Microsoft.CognitiveServices/accounts/{account_name}"
        f"/projects/{project_name}/connections/{connection_name}"
        f"?api-version=2025-04-01-preview"
    )
    
    result = subprocess.run(
        f'az rest --method DELETE --url "{url}" 2>/dev/null',
        shell=True, capture_output=True, text=True
    )
    
    if result.returncode != 0:
        return {"error": result.stderr}
    
    return {"success": True, "deleted": connection_name}


# =============================================================================
# TOOL LIFECYCLE (Block/Unblock)
# =============================================================================

def is_tool_blocked(subscription: str, apim_rg: str, apim_name: str, api_name: str) -> bool:
    """
    Check if an MCP tool is blocked by examining its APIM policy.
    
    Blocked tools have a policy with 'return-response id="tool-disabled"'.
    """
    url = (
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
        f"/providers/Microsoft.ApiManagement/service/{apim_name}/apis/{api_name}"
        f"/policies/policy?api-version=2024-05-01"
    )
    
    result = subprocess.run(
        f'az rest --method GET --url "{url}" 2>/dev/null',
        shell=True, capture_output=True, text=True
    )
    
    if result.returncode != 0:
        return False
    
    return 'tool-disabled' in result.stdout


def block_tool(subscription: str, apim_rg: str, apim_name: str, api_name: str) -> dict:
    """
    Block an MCP tool by setting a return-response policy (403).
    
    Same pattern as blocking agents in AI Gateway.
    """
    url = (
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
        f"/providers/Microsoft.ApiManagement/service/{apim_name}/apis/{api_name}"
        f"/policies/policy?api-version=2024-05-01"
    )
    
    block_policy = """<policies>
    <inbound>
        <return-response id="tool-disabled">
            <set-status code="403" reason="Forbidden" />
            <set-body>{"error": "ToolBlocked", "message": "This tool has been blocked by an administrator."}</set-body>
        </return-response>
        <base />
    </inbound>
    <backend><base /></backend>
    <outbound><base /></outbound>
    <on-error><base /></on-error>
</policies>"""
    
    result = az_rest("PUT", url, {
        "properties": {
            "format": "xml",
            "value": block_policy
        }
    })
    
    if result is None:
        return {"error": "Failed to block tool"}
    
    return {"success": True, "status": "blocked", "api_name": api_name}


def unblock_tool(subscription: str, apim_rg: str, apim_name: str, api_name: str) -> dict:
    """
    Unblock an MCP tool by removing the blocking policy.
    """
    url = (
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
        f"/providers/Microsoft.ApiManagement/service/{apim_name}/apis/{api_name}"
        f"/policies/policy?api-version=2024-05-01"
    )
    
    result = az_rest("DELETE", url, silent=True)
    
    return {"success": True, "status": "active", "api_name": api_name}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_portal_tools_url(subscription: str, rg: str, account_name: str, project_name: str) -> str:
    """Generate the Foundry portal URL for tools management."""
    import base64
    import uuid
    
    sub_bytes = uuid.UUID(subscription).bytes
    encoded_sub = base64.urlsafe_b64encode(sub_bytes).decode('utf-8').rstrip('=')
    return f"https://ai.azure.com/nextgen/r/{encoded_sub},{rg},,{account_name},{project_name}/Build/tools"


def compare_tool_routing(tools: list[MCPTool]) -> dict:
    """
    Compare and categorize tools by their routing mode.
    
    Returns a dict with 'direct' and 'gateway' lists.
    """
    direct = [t for t in tools if not t.is_gateway_routed]
    gateway = [t for t in tools if t.is_gateway_routed]
    
    return {
        "direct": direct,
        "gateway": gateway,
        "total": len(tools),
        "direct_count": len(direct),
        "gateway_count": len(gateway)
    }
