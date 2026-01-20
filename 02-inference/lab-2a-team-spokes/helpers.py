"""Lab 2A Helper Functions - Team Spoke Deployment"""
import subprocess, json, uuid, os, re
from pathlib import Path

def get_lz_account(rg="foundry-lz-parent"):
    """Get Landing Zone account name"""
    result = subprocess.run(
        f'az cognitiveservices account list -g {rg} --query "[0].name" -o tsv',
        shell=True, capture_output=True, text=True
    )
    return result.stdout.strip()

def get_existing_deployments(rg, account):
    """Get list of deployed models"""
    result = subprocess.run(
        f'az cognitiveservices account deployment list -g {rg} -n {account} --query "[].name" -o json',
        shell=True, capture_output=True, text=True
    )
    return json.loads(result.stdout) if result.returncode == 0 else []

def deploy_model(rg, account, model):
    """Deploy a single model to the account"""
    result = subprocess.run(
        f'az cognitiveservices account deployment create -g {rg} -n {account} '
        f'--deployment-name {model["name"]} --model-name {model["name"]} '
        f'--model-version {model["version"]} --model-format {model["format"]} '
        f'--sku-capacity {model["capacity"]} --sku-name {model["sku"]} -o none',
        shell=True, capture_output=True, text=True
    )
    return result.returncode == 0, result.stderr[-200:] if result.stderr else ""

def load_env(env_file='/workspaces/getting-started-with-foundry/.env'):
    """Load environment variables from .env file"""
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    return os.environ.get('APIM_URL'), os.environ.get('APIM_KEY')

def load_spoke_config(path='/workspaces/getting-started-with-foundry/02-inference/spoke-config.json'):
    """Load spoke configuration"""
    with open(path) as f:
        return json.load(f)

def get_principal_id():
    """Get current user's principal ID"""
    result = subprocess.run('az ad signed-in-user show --query id -o tsv', 
                          shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def deploy_spoke(spoke, principal_id, apim_url, apim_key, location="eastus2"):
    """Deploy a single team spoke"""
    rg = spoke['resourceGroup']
    subprocess.run(f'az group create -n {rg} -l {location} -o none', shell=True)
    
    conn_name = f"apim-{uuid.uuid4().hex[:8]}"
    projects = [{
        **p,
        "modelsJson": json.dumps([{"name": m, "properties": {"model": {"name": m, "version": "", "format": "OpenAI"}}} 
                                  for m in p['allowedModels']])
    } for p in spoke['projects']]
    
    params = {
        "teamName": {"value": spoke['name']},
        "deployerPrincipalId": {"value": principal_id},
        "apimUrl": {"value": apim_url},
        "apimSubscriptionKey": {"value": apim_key},
        "connectionName": {"value": conn_name},
        "projectsJson": {"value": json.dumps(projects)}
    }
    
    pf = f"/tmp/deploy-{spoke['name']}.json"
    json.dump(params, open(pf, 'w'))
    
    result = subprocess.run(
        f'az deployment group create -g {rg} --template-file main.bicep --parameters @{pf} --query properties.outputs -o json',
        shell=True, capture_output=True, text=True
    )
    os.remove(pf)
    
    if result.returncode == 0:
        out = json.loads(result.stdout)
        return {
            'name': spoke['name'], 
            'displayName': spoke['displayName'], 
            'resourceGroup': rg,
            'accountName': out['accountName']['value'],
            'accountEndpoint': out['accountEndpoint']['value'],
            'connectionName': out['connectionName']['value'],
            'projectNames': out['projectNames']['value'],
            'projectEndpoints': out['projectEndpoints']['value']
        }
    return None

def save_deployments(deployed_teams, outputs_file='/workspaces/getting-started-with-foundry/02-inference/team-deployments.json',
                     env_file='/workspaces/getting-started-with-foundry/.env'):
    """Save deployment outputs to JSON and .env"""
    Path(outputs_file).write_text(json.dumps(deployed_teams, indent=2))
    
    with open(env_file, 'a') as f:
        f.write(f"\n# Team Spoke Deployments ({len(deployed_teams)} teams)\n")
        for team in deployed_teams:
            prefix = team['name'].upper().replace('-', '_')
            f.write(f"{prefix}_ACCOUNT={team['accountName']}\n")
            f.write(f"{prefix}_ENDPOINT={team['accountEndpoint']}\n")
            for i, proj in enumerate(team['projectNames']):
                f.write(f"{prefix}_PROJECT_{i+1}={proj}\n")

def make_agent_name(team_name, proj_name, model_name):
    """Generate valid agent name (alphanumeric only)"""
    return re.sub(r'[^a-zA-Z0-9]', '', f"test{team_name[:6]}{proj_name[:6]}{model_name[:6]}")

# Model definitions with correct formats per provider
REQUIRED_MODELS = [
    {"name": "gpt-4.1-mini", "version": "2025-04-14", "format": "OpenAI", "sku": "GlobalStandard", "capacity": 150},
    {"name": "gpt-4.1", "version": "2025-04-14", "format": "OpenAI", "sku": "Standard", "capacity": 150},
    {"name": "gpt-4.1-nano", "version": "2025-04-14", "format": "OpenAI", "sku": "GlobalStandard", "capacity": 150},
    {"name": "gpt-4o", "version": "2024-11-20", "format": "OpenAI", "sku": "Standard", "capacity": 30},
    {"name": "gpt-4o-mini", "version": "2024-07-18", "format": "OpenAI", "sku": "Standard", "capacity": 150},
    {"name": "grok-3", "version": "1", "format": "xAI", "sku": "GlobalStandard", "capacity": 200},
    {"name": "DeepSeek-R1", "version": "1", "format": "DeepSeek", "sku": "GlobalStandard", "capacity": 200},
    {"name": "model-router", "version": "2025-05-19", "format": "OpenAI", "sku": "GlobalStandard", "capacity": 30},
]
