"""
Agents Inventory Helpers

This module provides functions to list all agents using Azure ARM APIs:
- Foundry Agents: via Azure AI Projects SDK (data plane)
- Custom Agents: via APIM APIs where isAgent=true (ARM)

No portal-specific APIs are used.
"""

import os
import json
import re
import subprocess
from typing import Optional
from dataclasses import dataclass
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


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
class FoundryAgent:
    """A Foundry-hosted agent (created in AI Foundry portal)."""
    name: str
    id: str
    description: str
    project: str
    account: str
    resource_group: str
    endpoint: str
    platform: str = "Foundry"


@dataclass  
class CustomAgent:
    """A custom agent registered via APIM."""
    name: str
    agent_id: str
    backend_url: str
    path: str
    apim_api_name: str
    apim_name: str
    gateway_url: str
    platform: str = "AzureAiGateway"


def get_access_token() -> str:
    """Get Azure ARM access token."""
    result = subprocess.run(
        'az account get-access-token --query accessToken -o tsv',
        shell=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def arm_request(method: str, url: str, body: dict = None) -> dict:
    """Make an ARM REST API request."""
    import tempfile
    
    if body:
        # Write body to temp file to avoid shell escaping issues
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(body, f)
            temp_file = f.name
        
        cmd = f'az rest --method {method} --url "{url}" --body @{temp_file} -o json'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # Clean up temp file
        os.unlink(temp_file)
    else:
        cmd = f'az rest --method {method} --url "{url}" -o json'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        # Capture actual error message from stderr
        error_msg = result.stderr.strip() if result.stderr else "Unknown error"
        return {"error": error_msg}
    
    # Handle empty response (e.g., DELETE)
    if not result.stdout.strip():
        return {"success": True}
    
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        # Might be XML or plain text - return as raw
        return {"raw": result.stdout}


def arm_request_raw(method: str, url: str) -> str:
    """Make an ARM REST API request and return raw text response."""
    cmd = f'az rest --method {method} --url "{url}" 2>/dev/null'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        return ""
    
    return result.stdout


# =============================================================================
# FOUNDRY AGENTS (Data Plane API)
# =============================================================================

def list_foundry_agents(account_name: str, project_name: str) -> list[FoundryAgent]:
    """
    List Foundry-hosted agents for a project.
    
    Uses Azure AI Projects SDK data plane API:
    GET https://{account}.services.ai.azure.com/api/projects/{project}/agents
    """
    endpoint = f"https://{account_name}.services.ai.azure.com/api/projects/{project_name}"
    
    try:
        credential = DefaultAzureCredential()
        client = AIProjectClient(endpoint=endpoint, credential=credential)
        
        agents = []
        for agent in client.agents.list():
            agents.append(FoundryAgent(
                name=agent.name,
                id=agent.id,
                description=getattr(agent, 'description', '') or '',
                project=project_name,
                account=account_name,
                resource_group='',  # Would need ARM call to get this
                endpoint=f"https://{account_name}.services.ai.azure.com/api/projects/{project_name}"
            ))
        return agents
    except Exception as e:
        print(f"Error listing agents for {account_name}/{project_name}: {e}")
        return []


def list_all_projects(subscription: str) -> list[dict]:
    """
    List all AI Foundry projects in a subscription using Azure Resource Graph.
    
    Uses ARM API:
    POST https://management.azure.com/providers/Microsoft.ResourceGraph/resources
    """
    query = """
    resources
    | where type =~ 'microsoft.cognitiveservices/accounts/projects'
    | project 
        id,
        name,
        resourceGroup,
        accountName=split(id, '/')[8],
        projectName=split(id, '/')[10],
        location,
        subscriptionId
    """
    
    response = arm_request(
        "POST",
        "https://management.azure.com/providers/Microsoft.ResourceGraph/resources?api-version=2021-03-01",
        {"subscriptions": [subscription], "query": query}
    )
    
    if "error" in response:
        print(f"Error querying projects: {response['error']}")
        return []
    
    return response.get('data', [])


# =============================================================================
# CUSTOM AGENTS (APIM ARM API)
# =============================================================================

def list_custom_agents(subscription: str, apim_rg: str, apim_name: str) -> list[CustomAgent]:
    """
    List custom agents registered in APIM.
    
    Custom agents are identified by the `isAgent: true` flag on APIM APIs.
    
    Uses ARM API:
    GET https://management.azure.com/.../Microsoft.ApiManagement/service/{apim}/apis
    """
    url = f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}/providers/Microsoft.ApiManagement/service/{apim_name}/apis?api-version=2024-05-01"
    
    response = arm_request("GET", url)
    
    if "error" in response:
        print(f"Error listing APIM APIs: {response['error']}")
        return []
    
    agents = []
    for api in response.get('value', []):
        props = api.get('properties', {})
        
        # Only include APIs marked as agents
        if props.get('isAgent', False):
            agent_info = props.get('agent', {})
            agents.append(CustomAgent(
                name=agent_info.get('name', props.get('displayName', '')),
                agent_id=agent_info.get('id', ''),
                backend_url=props.get('serviceUrl', ''),
                path=props.get('path', ''),
                apim_api_name=api.get('name', ''),
                apim_name=apim_name,
                gateway_url=f"https://{apim_name}.azure-api.net"
            ))
    
    return agents


