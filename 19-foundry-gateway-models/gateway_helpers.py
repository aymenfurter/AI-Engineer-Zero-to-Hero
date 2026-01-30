"""Helper functions for AI Gateway governance lab."""

import os
import subprocess
import json
import random
import string
import uuid
import time
import re
from pathlib import Path

# Azure role IDs
COGNITIVE_SERVICES_USER_ROLE = "a97b65f3-24c7-4388-baec-2e87135dc908"


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


def mask_principal_id(principal_id: str) -> str:
    """Mask principal ID, keeping first 8 chars."""
    if not principal_id or len(principal_id) < 8:
        return principal_id
    return f"{principal_id[:8]}..."


def load_env(path: str) -> bool:
    """Load .env file into os.environ."""
    if Path(path).exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        return True
    return False


def az_rest(method: str, url: str, body: dict = None, silent: bool = False) -> dict | None:
    """Execute az rest command and return parsed JSON.
    
    Args:
        method: HTTP method (GET, PUT, POST, DELETE, PATCH)
        url: Full Azure REST API URL
        body: Optional request body dict
        silent: If True, suppress error output (useful for DELETE where 404 is expected)
    
    Returns:
        Parsed JSON response or None on error
    """
    import tempfile
    
    cmd = ["az", "rest", "--method", method, "--url", url, "-o", "json"]
    
    temp_file = None
    if body:
        # Use temp file for body to avoid shell quoting issues
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(body, temp_file)
        temp_file.close()
        cmd.extend(["--body", f"@{temp_file.name}"])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Clean up temp file
    if temp_file:
        import os
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
        # Log error unless silent mode
        if not silent:
            error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
            # Extract just the error message, not the full stack
            if error_msg:
                # Try to parse JSON error
                try:
                    err_json = json.loads(error_msg)
                    if "error" in err_json:
                        msg = err_json["error"].get("message", error_msg)
                        print(f"    ERROR [{method}]: {msg[:200]}")
                    else:
                        print(f"    ERROR [{method}]: {error_msg[:200]}")
                except:
                    # Not JSON, print first line
                    first_line = error_msg.split('\n')[0]
                    if "ERROR" in first_line or "error" in first_line.lower():
                        print(f"    {first_line[:200]}")
        return None


