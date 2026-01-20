"""
Foundry IQ helpers for Lab 6
Handles knowledge base and knowledge source operations via Azure AI Search API
"""
import subprocess
import requests


def get_search_token() -> str:
    """Get access token for Azure AI Search."""
    result = subprocess.run(
        'az account get-access-token --resource https://search.azure.com --query accessToken -o tsv',
        shell=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def get_mgmt_token() -> str:
    """Get access token for Azure Management API."""
    result = subprocess.run(
        'az account get-access-token --resource https://management.azure.com --query accessToken -o tsv',
        shell=True, capture_output=True, text=True
    )
    return result.stdout.strip()


class FoundryIQClient:
    """Client for Foundry IQ (Knowledge Bases) operations."""
    
    API_VERSION = "2025-11-01-preview"
    
    def __init__(self, search_endpoint: str):
        self.search_endpoint = search_endpoint.rstrip('/')
    
    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {get_search_token()}',
            'Content-Type': 'application/json'
        }
    
    def _url(self, path: str) -> str:
        return f"{self.search_endpoint}/{path}?api-version={self.API_VERSION}"
    
    # ─────────────────────────────────────────────────────────────
    # Knowledge Sources
    # ─────────────────────────────────────────────────────────────
    
    def create_knowledge_source(self, name: str, kind: str, config: dict) -> dict:
        """
        Create a knowledge source.
        
        For web sources:
            kind="web", config={"webParameters": {"urls": [...]}}
        
        For search index sources:
            kind="searchIndex", config={"searchIndexParameters": {"searchIndexName": "...", "sourceDataFields": [...]}}
        """
        payload = {"name": name, "kind": kind, **config}
        
        resp = requests.put(
            self._url(f"knowledgesources/{name}"),
            headers=self._headers(),
            json=payload
        )
        if resp.status_code in [200, 201]:
            return resp.json()
        elif resp.status_code == 204:
            return {"status": "success", "name": name}  # 204 No Content = success
        else:
            return {"error": resp.text}
    
    def get_knowledge_source_status(self, name: str) -> dict:
        """Check indexing status of a knowledge source."""
        resp = requests.get(
            self._url(f"knowledgesources('{name}')/status"),
            headers=self._headers()
        )
        return resp.json() if resp.ok else {"error": resp.text}
    
    def delete_knowledge_source(self, name: str) -> bool:
        """Delete a knowledge source."""
        resp = requests.delete(
            self._url(f"knowledgesources/{name}"),
            headers=self._headers()
        )
        return resp.status_code in [200, 204]
    
    # ─────────────────────────────────────────────────────────────
    # Knowledge Bases
    # ─────────────────────────────────────────────────────────────
    
    def create_knowledge_base(self, name: str, sources: list, 
                               description: str = "", output_mode: str = None,
                               model_config: dict = None) -> dict:
        """
        Create a knowledge base that uses one or more knowledge sources.
        
        Args:
            name: Knowledge base name
            sources: List of knowledge source names
            description: Description of the knowledge base
            output_mode: Optional output mode (note: web sources don't support extractive mode)
            model_config: Optional LLM config for answer synthesis. Should include:
                - kind: "azureOpenAI"
                - azureOpenAIParameters: {resourceUri, deploymentId, apiKey, modelName}
        """
        payload = {
            "name": name,
            "description": description,
            "knowledgeSources": [{"name": s} for s in sources]
        }
        
        # Only include outputMode if explicitly provided
        if output_mode:
            payload["outputMode"] = output_mode
        
        # Only include models if provided
        if model_config:
            payload["models"] = [model_config]
        
        resp = requests.put(
            self._url(f"knowledgebases/{name}"),
            headers=self._headers(),
            json=payload
        )
        if resp.status_code in [200, 201]:
            return resp.json()
        elif resp.status_code == 204:
            return {"status": "success", "name": name}
        else:
            return {"error": resp.text}
    
    def query_knowledge_base(self, name: str, query: str, 
                              source_name: str = None, user_groups: list = None) -> dict:
        """Query a knowledge base directly (without agent).
        
        Uses 'intents' format with minimal reasoning effort (no model required).
        
        Args:
            name: Knowledge base name
            query: The search query
            source_name: Optional knowledge source name for filtering
            user_groups: Optional list of group IDs for document-level security filtering.
                        Documents are only returned if their group_ids field contains
                        at least one of these groups. This implements the security
                        trimming pattern - the filter must be applied at query time!
        """
        payload = {
            "intents": [{"search": query, "type": "semantic"}],
            "retrievalReasoningEffort": {"kind": "minimal"}
        }
        
        # Add security filter if user_groups provided
        if source_name and user_groups:
            groups_str = ", ".join(user_groups)
            payload["knowledgeSourceParams"] = [{
                "knowledgeSourceName": source_name,
                "kind": "searchIndex",
                "filterAddOn": f"group_ids/any(g:search.in(g, '{groups_str}'))"
            }]
        
        resp = requests.post(
            self._url(f"knowledgebases/{name}/retrieve"),
            headers=self._headers(),
            json=payload
        )
        return resp.json() if resp.ok else {"error": resp.text}
    
    def query_knowledge_base_with_reasoning(self, name: str, query: str, effort: str = "low") -> dict:
        """Query a knowledge base with LLM-based reasoning.
        
        Args:
            name: Knowledge base name
            query: The search query
            effort: Reasoning effort level - "minimal", "low", or "medium"
                   "low" and "medium" require a model to be configured
        """
        payload = {
            "intents": [{"search": query, "type": "semantic"}],
            "retrievalReasoningEffort": {"kind": effort}
        }
        
        resp = requests.post(
            self._url(f"knowledgebases/{name}/retrieve"),
            headers=self._headers(),
            json=payload
        )
        return resp.json() if resp.ok else {"error": resp.text}
    
    def delete_knowledge_base(self, name: str) -> bool:
        """Delete a knowledge base."""
        resp = requests.delete(
            self._url(f"knowledgebases/{name}"),
            headers=self._headers()
        )
        return resp.status_code in [200, 204]


def create_mcp_connection(subscription_id: str, resource_group: str, 
                          account_name: str, project_name: str,
                          connection_name: str, search_endpoint: str, 
                          kb_name: str) -> dict:
    """Create a RemoteTool (MCP) connection from Foundry project to knowledge base."""
    
    mcp_endpoint = f"{search_endpoint}/knowledgebases/{kb_name}/mcp?api-version=2025-11-01-preview"
    
    url = (f"https://management.azure.com/subscriptions/{subscription_id}"
           f"/resourceGroups/{resource_group}"
           f"/providers/Microsoft.CognitiveServices/accounts/{account_name}"
           f"/projects/{project_name}/connections/{connection_name}"
           f"?api-version=2025-04-01-preview")
    
    payload = {
        "properties": {
            "authType": "ProjectManagedIdentity",
            "category": "RemoteTool",
            "target": mcp_endpoint,
            "isSharedToAll": True,
            "audience": "https://search.azure.com/",
            "metadata": {"ApiType": "Azure"}
        }
    }
    
    resp = requests.put(
        url,
        headers={
            'Authorization': f'Bearer {get_mgmt_token()}',
            'Content-Type': 'application/json'
        },
        json=payload
    )
    
    return resp.json() if resp.status_code in [200, 201] else {"error": resp.text, "status": resp.status_code}