def list_connected_projects(subscription: str, apim_rg: str, apim_name: str) -> list[dict]:
    """
    List Foundry projects connected to APIM via products.
    
    Each APIM product represents a Foundry project connection.
    Product displayName format: "{account} / {project}"
    
    Uses ARM API:
    GET https://management.azure.com/.../Microsoft.ApiManagement/service/{apim}/products
    """
    url = f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}/providers/Microsoft.ApiManagement/service/{apim_name}/products?api-version=2024-05-01"
    
    response = arm_request("GET", url)
    
    if "error" in response:
        print(f"Error listing APIM products: {response['error']}")
        return []
    
    projects = []
    for product in response.get('value', []):
        props = product.get('properties', {})
        display_name = props.get('displayName', '')
        
        # Parse displayName format: "account / project" or "account-project-ai-xxx"
        if ' / ' in display_name:
            parts = display_name.split(' / ')
            if len(parts) == 2:
                projects.append({
                    'accountName': parts[0].strip(),
                    'projectName': parts[1].strip(),
                    'productName': product.get('name', '')
                })
    
    return projects


def get_apim_gateway_url(subscription: str, apim_rg: str, apim_name: str) -> str:
    """Get the APIM gateway URL."""
    url = f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}/providers/Microsoft.ApiManagement/service/{apim_name}?api-version=2024-05-01"
    response = arm_request("GET", url)
    
    if "error" in response:
        return f"https://{apim_name}.azure-api.net"
    
    return response.get('properties', {}).get('gatewayUrl', f"https://{apim_name}.azure-api.net")


# =============================================================================
# REGISTER CUSTOM AGENT (APIM ARM API)
# =============================================================================

def register_custom_agent(
    subscription: str,
    apim_rg: str,
    apim_name: str,
    agent_name: str,
    agent_id: str,
    backend_url: str,
    description: str = ""
) -> dict:
    """
    Register a custom agent in APIM.
    
    Creates an APIM API with isAgent=true flag (same as portal).
    
    Uses ARM API:
    PUT https://management.azure.com/.../apis/{api-name}
    """
    import secrets
    
    # Generate unique API name (same pattern as portal)
    suffix = secrets.token_hex(4)
    api_name = f"{agent_name}-{suffix}"
    
    # Create API with isAgent flag
    url = f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}/providers/Microsoft.ApiManagement/service/{apim_name}/apis/{api_name}?api-version=2024-05-01"
    
    body = {
        "properties": {
            "displayName": agent_name,
            "description": description,
            "path": agent_id,  # The agentId becomes the URL path
            "protocols": ["https"],
            "serviceUrl": backend_url,
            "subscriptionRequired": False,
            "isAgent": True,
            "agent": {
                "id": agent_id,
                "name": agent_name,
                "managementPortalUrl": ""
            }
        }
    }
    
    response = arm_request("PUT", url, body)
    
    if "error" in response:
        return {"error": response['error']}
    
    gateway_url = get_apim_gateway_url(subscription, apim_rg, apim_name)
    
    return {
        "success": True,
        "apiName": api_name,
        "agentName": agent_name,
        "agentId": agent_id,
        "agentEndpoint": f"{gateway_url}/{agent_id}",
        "backendUrl": backend_url
    }


def unregister_custom_agent(
    subscription: str,
    apim_rg: str,
    apim_name: str,
    api_name: str
) -> dict:
    """
    Unregister a custom agent by deleting its APIM API.
    
    Uses ARM API:
    DELETE https://management.azure.com/.../apis/{api-name}
    """
    url = f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}/providers/Microsoft.ApiManagement/service/{apim_name}/apis/{api_name}?api-version=2024-05-01"
    
    result = subprocess.run(
        f'az rest --method DELETE --url "{url}" 2>/dev/null',
        shell=True, capture_output=True, text=True
    )
    
    if result.returncode != 0:
        return {"error": result.stderr}
    
    return {"success": True, "deleted": api_name}