def get_subscription_id() -> str:
    """Get current Azure subscription ID."""
    result = subprocess.run(
        'az account show --query id -o tsv',
        shell=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def discover_spokes() -> list[dict]:
    """Discover all Foundry spokes from environment and config files."""
    spokes = []
    
    # Landing Zone (Lab 1A) - the hub itself
    ai_endpoint = os.environ.get('AI_ENDPOINT', '')
    if ai_endpoint:
        # Extract account name from endpoint: https://foundry-hub-xxx.cognitiveservices.azure.com/
        lz_account = ai_endpoint.split('//')[1].split('.')[0] if '//' in ai_endpoint else None
        if lz_account:
            spokes.append({
                "name": lz_account,
                "rg": "foundry-lz-parent",
                "lab": "Lab 1A (Landing Zone)"
            })
    
    # Lab 1B spoke
    if os.environ.get('SPOKE_ACCOUNT'):
        spokes.append({
            "name": os.environ['SPOKE_ACCOUNT'],
            "rg": "foundry-child-1",
            "lab": "Lab 1B"
        })
    
    # Lab 2A team spokes
    team_deployments = Path(__file__).parent.parent / '02-inference/team-deployments.json'
    if team_deployments.exists():
        with open(team_deployments) as f:
            teams = json.load(f)
            for team in teams:
                spokes.append({
                    "name": team["accountName"],
                    "rg": team["resourceGroup"],
                    "lab": f"Lab 2A ({team['displayName']})"
                })
    
    # Lab 18 spoke
    if os.environ.get('ACCOUNT_NAME'):
        spokes.append({
            "name": os.environ['ACCOUNT_NAME'],
            "rg": "foundry-gateway-lab",
            "lab": "Lab 18"
        })
    
    return spokes


def connect_spoke_to_gateway(
    spoke: dict,
    subscription: str,
    apim_name: str,
    apim_rg: str,
    apim_principal_id: str,
    api_version: str = "2024-05-01"
) -> list[dict]:
    """
    Connect a Foundry spoke to the AI Gateway.
    
    Returns list of connected projects.
    """
    account_name = spoke["name"]
    spoke_rg = spoke["rg"]
    lab = spoke["lab"]
    projects_api_version = "2025-04-01-preview"
    connected = []
    
    print(f"\nProcessing: {mask_resource_name(account_name)} ({lab})")
    
    # Check if account exists
    account = az_rest(
        "GET",
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{spoke_rg}"
        f"/providers/Microsoft.CognitiveServices/accounts/{account_name}?api-version=2023-05-01"
    )
    if not account:
        print(f"  SKIP - Account not found")
        return connected
    
    # 1. RBAC role assignment (silent - may already exist)
    print(f"  1. Setting up RBAC...")
    role_id = str(uuid.uuid4())
    az_rest(
        "PUT",
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{spoke_rg}"
        f"/providers/Microsoft.CognitiveServices/accounts/{account_name}"
        f"/providers/Microsoft.Authorization/roleAssignments/{role_id}?api-version=2022-04-01",
        {
            "properties": {
                "principalId": apim_principal_id,
                "principalType": "ServicePrincipal",
                "roleDefinitionId": f"/providers/Microsoft.Authorization/roleDefinitions/{COGNITIVE_SERVICES_USER_ROLE}"
            }
        },
        silent=True  # Role may already exist
    )
    time.sleep(2)  # Brief delay to avoid throttling
    
    # 2. Create APIM Backend with managed identity credentials
    print(f"  2. Creating APIM backend...")
    az_rest(
        "PUT",
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
        f"/providers/Microsoft.ApiManagement/service/{apim_name}/backends/{account_name}?api-version={api_version}",
        {
            "properties": {
                "title": account_name,
                "url": f"https://{account_name}.services.ai.azure.com/",
                "protocol": "http",
                "credentials": {
                    "managedIdentity": {
                        "resource": "https://ai.azure.com/"
                    }
                }
            }
        }
    )
    time.sleep(2)  # Brief delay to avoid throttling
    
    # 3. Create/Update APIM API (PUT is idempotent - creates or updates)
    print(f"  3. Creating APIM API...")
    api_url = (
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
        f"/providers/Microsoft.ApiManagement/service/{apim_name}/apis/{account_name}?api-version={api_version}"
    )
    # Note: Skipping delete to avoid Bad Gateway during APIM state transitions
    # PUT is idempotent and will update if exists
    
    api_result = az_rest(
        "PUT",
        api_url,
        {
            "properties": {
                "displayName": account_name,
                "path": account_name,
                "protocols": ["https"],
                "subscriptionRequired": True,
                "subscriptionKeyParameterNames": {
                    "header": "api-key",
                    "query": "subscription-key"
                }
            }
        }
    )
    if api_result is None:
        print(f"  SKIP - Failed to create API")
        return connected
    
    time.sleep(2)  # Brief wait for API to stabilize
    
    # 4. Create API operations
    print(f"  4. Creating API operations...")
    for op_id, method in [("get-default", "GET"), ("post-default", "POST"), ("put-default", "PUT"), ("delete-default", "DELETE"), ("patch-default", "PATCH")]:
        az_rest(
            "PUT",
            f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
            f"/providers/Microsoft.ApiManagement/service/{apim_name}/apis/{account_name}/operations/{op_id}?api-version={api_version}",
            {"properties": {"displayName": method, "urlTemplate": "*", "method": method}}
        )
    
    # 5. Create API policy with AI Gateway token limiting
    print(f"  5. Setting API policy...")
    policy_xml = _get_ai_gateway_policy(account_name)
    az_rest(
        "PUT",
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
        f"/providers/Microsoft.ApiManagement/service/{apim_name}/apis/{account_name}/policies/policy?api-version={api_version}",
        {"properties": {"format": "rawxml", "value": policy_xml}}
    )
    
    time.sleep(5)  # Longer delay before project discovery to avoid throttling
    
    print(f"  6. Creating account-level resource link...")
    account_link_name = _random_string(16)
    account_resource_id = f"/subscriptions/{subscription}/resourceGroups/{spoke_rg}/providers/Microsoft.CognitiveServices/accounts/{account_name}"
    apim_service_id = f"/subscriptions/{subscription}/resourceGroups/{apim_rg}/providers/Microsoft.ApiManagement/service/{apim_name}"
    
    az_rest(
        "PUT",
        f"https://management.azure.com{account_resource_id}/providers/Microsoft.Resources/links/{account_link_name}?api-version=2016-09-01",
        {"properties": {"targetId": apim_service_id}},
        silent=True
    )
    
    # 7. Discover projects
    print(f"  7. Discovering projects...")
    projects_resp = az_rest(
        "GET",
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{spoke_rg}"
        f"/providers/Microsoft.CognitiveServices/accounts/{account_name}/projects?api-version={projects_api_version}"
    )
    
    projects = projects_resp.get("value", []) if projects_resp else []
    
    if not projects:
        print(f"     No projects found - account-level link already created")
        connected.append({"account": account_name, "project": None, "lab": lab, "rg": spoke_rg})
        return connected
    
    # 8. Connect each project
    print(f"     Found {len(projects)} project(s)")
    for proj in projects:
        full_name = proj["name"]
        proj_name = full_name.split("/")[-1] if "/" in full_name else full_name
        
        # Create APIM Product for this project
        # Product name must be alphanumeric/hyphens, max 80 chars
        # Use prefix for lookup (existing products may have random suffixes)
        product_prefix = f"{account_name}-{proj_name}"
        product_name = f"{product_prefix}-ai"[:80]  # Deterministic name for new products
        
        print(f"     Connecting: {mask_resource_name(proj_name)}")
        
        # Search for existing product by prefix (handles both old random-suffix and new deterministic names)
        list_cmd = ["az", "apim", "product", "list", "-g", apim_rg, "-n", apim_name, "-o", "json"]
        list_result = subprocess.run(list_cmd, capture_output=True, text=True)
        existing_product = None
        
        if list_result.returncode == 0:
            try:
                all_products = json.loads(list_result.stdout)
                for p in all_products:
                    if p["name"].startswith(product_prefix):
                        existing_product = p["name"]
                        break
            except json.JSONDecodeError:
                pass
        
        if existing_product:
            # Product already exists - use it
            print(f"       Product exists: {mask_resource_name(existing_product)}")
            product_result = {"name": existing_product}
            product_name = existing_product  # Use existing name for resource link
        else:
            # Product doesn't exist - create it with retry
            product_cmd = [
                "az", "apim", "product", "create",
                "-g", apim_rg,
                "-n", apim_name,
                "--product-id", product_name,
                "--product-name", f"{account_name} / {proj_name}",
                "--description", f"AI Gateway product for project {proj_name}",
                "--subscription-required", "true",
                "--approval-required", "false",
                "--state", "published",
                "-o", "json"
            ]
            
            product_result = None
            for attempt in range(5):
                result = subprocess.run(product_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    try:
                        product_result = json.loads(result.stdout)
                    except json.JSONDecodeError:
                        product_result = {}
                    break
                delay = 15 + (attempt * 15)  # 15, 30, 45, 60, 75 seconds (longer for throttle)
                if attempt < 4:
                    print(f"       Retry {attempt + 1}/5 in {delay}s...")
                    time.sleep(delay)
                else:
                    err_msg = result.stderr[:150] if result.stderr else "Unknown error"
                    print(f"       ERROR: {err_msg}")
        
        if product_result is None:
            print(f"       SKIP - Failed to create product")
            continue
        
        # Small delay for product to be fully provisioned
        time.sleep(1)
        
        # Set product policy (empty base - limits can be added later)
        product_policy = '''<policies>
    <inbound>
        <base />
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
    </outbound>
    <on-error>
        <base />
    </on-error>
</policies>'''
        az_rest(
            "PUT",
            f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
            f"/providers/Microsoft.ApiManagement/service/{apim_name}/products/{product_name}/policies/policy?api-version={api_version}",
            {"properties": {"format": "rawxml", "value": product_policy}},
            silent=True
        )
        
        # Add API to product
        az_rest(
            "PUT",
            f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
            f"/providers/Microsoft.ApiManagement/service/{apim_name}/products/{product_name}/apis/{account_name}?api-version={api_version}",
            {},
            silent=True
        )
        
        # Create APIM subscription for the product (critical for traffic routing!)
        # The portal creates this automatically - without it, traffic won't flow through APIM
        az_rest(
            "PUT",
            f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
            f"/providers/Microsoft.ApiManagement/service/{apim_name}/subscriptions/{product_name}?api-version={api_version}",
            {
                "properties": {
                    "displayName": product_name,
                    "scope": f"/subscriptions/{subscription}/resourceGroups/{apim_rg}/providers/Microsoft.ApiManagement/service/{apim_name}/products/{product_name}",
                    "state": "active"
                }
            },
            silent=True
        )
        
        # Create Resource Link: Project -> APIM Product
        link_name = _random_string(16)
        project_resource_id = f"/subscriptions/{subscription}/resourceGroups/{spoke_rg}/providers/Microsoft.CognitiveServices/accounts/{account_name}/projects/{proj_name}"
        product_resource_id = f"/subscriptions/{subscription}/resourceGroups/{apim_rg}/providers/Microsoft.ApiManagement/service/{apim_name}/products/{product_name}"
        
        az_rest(
            "PUT",
            f"https://management.azure.com{project_resource_id}/providers/Microsoft.Resources/links/{link_name}?api-version=2016-09-01",
            {"properties": {"targetId": product_resource_id}},
            silent=True
        )
        
        print(f"       OK - Product: {mask_resource_name(product_name)}")
        connected.append({
            "account": account_name,
            "project": proj_name,
            "product": product_name,
            "lab": lab,
            "rg": spoke_rg
        })
    
    # Add delay after processing spoke to avoid APIM throttling between spokes
    if connected:
        print(f"  Waiting 10s for APIM to stabilize...")
        time.sleep(10)
    
    return connected


def get_portal_url(subscription: str, rg: str, account_name: str, project_name: str) -> str:
    """Generate the AI Gateway portal URL using Foundry's nextgen format."""
    import base64
    sub_bytes = uuid.UUID(subscription).bytes
    encoded_sub = base64.urlsafe_b64encode(sub_bytes).decode('utf-8').rstrip('=')
    return f"https://ai.azure.com/nextgen/r/{encoded_sub},{rg},,{account_name},{project_name}/Operate/manage/gateway"


def list_ai_gateway_products(subscription: str, apim_rg: str, apim_name: str, api_version: str = "2024-05-01") -> list[dict]:
    """List all AI Gateway products (those with -ai suffix)."""
    products = az_rest(
        "GET",
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
        f"/providers/Microsoft.ApiManagement/service/{apim_name}/products?api-version={api_version}"
    )
    
    if not products or "value" not in products:
        return []
    
    return [
        {
            "name": p["name"],
            "displayName": p["properties"].get("displayName", p["name"]),
            "state": p["properties"].get("state", "unknown")
        }
        for p in products["value"]
        if p["name"].endswith("-ai")
    ]


def set_token_limit(
    subscription: str,
    apim_rg: str,
    apim_name: str,
    product_name: str,
    deployment_name: str,
    tokens_per_minute: int,
    quota: int = None,
    quota_period: str = None,
    api_version: str = "2024-05-01"
) -> bool:
    """
    Set token limit for a deployment on an APIM product.
    
    This mimics what the portal does when you set limits via the UI.
    The limit is set as a variable in the product policy, which the API
    policy then reads via context.Variables.
    
    Args:
        subscription: Azure subscription ID
        apim_rg: APIM resource group
        apim_name: APIM service name
        product_name: APIM product name
        deployment_name: Model deployment name (e.g., "gpt-4o", "deepseek-r1")
        tokens_per_minute: TPM limit
        quota: Optional token quota
        quota_period: Optional quota period (Hourly|Daily|Weekly|Monthly|Yearly)
    
    Returns:
        True if successful
    """
    # Get existing product policy
    policy_url = (
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
        f"/providers/Microsoft.ApiManagement/service/{apim_name}/products/{product_name}"
        f"/policies/policy?api-version={api_version}"
    )
    
    existing = az_rest("GET", policy_url)
    
    # Build new policy with token limit variable
    variables = [f'<set-variable name="tokenlimit-{deployment_name}" value="{tokens_per_minute}" />']
    
    if quota and quota_period:
        variables.append(f'<set-variable name="tokenquota-{deployment_name}" value="{quota}|{quota_period}" />')
    
    variables_xml = "\n        ".join(variables)
    
    policy_xml = f'''<policies>
    <inbound>
        <base />
        {variables_xml}
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
    </outbound>
    <on-error>
        <base />
    </on-error>
</policies>'''
    
    result = az_rest(
        "PUT",
        policy_url,
        {"properties": {"format": "rawxml", "value": policy_xml}}
    )
    
    return result is not None


def get_product_token_limits(
    subscription: str,
    apim_rg: str,
    apim_name: str,
    product_name: str,
    api_version: str = "2024-05-01"
) -> dict:
    """
    Get token limits configured on a product.
    
    Returns dict of deployment_name -> {"tpm": int, "quota": int, "period": str}
    """
    import re
    
    policy_url = (
        f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{apim_rg}"
        f"/providers/Microsoft.ApiManagement/service/{apim_name}/products/{product_name}"
        f"/policies/policy?api-version={api_version}"
    )
    
    result = az_rest("GET", policy_url)
    if not result:
        return {}
    
    policy_xml = result.get("properties", {}).get("value", "")
    limits = {}
    
    # Parse tokenlimit-{deployment} variables
    tpm_pattern = r'name="tokenlimit-([^"]+)"\s+value="(\d+)"'
    for match in re.finditer(tpm_pattern, policy_xml):
        deployment = match.group(1)
        tpm = int(match.group(2))
        if deployment not in limits:
            limits[deployment] = {}
        limits[deployment]["tpm"] = tpm
    
    # Parse tokenquota-{deployment} variables
    quota_pattern = r'name="tokenquota-([^"]+)"\s+value="(\d+)\|(\w+)"'
    for match in re.finditer(quota_pattern, policy_xml):
        deployment = match.group(1)
        quota = int(match.group(2))
        period = match.group(3)
        if deployment not in limits:
            limits[deployment] = {}
        limits[deployment]["quota"] = quota
        limits[deployment]["period"] = period
    
    return limits


def _random_string(length: int) -> str:
    """Generate a random alphanumeric string."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def _get_ai_gateway_policy(backend_id: str) -> str:
    """Generate the AI Gateway policy XML that matches the portal pattern."""
    return f'''<policies>
    <inbound>
        <base />
        <set-backend-service id="apim-generated-policy" backend-id="{backend_id}" />
        <choose>
            <when condition="@(context.Variables.ContainsKey(&quot;tokenlimit-&quot;+(string)context.Request.Foundry.Deployment) || context.Variables.ContainsKey(&quot;tokenquota-&quot;+(string)context.Request.Foundry.Deployment))">
                <set-variable name="deploymentName" value="@((string)context.Request.Foundry.Deployment)" />
                <set-variable name="counterKey" value="@(&quot;product/&quot;+ context.Product?.Id + &quot;/deployment/&quot; + (string)context.Variables[&quot;deploymentName&quot;])" />
                <set-variable name="limitVariableName" value="@(&quot;tokenlimit-&quot;+(string)context.Variables[&quot;deploymentName&quot;])" />
                <set-variable name="quotaVariableName" value="@(&quot;tokenquota-&quot;+(string)context.Variables[&quot;deploymentName&quot;])" />
                <set-variable name="tokenLimitValue" value="@(context.Variables.ContainsKey((string)context.Variables[&quot;limitVariableName&quot;]) ? (string)context.Variables[(string)context.Variables[&quot;limitVariableName&quot;]] : null)" />
                <set-variable name="tokenQuotaValue" value="@(context.Variables.ContainsKey((string)context.Variables[&quot;quotaVariableName&quot;]) ? ((string)context.Variables[(string)context.Variables[&quot;quotaVariableName&quot;]]).Split('|')[0] : null)" />
                <set-variable name="tokenQuotaPeriod" value="@(context.Variables.ContainsKey((string)context.Variables[&quot;quotaVariableName&quot;]) ? (((string)context.Variables[(string)context.Variables[&quot;quotaVariableName&quot;]]).Split('|').Length > 1 ? ((string)context.Variables[(string)context.Variables[&quot;quotaVariableName&quot;]]).Split('|')[1] : null) : null)" />
                <choose>
                    <when condition="@(context.Variables.ContainsKey((string)context.Variables[&quot;limitVariableName&quot;]) &amp;&amp; context.Variables.ContainsKey((string)context.Variables[&quot;quotaVariableName&quot;]))">
                        <choose>
                            <when condition="@(((string)context.Variables[&quot;tokenQuotaPeriod&quot;]) == &quot;Hourly&quot;)">
                                <llm-token-limit counter-key="@((string)context.Variables[&quot;counterKey&quot;])" tokens-per-minute="@(int.Parse((context.Variables[&quot;tokenLimitValue&quot;] as string) ?? &quot;0&quot;))" token-quota="@(long.Parse((context.Variables[&quot;tokenQuotaValue&quot;] as string) ?? &quot;0&quot;))" token-quota-period="Hourly" estimate-prompt-tokens="false" />
                            </when>
                            <when condition="@(((string)context.Variables[&quot;tokenQuotaPeriod&quot;]) == &quot;Daily&quot;)">
                                <llm-token-limit counter-key="@((string)context.Variables[&quot;counterKey&quot;])" tokens-per-minute="@(int.Parse((context.Variables[&quot;tokenLimitValue&quot;] as string) ?? &quot;0&quot;))" token-quota="@(long.Parse((context.Variables[&quot;tokenQuotaValue&quot;] as string) ?? &quot;0&quot;))" token-quota-period="Daily" estimate-prompt-tokens="false" />
                            </when>
                            <when condition="@(((string)context.Variables[&quot;tokenQuotaPeriod&quot;]) == &quot;Weekly&quot;)">
                                <llm-token-limit counter-key="@((string)context.Variables[&quot;counterKey&quot;])" tokens-per-minute="@(int.Parse((context.Variables[&quot;tokenLimitValue&quot;] as string) ?? &quot;0&quot;))" token-quota="@(long.Parse((context.Variables[&quot;tokenQuotaValue&quot;] as string) ?? &quot;0&quot;))" token-quota-period="Weekly" estimate-prompt-tokens="false" />
                            </when>
                            <when condition="@(((string)context.Variables[&quot;tokenQuotaPeriod&quot;]) == &quot;Monthly&quot;)">
                                <llm-token-limit counter-key="@((string)context.Variables[&quot;counterKey&quot;])" tokens-per-minute="@(int.Parse((context.Variables[&quot;tokenLimitValue&quot;] as string) ?? &quot;0&quot;))" token-quota="@(long.Parse((context.Variables[&quot;tokenQuotaValue&quot;] as string) ?? &quot;0&quot;))" token-quota-period="Monthly" estimate-prompt-tokens="false" />
                            </when>
                            <otherwise>
                                <llm-token-limit counter-key="@((string)context.Variables[&quot;counterKey&quot;])" tokens-per-minute="@(int.Parse((context.Variables[&quot;tokenLimitValue&quot;] as string) ?? &quot;0&quot;))" token-quota="@(long.Parse((context.Variables[&quot;tokenQuotaValue&quot;] as string) ?? &quot;0&quot;))" token-quota-period="Yearly" estimate-prompt-tokens="false" />
                            </otherwise>
                        </choose>
                    </when>
                    <when condition="@(context.Variables.ContainsKey((string)context.Variables[&quot;limitVariableName&quot;]))">
                        <llm-token-limit counter-key="@((string)context.Variables[&quot;counterKey&quot;])" tokens-per-minute="@(int.Parse((context.Variables[&quot;tokenLimitValue&quot;] as string) ?? &quot;0&quot;))" estimate-prompt-tokens="false" />
                    </when>
                    <otherwise>
                        <choose>
                            <when condition="@(((string)context.Variables[&quot;tokenQuotaPeriod&quot;]) == &quot;Hourly&quot;)">
                                <llm-token-limit counter-key="@((string)context.Variables[&quot;counterKey&quot;])" token-quota="@(long.Parse((context.Variables[&quot;tokenQuotaValue&quot;] as string) ?? &quot;0&quot;))" token-quota-period="Hourly" estimate-prompt-tokens="false" />
                            </when>
                            <when condition="@(((string)context.Variables[&quot;tokenQuotaPeriod&quot;]) == &quot;Daily&quot;)">
                                <llm-token-limit counter-key="@((string)context.Variables[&quot;counterKey&quot;])" token-quota="@(long.Parse((context.Variables[&quot;tokenQuotaValue&quot;] as string) ?? &quot;0&quot;))" token-quota-period="Daily" estimate-prompt-tokens="false" />
                            </when>
                            <when condition="@(((string)context.Variables[&quot;tokenQuotaPeriod&quot;]) == &quot;Weekly&quot;)">
                                <llm-token-limit counter-key="@((string)context.Variables[&quot;counterKey&quot;])" token-quota="@(long.Parse((context.Variables[&quot;tokenQuotaValue&quot;] as string) ?? &quot;0&quot;))" token-quota-period="Weekly" estimate-prompt-tokens="false" />
                            </when>
                            <when condition="@(((string)context.Variables[&quot;tokenQuotaPeriod&quot;]) == &quot;Monthly&quot;)">
                                <llm-token-limit counter-key="@((string)context.Variables[&quot;counterKey&quot;])" token-quota="@(long.Parse((context.Variables[&quot;tokenQuotaValue&quot;] as string) ?? &quot;0&quot;))" token-quota-period="Monthly" estimate-prompt-tokens="false" />
                            </when>
                            <otherwise>
                                <llm-token-limit counter-key="@((string)context.Variables[&quot;counterKey&quot;])" token-quota="@(long.Parse((context.Variables[&quot;tokenQuotaValue&quot;] as string) ?? &quot;0&quot;))" token-quota-period="Yearly" estimate-prompt-tokens="false" />
                            </otherwise>
                        </choose>
                    </otherwise>
                </choose>
            </when>
            <otherwise />
        </choose>
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
    </outbound>
    <on-error>
        <base />
    </on-error>
</policies>'''
