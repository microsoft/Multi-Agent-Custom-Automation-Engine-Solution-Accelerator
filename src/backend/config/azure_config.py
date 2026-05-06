# Copyright (c) Microsoft. All rights reserved.
"""Azure OpenAI and authentication configuration."""

import logging

from agent_framework import ChatOptions
from agent_framework.azure import AzureOpenAIChatClient

from common.config.app_config import config

logger = logging.getLogger(__name__)


class AzureConfig:
    """Azure OpenAI and authentication configuration (agent_framework)."""

    def __init__(self):
        self.endpoint = config.AZURE_OPENAI_ENDPOINT
        self.reasoning_model = config.REASONING_MODEL_NAME
        self.standard_model = config.AZURE_OPENAI_DEPLOYMENT_NAME
        self.credential = config.get_azure_credentials()

    def ad_token_provider(self) -> str:
        """Return a bearer token string for Azure Cognitive Services scope."""
        token = self.credential.get_token(config.AZURE_COGNITIVE_SERVICES)
        return token.token

    async def create_chat_completion_service(
        self, use_reasoning_model: bool = False
    ) -> AzureOpenAIChatClient:
        """
        Create an AzureOpenAIChatClient for the selected model.

        NOTE (Phase 2): This method will be removed when agents migrate to
        FoundryChatClient. Kept here so existing callers have a clean import target
        during the transition.
        """
        model_name = self.reasoning_model if use_reasoning_model else self.standard_model
        return AzureOpenAIChatClient(
            endpoint=self.endpoint,
            model_deployment_name=model_name,
            azure_ad_token_provider=self.ad_token_provider,
        )

    def create_execution_settings(self) -> ChatOptions:
        """Create ChatOptions with standard execution settings."""
        return ChatOptions(
            max_output_tokens=4000,
            temperature=0.1,
        )


# Module-level singleton
azure_config = AzureConfig()