# =============================================================================
# AGENT LIFECYCLE (Block/Unblock via APIM Policy)
# =============================================================================

def is_agent_blocked(subscription: str, apim_rg: str, apim_name: str, api_name: str) -> bool:
    """
    Check if an agent is blocked by examining its APIM policy.
    
    Blocked agents have a policy with 'return-response id="agent-disabled"'.
    """
    url = f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}/providers/Microsoft.ApiManagement/service/{apim_name}/apis/{api_name}/policies/policy?api-version=2024-05-01"
    
    # Get raw response since policy may return XML
    policy_text = arm_request_raw("GET", url)
    
    if not policy_text:
        return False
    
    # Check for the blocking marker in the policy
    return 'id="agent-disabled"' in policy_text or 'agent-disabled' in policy_text


def block_custom_agent(
    subscription: str,
    apim_rg: str,
    apim_name: str,
    api_name: str
) -> dict:
    """
    Block a custom agent by setting a return-response policy (403).
    
    Uses the same format as the Azure AI Foundry portal.
    
    Uses ARM API:
    PUT https://management.azure.com/.../apis/{api-name}/policies/policy
    """
    url = f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}/providers/Microsoft.ApiManagement/service/{apim_name}/apis/{api_name}/policies/policy?api-version=2024-05-01"
    
    # Use same format as portal - 403 with id="agent-disabled"
    block_policy = """<policies>
    <inbound>
        <return-response id="agent-disabled">
            <set-status code="403" reason="Forbidden" />
            <set-body>{"error": "AgentBlocked", "message": "All incoming traffic to this agent has been blocked by an administrator."}</set-body>
        </return-response>
        <base />
    </inbound>
    <backend><base /></backend>
    <outbound><base /></outbound>
    <on-error><base /></on-error>
</policies>"""
    
    body = {
        "properties": {
            "format": "xml",
            "value": block_policy
        }
    }
    
    response = arm_request("PUT", url, body)
    
    if "error" in response:
        return {"error": response['error']}
    
    return {"success": True, "status": "blocked", "apiName": api_name}


def unblock_custom_agent(
    subscription: str,
    apim_rg: str,
    apim_name: str,
    api_name: str
) -> dict:
    """
    Unblock a custom agent by removing the blocking policy.
    
    Uses ARM API:
    DELETE https://management.azure.com/.../apis/{api-name}/policies/policy
    """
    url = f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}/providers/Microsoft.ApiManagement/service/{apim_name}/apis/{api_name}/policies/policy?api-version=2024-05-01"
    
    # Delete the API-level policy to unblock
    # This removes the return-response block and lets requests pass through
    response = arm_request("DELETE", url)
    
    if "error" in response and "NotFound" not in str(response.get('error', '')):
        return {"error": response['error']}
    
    return {"success": True, "status": "active", "apiName": api_name}


# =============================================================================
# CONFIGURATION HELPERS
# =============================================================================

def load_env_config(env_path: str = "/workspaces/getting-started-with-foundry/.env") -> dict:
    """Load configuration from .env file and Azure CLI."""
    config = {}
    
    # Load .env file
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('"').strip("'")
                    config[key] = value
    
    # Get subscription from Azure CLI
    result = subprocess.run(
        'az account show --query id -o tsv 2>/dev/null',
        shell=True, capture_output=True, text=True
    )
    subscription = result.stdout.strip()
    
    # Extract APIM name from APIM_URL (e.g., https://foundry-lz-apim-lagivk.azure-api.net/openai)
    apim_url = config.get("APIM_URL", "")
    apim_name = ""
    if "azure-api.net" in apim_url:
        # Extract: foundry-lz-apim-lagivk from https://foundry-lz-apim-lagivk.azure-api.net/...
        apim_name = apim_url.split("//")[1].split(".azure-api.net")[0]
    
    # Get APIM resource group via Azure CLI (using resource list since apim show requires RG)
    apim_rg = ""
    if apim_name and subscription:
        result = subprocess.run(
            f'az resource list --name {apim_name} --resource-type Microsoft.ApiManagement/service --query "[0].resourceGroup" -o tsv 2>/dev/null',
            shell=True, capture_output=True, text=True
        )
        apim_rg = result.stdout.strip()
    
    # Build gateway URL
    gateway_url = f"https://{apim_name}.azure-api.net" if apim_name else ""
    
    return {
        "subscription": subscription,
        "apim_name": apim_name,
        "apim_rg": apim_rg,
        "gateway_url": gateway_url,
        "api_key": config.get("APIM_KEY", "")
    }
