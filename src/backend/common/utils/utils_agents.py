
import logging
import secrets
import string
from typing import Optional

from common.database.database_base import DatabaseBase
from common.models.messages_af import TeamConfiguration


def generate_assistant_id(prefix: str = "asst_", length: int = 24) -> str:
    """
    Generate a unique ID like 'asst_jRgR5t2U7o8nUPkNGv5HWOgV'.

    - prefix: leading string (defaults to 'asst_')
    - length: number of random characters after the prefix
    """
    # URL-safe characters similar to what OpenAI-style IDs use
    alphabet = string.ascii_letters + string.digits  # a-zA-Z0-9

    # cryptographically strong randomness
    random_part = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}{random_part}"


async def get_database_team_agent_id(
    memory_store: DatabaseBase, team_config: TeamConfiguration, agent_name: str
) -> Optional[str]:
    """Retrieve existing team agent from database, if any."""
    agent_id = None
    try:
        currentAgent = await memory_store.get_team_agent(
            team_id=team_config.team_id, agent_name=agent_name
        )
        if currentAgent and currentAgent.agent_foundry_id:
            agent_id = currentAgent.agent_foundry_id

    except (
        Exception
    ) as ex:  # Consider narrowing this to specific exceptions if possible
        logging.error("Failed to initialize Get database team agent: %s", ex)
    return agent_id
