import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
)
from azure.search.documents.indexes import SearchIndexClient
from common.config.app_config import config
from common.database.database_base import DatabaseBase
from common.models.messages_kernel import (
    StartingTask,
    TeamAgent,
    TeamConfiguration,
    UserCurrentTeam,
)
from v3.common.services.foundry_service import FoundryService


class TeamService:
    """Service for handling JSON team configuration operations."""

    def __init__(self, memory_context: Optional[DatabaseBase] = None):
        """Initialize with optional memory context."""
        self.memory_context = memory_context
        self.logger = logging.getLogger(__name__)

        # Search validation configuration
        self.search_endpoint = config.AZURE_SEARCH_ENDPOINT

        self.search_credential = config.get_azure_credentials()

    async def validate_and_parse_team_config(
        self, json_data: Dict[str, Any], user_id: str
    ) -> TeamConfiguration:
        """
        Validate and parse team configuration JSON.

        Args:
            json_data: Raw JSON data
            user_id: User ID who uploaded the configuration

        Returns:
            TeamConfiguration object

        Raises:
            ValueError: If JSON structure is invalid
        """
        try:
            # Validate required top-level fields (id and team_id will be generated)
            required_fields = [
                "name",
                "status",
            ]
            for field in required_fields:
                if field not in json_data:
                    raise ValueError(f"Missing required field: {field}")

            # Generate unique IDs and timestamps
            unique_team_id = str(uuid.uuid4())
            session_id = str(uuid.uuid4())
            current_timestamp = datetime.now(timezone.utc).isoformat()

            # Validate agents array exists and is not empty
            if "agents" not in json_data or not isinstance(json_data["agents"], list):
                raise ValueError(
                    "Missing or invalid 'agents' field - must be a non-empty array"
                )

            if len(json_data["agents"]) == 0:
                raise ValueError("Agents array cannot be empty")

            # Validate starting_tasks array exists and is not empty
            if "starting_tasks" not in json_data or not isinstance(
                json_data["starting_tasks"], list
            ):
                raise ValueError(
                    "Missing or invalid 'starting_tasks' field - must be a non-empty array"
                )

            if len(json_data["starting_tasks"]) == 0:
                raise ValueError("Starting tasks array cannot be empty")

            # Parse agents
            agents = []
            for agent_data in json_data["agents"]:
                agent = self._validate_and_parse_agent(agent_data)
                agents.append(agent)

            # Parse starting tasks
            starting_tasks = []
            for task_data in json_data["starting_tasks"]:
                task = self._validate_and_parse_task(task_data)
                starting_tasks.append(task)

            # Create team configuration
            team_config = TeamConfiguration(
                id=unique_team_id,  # Use generated GUID
                session_id=session_id,
                team_id=unique_team_id,  # Use generated GUID
                name=json_data["name"],
                status=json_data["status"],
                created=current_timestamp,  # Use generated timestamp
                created_by=user_id,  # Use user_id who uploaded the config
                agents=agents,
                description=json_data.get("description", ""),
                logo=json_data.get("logo", ""),
                plan=json_data.get("plan", ""),
                starting_tasks=starting_tasks,
                user_id=user_id,
            )

            self.logger.info(
                "Successfully validated team configuration: %s (ID: %s)",
                team_config.team_id,
                team_config.id,
            )
            return team_config

        except Exception as e:
            self.logger.error("Error validating team configuration: %s", str(e))
            raise ValueError(f"Invalid team configuration: {str(e)}") from e

    def _validate_and_parse_agent(self, agent_data: Dict[str, Any]) -> TeamAgent:
        """Validate and parse a single agent."""
        required_fields = ["input_key", "type", "name", "icon"]
        for field in required_fields:
            if field not in agent_data:
                raise ValueError(f"Agent missing required field: {field}")

        return TeamAgent(
            input_key=agent_data["input_key"],
            type=agent_data["type"],
            name=agent_data["name"],
            deployment_name=agent_data.get("deployment_name", ""),
            icon=agent_data["icon"],
            system_message=agent_data.get("system_message", ""),
            description=agent_data.get("description", ""),
            use_rag=agent_data.get("use_rag", False),
            use_mcp=agent_data.get("use_mcp", False),
            use_bing=agent_data.get("use_bing", False),
            use_reasoning=agent_data.get("use_reasoning", False),
            index_name=agent_data.get("index_name", ""),
            coding_tools=agent_data.get("coding_tools", False),
        )

    def _validate_and_parse_task(self, task_data: Dict[str, Any]) -> StartingTask:
        """Validate and parse a single starting task."""
        required_fields = ["id", "name", "prompt", "created", "creator", "logo"]
        for field in required_fields:
            if field not in task_data:
                raise ValueError(f"Starting task missing required field: {field}")

        return StartingTask(
            id=task_data["id"],
            name=task_data["name"],
            prompt=task_data["prompt"],
            created=task_data["created"],
            creator=task_data["creator"],
            logo=task_data["logo"],
        )

    async def save_team_configuration(self, team_config: TeamConfiguration) -> str:
        """
        Save team configuration to the database.

        Args:
            team_config: TeamConfiguration object to save

        Returns:
            The unique ID of the saved configuration
        """
        try:
            # Use the specific add_team method from cosmos memory context
            await self.memory_context.add_team(team_config)

            self.logger.info(
                "Successfully saved team configuration with ID: %s", team_config.id
            )
            return team_config.id

        except Exception as e:
            self.logger.error("Error saving team configuration: %s", str(e))
            raise ValueError(f"Failed to save team configuration: {str(e)}") from e

    async def get_team_configuration(
        self, team_id: str, user_id: str
    ) -> Optional[TeamConfiguration]:
        """
        Retrieve a team configuration by ID.

        Args:
            team_id: Configuration ID to retrieve
            user_id: User ID for access control

        Returns:
            TeamConfiguration object or None if not found
        """
        try:
            # Get the specific configuration using the team-specific method
            team_config = await self.memory_context.get_team(team_id)

            if team_config is None:
                return None

            # Verify the configuration belongs to the user
            # if team_config.user_id != user_id:
            #     self.logger.warning(
            #         "Access denied: config %s does not belong to user %s",
            #         team_id,
            #         user_id,
            #     )
            #     return None

            return team_config

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error("Error retrieving team configuration: %s", str(e))
            return None

    async def delete_user_current_team(self, user_id: str) -> bool:
        """
        Delete the current team for a user.

        Args:
            user_id: User ID to delete the current team for

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.memory_context.delete_current_team(user_id)
            self.logger.info("Successfully deleted current team for user %s", user_id)
            return True

        except Exception as e:
            self.logger.error("Error deleting current team: %s", str(e))
            return False

    async def handle_team_selection(
        self, user_id: str, team_id: str
    ) -> UserCurrentTeam:
        """
        Set a default team for a user.

        Args:
            user_id: User ID to set the default team for
            team_id: Team ID to set as default

        Returns:
            True if successful, False otherwise
        """
        print("Handling team selection for user:", user_id, "team:", team_id)
        try:
            await self.memory_context.delete_current_team(user_id)
            current_team = UserCurrentTeam(
                user_id=user_id,
                team_id=team_id,
            )
            await self.memory_context.set_current_team(current_team)
            return current_team

        except Exception as e:
            self.logger.error("Error setting default team: %s", str(e))
            return None

    async def get_all_team_configurations(self) -> List[TeamConfiguration]:
        """
        Retrieve all team configurations for a user.

        Args:
            user_id: User ID to retrieve configurations for

        Returns:
            List of TeamConfiguration objects
        """
        try:
            # Use the specific get_all_teams method
            team_configs = await self.memory_context.get_all_teams()
            return team_configs

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error("Error retrieving team configurations: %s", str(e))
            return []

    async def delete_team_configuration(self, team_id: str, user_id: str) -> bool:
        """
        Delete a team configuration by ID.

        Args:
            team_id: Configuration ID to delete
            user_id: User ID for access control

        Returns:
            True if deleted successfully, False if not found
        """
        try:
            # First, verify the configuration exists and belongs to the user
            success = await self.memory_context.delete_team(team_id)
            if success:
                self.logger.info("Successfully deleted team configuration: %s", team_id)

            return success

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error("Error deleting team configuration: %s", str(e))
            return False

    def extract_models_from_agent(self, agent: Dict[str, Any]) -> set:
        """
        Extract all possible model references from a single agent configuration.
         Skip proxy agents as they don't require deployment models.
        """
        models = set()

        # Skip proxy agents - they don't need deployment models
        if agent.get("name", "").lower() == "proxyagent":
            return models

        if agent.get("deployment_name"):
            models.add(str(agent["deployment_name"]).lower())

        if agent.get("model"):
            models.add(str(agent["model"]).lower())

        config = agent.get("config", {})
        if isinstance(config, dict):
            for field in ["model", "deployment_name", "engine"]:
                if config.get(field):
                    models.add(str(config[field]).lower())

        instructions = agent.get("instructions", "") or agent.get("system_message", "")
        if instructions:
            models.update(self.extract_models_from_text(str(instructions)))

        return models

    def extract_models_from_text(self, text: str) -> set:
        """Extract model names from text using pattern matching."""
        import re

        models = set()
        text_lower = text.lower()
        model_patterns = [
            r"gpt-4o(?:-\w+)?",
            r"gpt-4(?:-\w+)?",
            r"gpt-35-turbo(?:-\w+)?",
            r"gpt-3\.5-turbo(?:-\w+)?",
            r"claude-3(?:-\w+)?",
            r"claude-2(?:-\w+)?",
            r"gemini-pro(?:-\w+)?",
            r"mistral-\w+",
            r"llama-?\d+(?:-\w+)?",
            r"text-davinci-\d+",
            r"text-embedding-\w+",
            r"ada-\d+",
            r"babbage-\d+",
            r"curie-\d+",
            r"davinci-\d+",
        ]

        for pattern in model_patterns:
            matches = re.findall(pattern, text_lower)
            models.update(matches)

        return models

    async def validate_team_models(
        self, team_config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate that all models required by agents in the team config are deployed."""
        try:
            foundry_service = FoundryService()
            deployments = await foundry_service.list_model_deployments()
            available_models = [
                d.get("name", "").lower()
                for d in deployments
                if d.get("status") == "Succeeded"
            ]

            required_models: set = set()
            agents = team_config.get("agents", [])
            for agent in agents:
                if isinstance(agent, dict):
                    required_models.update(self.extract_models_from_agent(agent))

            team_level_models = self.extract_team_level_models(team_config)
            required_models.update(team_level_models)

            if not required_models:
                default_model = config.AZURE_OPENAI_DEPLOYMENT_NAME
                required_models.add(default_model.lower())

            missing_models: List[str] = []
            for model in required_models:
                # Temporary bypass for known deployed models
                if model.lower() in ["gpt-4o", "o3", "gpt-4", "gpt-35-turbo"]:
                    continue
                if model not in available_models:
                    missing_models.append(model)

            is_valid = len(missing_models) == 0
            if not is_valid:
                self.logger.warning(f"Missing model deployments: {missing_models}")
                self.logger.info(f"Available deployments: {available_models}")
            return is_valid, missing_models
        except Exception as e:
            self.logger.error(f"Error validating team models: {e}")
            return True, []

    async def get_deployment_status_summary(self) -> Dict[str, Any]:
        """Get a summary of deployment status for debugging/monitoring."""
        try:
            foundry_service = FoundryService()
            deployments = await foundry_service.list_model_deployments()
            summary: Dict[str, Any] = {
                "total_deployments": len(deployments),
                "successful_deployments": [],
                "failed_deployments": [],
                "pending_deployments": [],
            }
            for deployment in deployments:
                name = deployment.get("name", "unknown")
                status = deployment.get("status", "unknown")
                if status == "Succeeded":
                    summary["successful_deployments"].append(name)
                elif status in ["Failed", "Canceled"]:
                    summary["failed_deployments"].append(name)
                else:
                    summary["pending_deployments"].append(name)
            return summary
        except Exception as e:
            self.logger.error(f"Error getting deployment summary: {e}")
            return {"error": str(e)}

    def extract_team_level_models(self, team_config: Dict[str, Any]) -> set:
        """Extract model references from team-level configuration."""
        models = set()
        for field in ["default_model", "model", "llm_model"]:
            if team_config.get(field):
                models.add(str(team_config[field]).lower())
        settings = team_config.get("settings", {})
        if isinstance(settings, dict):
            for field in ["model", "deployment_name"]:
                if settings.get(field):
                    models.add(str(settings[field]).lower())
        env_config = team_config.get("environment", {})
        if isinstance(env_config, dict):
            for field in ["model", "openai_deployment"]:
                if env_config.get(field):
                    models.add(str(env_config[field]).lower())
        return models

    # -----------------------
    # Search validation methods
    # -----------------------

    async def validate_team_search_indexes(
        self, team_config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate that all search indexes referenced in the team config exist.
        Only validates if there are actually search indexes/RAG agents in the config.
        """
        try:
            index_names = self.extract_index_names(team_config)
            has_rag_agents = self.has_rag_or_search_agents(team_config)

            if not index_names and not has_rag_agents:
                self.logger.info(
                    "No search indexes or RAG agents found in team config - skipping search validation"
                )
                return True, []

            if not self.search_endpoint:
                if index_names or has_rag_agents:
                    error_msg = "Team configuration references search indexes but no Azure Search endpoint is configured"
                    self.logger.warning(error_msg)
                    return False, [error_msg]
                else:
                    return True, []

            if not index_names:
                self.logger.info(
                    "RAG agents found but no specific search indexes specified"
                )
                return True, []

            validation_errors: List[str] = []
            unique_indexes = set(index_names)
            self.logger.info(
                f"Validating {len(unique_indexes)} search indexes: {list(unique_indexes)}"
            )
            for index_name in unique_indexes:
                is_valid, error_message = await self.validate_single_index(index_name)
                if not is_valid:
                    validation_errors.append(error_message)
            return len(validation_errors) == 0, validation_errors
        except Exception as e:
            self.logger.error(f"Error validating search indexes: {str(e)}")
            return False, [f"Search index validation error: {str(e)}"]

    def extract_index_names(self, team_config: Dict[str, Any]) -> List[str]:
        """Extract all index names from RAG agents in the team configuration."""
        index_names: List[str] = []
        agents = team_config.get("agents", [])
        for agent in agents:
            if isinstance(agent, dict):
                agent_type = str(agent.get("type", "")).strip().lower()
                if agent_type == "rag":
                    index_name = agent.get("index_name")
                    if index_name and str(index_name).strip():
                        index_names.append(str(index_name).strip())
        return list(set(index_names))

    def has_rag_or_search_agents(self, team_config: Dict[str, Any]) -> bool:
        """Check if the team configuration contains RAG agents."""
        agents = team_config.get("agents", [])
        for agent in agents:
            if isinstance(agent, dict):
                agent_type = str(agent.get("type", "")).strip().lower()
                if agent_type == "rag":
                    return True
        return False

    async def validate_single_index(self, index_name: str) -> Tuple[bool, str]:
        """Validate that a single search index exists and is accessible."""
        try:
            index_client = SearchIndexClient(
                endpoint=self.search_endpoint, credential=self.search_credential
            )
            index = index_client.get_index(index_name)
            if index:
                self.logger.info(f"Search index '{index_name}' found and accessible")
                return True, ""
            else:
                error_msg = f"Search index '{index_name}' exists but may not be properly configured"
                self.logger.warning(error_msg)
                return False, error_msg
        except ResourceNotFoundError:
            error_msg = f"Search index '{index_name}' does not exist"
            self.logger.error(error_msg)
            return False, error_msg
        except ClientAuthenticationError as e:
            error_msg = (
                f"Authentication failed for search index '{index_name}': {str(e)}"
            )
            self.logger.error(error_msg)
            return False, error_msg
        except HttpResponseError as e:
            error_msg = f"Error accessing search index '{index_name}': {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = (
                f"Unexpected error validating search index '{index_name}': {str(e)}"
            )
            self.logger.error(error_msg)
            return False, error_msg

    async def get_search_index_summary(self) -> Dict[str, Any]:
        """Get a summary of available search indexes for debugging/monitoring."""
        try:
            if not self.search_endpoint:
                return {"error": "No Azure Search endpoint configured"}
            index_client = SearchIndexClient(
                endpoint=self.search_endpoint, credential=self.search_credential
            )
            indexes = list(index_client.list_indexes())
            summary = {
                "search_endpoint": self.search_endpoint,
                "total_indexes": len(indexes),
                "available_indexes": [index.name for index in indexes],
            }
            return summary
        except Exception as e:
            self.logger.error(f"Error getting search index summary: {e}")
            return {"error": str(e)}
