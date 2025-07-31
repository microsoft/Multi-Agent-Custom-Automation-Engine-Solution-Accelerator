import logging
from typing import Dict, Any, List, Optional

from ..models.messages_kernel import TeamConfiguration, TeamAgent, StartingTask


class JsonService:
    """Service for handling JSON team configuration operations."""

    def __init__(self, memory_store):
        """Initialize with memory store."""
        self.memory_store = memory_store
        self.logger = logging.getLogger(__name__)

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
            # Validate required top-level fields
            required_fields = [
                "id",
                "team_id",
                "name",
                "status",
                "created",
                "created_by",
            ]
            for field in required_fields:
                if field not in json_data:
                    raise ValueError(f"Missing required field: {field}")

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
                team_id=json_data["team_id"],
                name=json_data["name"],
                status=json_data["status"],
                created=json_data["created"],
                created_by=json_data["created_by"],
                agents=agents,
                description=json_data.get("description", ""),
                logo=json_data.get("logo", ""),
                plan=json_data.get("plan", ""),
                starting_tasks=starting_tasks,
                user_id=user_id,
            )

            self.logger.info(
                "Successfully validated team configuration: %s", team_config.team_id
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
            system_message=agent_data.get("system_message", ""),
            description=agent_data.get("description", ""),
            icon=agent_data["icon"],
            index_name=agent_data.get("index_name", ""),
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
            # Convert to dictionary for storage
            config_dict = team_config.model_dump()

            # Save to memory store
            await self.memory_store.upsert_async(
                f"team_config_{team_config.user_id}", config_dict
            )

            self.logger.info(
                "Successfully saved team configuration with ID: %s", team_config.id
            )
            return team_config.id

        except Exception as e:
            self.logger.error("Error saving team configuration: %s", str(e))
            raise ValueError(f"Failed to save team configuration: {str(e)}") from e

    async def get_team_configuration(
        self, config_id: str, user_id: str
    ) -> Optional[TeamConfiguration]:
        """
        Retrieve a team configuration by ID.

        Args:
            config_id: Configuration ID to retrieve
            user_id: User ID for access control

        Returns:
            TeamConfiguration object or None if not found
        """
        try:
            # Query from memory store
            configs = await self.memory_store.query_items(
                f"team_config_{user_id}", limit=1000
            )

            for config_dict in configs:
                if config_dict.get("id") == config_id:
                    return TeamConfiguration.model_validate(config_dict)

            return None

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error("Error retrieving team configuration: %s", str(e))
            return None

    async def get_all_team_configurations(
        self, user_id: str
    ) -> List[TeamConfiguration]:
        """
        Retrieve all team configurations for a user.

        Args:
            user_id: User ID to retrieve configurations for

        Returns:
            List of TeamConfiguration objects
        """
        try:
            # Query from memory store
            configs = await self.memory_store.query_items(
                f"team_config_{user_id}", limit=1000
            )

            team_configs = []
            for config_dict in configs:
                try:
                    team_config = TeamConfiguration.model_validate(config_dict)
                    team_configs.append(team_config)
                except (ValueError, TypeError) as e:
                    self.logger.warning(
                        "Failed to parse team configuration: %s", str(e)
                    )
                    continue

            return team_configs

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error("Error retrieving team configurations: %s", str(e))
            return []

    async def delete_team_configuration(self, config_id: str, user_id: str) -> bool:
        """
        Delete a team configuration by ID.

        Args:
            config_id: Configuration ID to delete
            user_id: User ID for access control

        Returns:
            True if deleted successfully, False if not found
        """
        try:
            # Get all configurations to find the one to delete
            configs = await self.memory_store.query_items(
                f"team_config_{user_id}", limit=1000
            )

            # Find the configuration to delete
            config_to_delete = None
            remaining_configs = []

            for config_dict in configs:
                if config_dict.get("id") == config_id:
                    config_to_delete = config_dict
                else:
                    remaining_configs.append(config_dict)

            if config_to_delete is None:
                self.logger.warning(
                    "Team configuration not found for deletion: %s", config_id
                )
                return False

            # Clear the collection
            await self.memory_store.delete_collection_async(f"team_config_{user_id}")

            # Re-add remaining configurations
            for config in remaining_configs:
                await self.memory_store.upsert_async(f"team_config_{user_id}", config)

            self.logger.info("Successfully deleted team configuration: %s", config_id)
            return True

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error("Error deleting team configuration: %s", str(e))
            return False
