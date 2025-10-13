# Copyright (c) Microsoft. All rights reserved.
""" Factory for creating and managing magentic agents from JSON configurations."""

import json
import logging
import os
from pathlib import Path
from types import SimpleNamespace
from typing import List, Union

from common.config.app_config import config
from common.models.messages_kernel import TeamConfiguration
from v3.config.settings import current_user_id
from v3.magentic_agents.foundry_agent import FoundryAgentTemplate
from v3.magentic_agents.models.agent_models import MCPConfig, SearchConfig
# from v3.magentic_agents.models.agent_models import (BingConfig, MCPConfig,
#                                                     SearchConfig)
from v3.magentic_agents.proxy_agent import ProxyAgent
from v3.magentic_agents.reasoning_agent import ReasoningAgentTemplate


class UnsupportedModelError(Exception):
    """Raised when an unsupported model is specified."""
    pass


class InvalidConfigurationError(Exception):
    """Raised when agent configuration is invalid."""
    pass


class MagenticAgentFactory:
    """Factory for creating and managing magentic agents from JSON configurations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._agent_list: List = []
    
    # @staticmethod
    # def parse_team_config(file_path: Union[str, Path]) -> SimpleNamespace:
    #     """Parse JSON file into objects using SimpleNamespace."""
    #     with open(file_path, 'r') as f:
    #         data = json.load(f)
    #     return json.loads(json.dumps(data), object_hook=lambda d: SimpleNamespace(**d))
    
    async def create_agent_from_config(self, agent_obj: SimpleNamespace) -> Union[FoundryAgentTemplate, ReasoningAgentTemplate, ProxyAgent]:
        """
        Create an agent from configuration object.
        
        Args:
            agent_obj: Agent object from parsed JSON (SimpleNamespace)
            team_model: Model name to determine which template to use
            
        Returns:
            Configured agent instance
            
        Raises:
            UnsupportedModelError: If model is not supported
            InvalidConfigurationError: If configuration is invalid
        """
        # Get model from agent config, team model, or environment
        deployment_name = getattr(agent_obj, 'deployment_name', None)

        if not deployment_name and agent_obj.name.lower() == "proxyagent":
            self.logger.info("Creating ProxyAgent")
            user_id = current_user_id.get()
            return ProxyAgent(user_id=user_id)
        
        # Validate supported models
        supported_models = json.loads(config.SUPPORTED_MODELS)

        if deployment_name not in supported_models:
            raise UnsupportedModelError(f"Model '{deployment_name}' not supported. Supported: {supported_models}")
        
        # Determine which template to use
        use_reasoning = deployment_name.startswith('o')
        
        # Validate reasoning template constraints
        if use_reasoning:
            if getattr(agent_obj, 'use_bing', False) or getattr(agent_obj, 'coding_tools', False):
                raise InvalidConfigurationError(
                    f"ReasoningAgentTemplate cannot use Bing search or coding tools. "
                    f"Agent '{agent_obj.name}' has use_bing={getattr(agent_obj, 'use_bing', False)}, "
                    f"coding_tools={getattr(agent_obj, 'coding_tools', False)}"
                )
        

        
        # Only create configs for explicitly requested capabilities
        search_config = SearchConfig.from_env() if getattr(agent_obj, 'use_rag', False) else None
        
        # Create MCP config with error handling
        mcp_config = None
        use_mcp_flag = getattr(agent_obj, 'use_mcp', False)
        print(f"🔍 DEBUG: Agent '{agent_obj.name}' use_mcp={use_mcp_flag}")  # Force output
        
        if use_mcp_flag:
            try:
                print(f"🔍 DEBUG: Attempting to create MCP config...")  # Force output
                mcp_config = MCPConfig.from_env()
                self.logger.info(f"✅ MCP config created for agent '{agent_obj.name}': {mcp_config.url}")
                print(f"✅ MCP config created: {mcp_config.url}")  # Force output
            except Exception as ex:
                self.logger.error(f"❌ Failed to create MCP config for agent '{agent_obj.name}': {ex}")
                self.logger.error(f"   Agent will be created WITHOUT MCP tools")
                print(f"❌ MCP config FAILED: {ex}")  # Force output
                import traceback
                traceback.print_exc()
                mcp_config = None
        
        # bing_config = BingConfig.from_env() if getattr(agent_obj, 'use_bing', False) else None
        
        self.logger.info(f"Creating agent '{agent_obj.name}' with model '{deployment_name}' "
                        f"(Template: {'Reasoning' if use_reasoning else 'Foundry'})")
        
        # Create appropriate agent
        if use_reasoning:
            # Get reasoning specific configuration
            azure_openai_endpoint = config.AZURE_OPENAI_ENDPOINT

            agent = ReasoningAgentTemplate(
                agent_name=agent_obj.name,
                agent_description=getattr(agent_obj, 'description', ''),
                agent_instructions=getattr(agent_obj, 'system_message', ''),
                model_deployment_name=deployment_name,
                azure_openai_endpoint=azure_openai_endpoint,
                search_config=search_config,
                mcp_config=mcp_config
            )
        else:
            agent = FoundryAgentTemplate(
                agent_name=agent_obj.name,
                agent_description=getattr(agent_obj, 'description', ''),
                agent_instructions=getattr(agent_obj, 'system_message', ''),
                model_deployment_name=deployment_name,
                enable_code_interpreter=getattr(agent_obj, 'coding_tools', False),
                mcp_config=mcp_config,
                #bing_config=bing_config,
                search_config=search_config
            )
        
        await agent.open()
        self.logger.info(f"Successfully created and initialized agent '{agent_obj.name}'")
        return agent

    async def get_agents(self, team_config_input: TeamConfiguration) -> List:
        """
        Create and return a team of agents from JSON configuration.
        
        Args:
            team_config_input: team configuration object from cosmos db
            
        Returns:
            List of initialized agent instances
        """
        # self.logger.info(f"Loading team configuration from: {file_path}")
        
        try:
            
            initalized_agents = []
            
            for i, agent_cfg in enumerate(team_config_input.agents, 1):
                try:
                    self.logger.info(f"Creating agent {i}/{len(team_config_input.agents)}: {agent_cfg.name}")
                    
                    agent = await self.create_agent_from_config(agent_cfg)
                    initalized_agents.append(agent)
                    self._agent_list.append(agent)  # Keep track for cleanup
                    
                    self.logger.info(f"✅ Agent {i}/{len(team_config_input.agents)} created: {agent_cfg.name}")
                    
                except (UnsupportedModelError, InvalidConfigurationError) as e:
                    self.logger.warning(f"Skipped agent {agent_cfg.name}: {e}")
                    continue
                except Exception as e:
                    self.logger.error(f"Failed to create agent {agent_cfg.name}: {e}")
                    continue
            
            self.logger.info(f"Successfully created {len(initalized_agents)}/{len(team_config_input.agents)} agents for team '{team_config_input.name}'")
            return initalized_agents
            
        except Exception as e:
            self.logger.error(f"Failed to load team configuration: {e}")
            raise

    @classmethod        
    async def cleanup_all_agents(cls, agent_list: List):
        """Clean up all created agents."""
        cls.logger = logging.getLogger(__name__)
        cls.logger.info(f"Cleaning up {len(agent_list)} agents")
        
        for agent in agent_list:
            try:
                await agent.close()
            except Exception as ex:
                name = getattr(agent, "agent_name", getattr(agent, "__class__", type("X",(object,),{})).__name__)
                cls.logger.warning(f"Error closing agent {name}: {ex}")
        
        agent_list.clear()
        cls.logger.info("Agent cleanup completed")
