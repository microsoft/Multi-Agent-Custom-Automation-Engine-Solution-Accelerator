import logging
import re
from typing import Any, Dict, List

# from git import List
import aiohttp
from azure.ai.projects.aio import AIProjectClient
from common.config.app_config import config


class FoundryService:
    """Helper around Azure AI Foundry's AIProjectClient.

    Uses AppConfig.get_ai_project_client() to obtain a properly configured
    asynchronous client. Provides a small set of convenience methods and
    can be extended for specific project operations.
    """

    def __init__(self, client: AIProjectClient | None = None) -> None:
        self._client = client
        self.logger = logging.getLogger(__name__)
        # Model validation configuration
        self.subscription_id = config.AZURE_AI_SUBSCRIPTION_ID
        self.resource_group = config.AZURE_AI_RESOURCE_GROUP
        self.project_name = config.AZURE_AI_PROJECT_NAME
        self.project_endpoint = config.AZURE_AI_PROJECT_ENDPOINT

    async def get_client(self) -> AIProjectClient:
        if self._client is None:
            self._client = config.get_ai_project_client()
        return self._client

    # Example convenience wrappers – adjust as your project needs evolve
    async def list_connections(self) -> list[Dict[str, Any]]:
        client = await self.get_client()
        conns = await client.connections.list()
        return [c.as_dict() if hasattr(c, "as_dict") else dict(c) for c in conns]

    async def get_connection(self, name: str) -> Dict[str, Any]:
        client = await self.get_client()
        conn = await client.connections.get(name=name)
        return conn.as_dict() if hasattr(conn, "as_dict") else dict(conn)

    # -----------------------
    # Model validation methods
    # -----------------------
    async def list_model_deployments(self) -> List[Dict[str, Any]]:
        """
        List all model deployments in the Azure AI project using the REST API.
        """
        if not all([self.subscription_id, self.resource_group, self.project_name]):
            self.logger.error("Azure AI project configuration is incomplete")
            return []

        try:
            # Get Azure Management API token (not Cognitive Services token)
            credential = config.get_azure_credentials()
            token = credential.get_token(config.AZURE_MANAGEMENT_SCOPE)

            # Extract Azure OpenAI resource name from endpoint URL
            openai_endpoint = config.AZURE_OPENAI_ENDPOINT
            # Extract resource name from URL like "https://aisa-macae-d3x6aoi7uldi.openai.azure.com/"
            match = re.search(r"https://([^.]+)\.openai\.azure\.com", openai_endpoint)
            if not match:
                self.logger.error(
                    f"Could not extract resource name from endpoint: {openai_endpoint}"
                )
                return []

            openai_resource_name = match.group(1)
            self.logger.info(f"Using Azure OpenAI resource: {openai_resource_name}")

            # Query Azure OpenAI resource deployments
            url = (
                f"https://management.azure.com/subscriptions/{self.subscription_id}/"
                f"resourceGroups/{self.resource_group}/providers/Microsoft.CognitiveServices/"
                f"accounts/{openai_resource_name}/deployments"
            )

            headers = {
                "Authorization": f"Bearer {token.token}",
                "Content-Type": "application/json",
            }
            params = {"api-version": "2024-10-01"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        deployments = data.get("value", [])
                        deployment_info: List[Dict[str, Any]] = []
                        for deployment in deployments:
                            deployment_info.append(
                                {
                                    "name": deployment.get("name"),
                                    "model": deployment.get("properties", {}).get(
                                        "model", {}
                                    ),
                                    "status": deployment.get("properties", {}).get(
                                        "provisioningState"
                                    ),
                                    "endpoint_uri": deployment.get(
                                        "properties", {}
                                    ).get("scoringUri"),
                                }
                            )
                        return deployment_info
                    else:
                        error_text = await response.text()
                        self.logger.error(
                            f"Failed to list deployments. Status: {response.status}, Error: {error_text}"
                        )
                        return []
        except Exception as e:
            self.logger.error(f"Error listing model deployments: {e}")
            return []
