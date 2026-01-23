"""Voice Assembler Agent for creating personalized AI voice agents.

This module implements the Voice Assembler Agent using OpenAI Agents SDK.
The agent creates personalized voice agents for business leads by:
1. Creating OpenAI Vector Stores with dossier content (for file_search RAG)
2. Generating business-specific personality prompts
3. Configuring RealtimeAgent instances with vector store knowledge

Key capabilities per spec FR-4:
- Voice agent answers questions about specific business accurately
- Handles "gotcha" questions using dossier data
- Automatic interruption detection and context management
"""

import asyncio
import concurrent.futures
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


def _load_openai_agents_sdk():
    """Load the openai-agents SDK from site-packages.

    This function handles the naming conflict between our local 'agents'
    package and the openai-agents SDK which also installs as 'agents'.

    Strategy: Load the SDK module directly using importlib without
    modifying sys.modules for our local agents package.
    """
    # Find the venv site-packages directory
    this_file = Path(__file__).resolve()
    leadgen_root = this_file.parent.parent
    venv_paths = list((leadgen_root / ".venv").glob("lib/python*/site-packages"))

    if not venv_paths:
        raise ImportError("Could not find venv site-packages directory")

    site_packages = venv_paths[0]
    sdk_path = site_packages / "agents"

    if not sdk_path.exists():
        raise ImportError(f"openai-agents SDK not found at {sdk_path}")

    # Add site-packages to the FRONT of sys.path
    site_pkg_str = str(site_packages)
    if site_pkg_str in sys.path:
        sys.path.remove(site_pkg_str)
    sys.path.insert(0, site_pkg_str)

    # Identify which modules are ours (our local agents package)
    our_modules = set()
    local_agents_path = str(leadgen_root / "agents")
    for key, mod in list(sys.modules.items()):
        if key == "agents" or key.startswith("agents."):
            if hasattr(mod, "__file__") and mod.__file__:
                if local_agents_path in mod.__file__:
                    our_modules.add(key)

    # Temporarily remove only OUR modules (not the currently-loading one)
    saved_modules = {}
    current_module = "agents.voice_assembler_agent"  # This module being loaded

    for key in list(sys.modules.keys()):
        if key in our_modules and key != current_module:
            saved_modules[key] = sys.modules.pop(key)

    # Also need to remove 'agents' itself if it's our local one
    if "agents" in sys.modules:
        mod = sys.modules["agents"]
        if hasattr(mod, "__file__") and mod.__file__ and local_agents_path in mod.__file__:
            saved_modules["agents"] = sys.modules.pop("agents")

    try:
        # Now import the SDK - Python will find it in site-packages
        import agents as sdk_module

        # Get what we need
        Agent = sdk_module.Agent
        function_tool = sdk_module.function_tool

        return Agent, function_tool

    finally:
        # The SDK will keep working with its modules in sys.modules
        pass


# Load the SDK components at module import time
Agent, function_tool = _load_openai_agents_sdk()

logger = logging.getLogger(__name__)

# Constants
DEFAULT_VECTOR_STORE_EXPIRY_DAYS = 7
DOSSIER_FILENAME = "business_dossier.md"


@dataclass
class VoiceAgentConfig:
    """Configuration for an assembled voice agent.

    Attributes:
        lead_id: Associated lead ID.
        lead_name: Business name.
        vector_store_id: OpenAI Vector Store ID.
        personality_prompt: Generated personality system prompt.
        greeting: Voice agent greeting message.
        closing: Voice agent closing message.
        industry: Business industry.
        dossier_status: Status of dossier ("complete", "partial", "minimal").
        voice_agent_ready: Whether voice agent is fully configured.
        created_at: ISO timestamp of creation.
        error: Error message if assembly failed.
    """

    lead_id: Optional[str]
    lead_name: str
    vector_store_id: Optional[str] = None
    personality_prompt: Optional[str] = None
    greeting: Optional[str] = None
    closing: Optional[str] = None
    industry: Optional[str] = None
    dossier_status: str = "pending"
    voice_agent_ready: bool = False
    created_at: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "lead_id": self.lead_id,
            "lead_name": self.lead_name,
            "vector_store_id": self.vector_store_id,
            "personality_prompt": self.personality_prompt,
            "greeting": self.greeting,
            "closing": self.closing,
            "industry": self.industry,
            "dossier_status": self.dossier_status,
            "voice_agent_ready": self.voice_agent_ready,
            "created_at": self.created_at,
            "error": self.error,
        }


@dataclass
class AssemblyResult:
    """Result from assembling a voice agent for a lead.

    Attributes:
        success: Whether assembly was successful.
        config: Voice agent configuration.
        vector_store_info: Information about created vector store.
        personality_template: Generated personality template details.
        errors: List of errors encountered during assembly.
    """

    success: bool
    config: VoiceAgentConfig
    vector_store_info: Optional[dict] = None
    personality_template: Optional[dict] = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "config": self.config.to_dict(),
            "vector_store_info": self.vector_store_info,
            "personality_template": self.personality_template,
            "errors": self.errors,
        }


def _create_vector_store_internal(
    name: str,
    dossier_content: str,
    metadata: Optional[dict[str, str]] = None,
    expires_after_days: int = DEFAULT_VECTOR_STORE_EXPIRY_DAYS,
) -> dict[str, Any]:
    """Internal implementation for creating vector store with dossier.

    Returns a dict - the @function_tool version wraps this and returns JSON.
    """
    from integrations.openai_vectors import VectorStoreManager

    logger.info("Creating vector store for: %s", name)

    async def _create() -> dict[str, Any]:
        """Async implementation."""
        try:
            async with VectorStoreManager() as manager:
                # Create vector store with dossier content
                vs_info = await manager.create_with_content(
                    name=f"{name} Knowledge Base",
                    content=dossier_content,
                    filename=DOSSIER_FILENAME,
                    expires_after_days=expires_after_days,
                    metadata=metadata,
                    wait_for_ready=True,
                )

                return {
                    "vector_store_id": vs_info.id,
                    "name": vs_info.name,
                    "status": vs_info.status,
                    "file_counts": vs_info.file_counts,
                    "usage_bytes": vs_info.usage_bytes,
                    "is_ready": vs_info.is_ready,
                    "success": True,
                    "error": None,
                }

        except ValueError as e:
            logger.error("Configuration error for VectorStoreManager: %s", e)
            return {
                "vector_store_id": None,
                "name": None,
                "status": "failed",
                "file_counts": {},
                "usage_bytes": 0,
                "is_ready": False,
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            logger.error("Error creating vector store: %s", e)
            return {
                "vector_store_id": None,
                "name": None,
                "status": "failed",
                "file_counts": {},
                "usage_bytes": 0,
                "is_ready": False,
                "success": False,
                "error": str(e),
            }

    # Run async code in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _create())
                return future.result()
        else:
            return loop.run_until_complete(_create())
    except RuntimeError:
        return asyncio.run(_create())


@function_tool
def create_vector_store_for_lead(
    business_name: str,
    dossier_content: str,
    lead_id: Optional[str] = None,
    expires_after_days: int = DEFAULT_VECTOR_STORE_EXPIRY_DAYS,
) -> str:
    """Create an OpenAI Vector Store populated with business dossier content.

    Creates a vector store for file_search RAG capabilities, allowing the
    voice agent to answer detailed questions about the business accurately.
    The dossier content is automatically chunked and embedded.

    Args:
        business_name: Name of the business (used in vector store name).
        dossier_content: Markdown dossier content to upload.
        lead_id: Optional lead ID for metadata tracking.
        expires_after_days: Days until vector store expires. Defaults to 7.

    Returns:
        JSON string containing:
        - vector_store_id: Created vector store ID (vs_xxx...)
        - name: Vector store name
        - status: Processing status ("completed", "in_progress", "failed")
        - file_counts: Dictionary with file count by status
        - usage_bytes: Storage usage in bytes
        - is_ready: Whether vector store is ready for queries
        - success: Whether creation was successful
        - error: Error message if creation failed

    Example:
        >>> result_json = create_vector_store_for_lead(
        ...     "Acme Dental",
        ...     "# Company Overview\\n\\nAcme Dental is...",
        ...     lead_id="lead_123"
        ... )
        >>> import json; result = json.loads(result_json)
        >>> print(f"Vector store: {result['vector_store_id']}")
    """
    metadata = {}
    if lead_id:
        metadata["lead_id"] = lead_id

    result = _create_vector_store_internal(
        name=business_name,
        dossier_content=dossier_content,
        metadata=metadata if metadata else None,
        expires_after_days=expires_after_days,
    )

    return json.dumps(result)


def _generate_voice_personality_internal(
    business_data: dict[str, Any],
    dossier_content: Optional[str] = None,
) -> dict[str, Any]:
    """Internal implementation for generating voice personality.

    Returns a dict - the @function_tool version wraps this and returns JSON.
    """
    from utils.voice_personality import (
        generate_personality,
        generate_personality_from_dossier,
    )

    business_name = business_data.get("name", "Unknown Business")
    logger.info("Generating voice personality for: %s", business_name)

    try:
        # Generate personality template
        if dossier_content:
            template = generate_personality_from_dossier(
                dossier_content=dossier_content,
                business_name=business_name,
                industry=business_data.get("industry", "general"),
            )
        else:
            template = generate_personality(business_data)

        return {
            "system_prompt": template.system_prompt,
            "greeting": template.greeting,
            "closing": template.closing,
            "fallback_responses": template.fallback_responses,
            "transfer_message": template.transfer_message,
            "voicemail_message": template.voicemail_message,
            "tone": template.config.tone.value if template.config.tone else "friendly",
            "industry": template.config.industry,
            "prompt_word_count": len(template.system_prompt.split()),
            "success": True,
            "error": None,
        }

    except Exception as e:
        logger.error("Error generating voice personality: %s", e)
        return {
            "system_prompt": None,
            "greeting": None,
            "closing": None,
            "fallback_responses": [],
            "transfer_message": None,
            "voicemail_message": None,
            "tone": None,
            "industry": None,
            "prompt_word_count": 0,
            "success": False,
            "error": str(e),
        }


@function_tool
def generate_voice_personality(
    business_name: str,
    industry: str,
    address: Optional[str] = None,
    phone: Optional[str] = None,
    website: Optional[str] = None,
    services: Optional[str] = None,
    dossier_content: Optional[str] = None,
) -> str:
    """Generate a business-specific voice agent personality prompt.

    Creates a comprehensive system prompt for the voice agent including:
    - Business identity and information
    - Industry-specific conversation handling
    - Appointment booking flows
    - Tone and style guidelines
    - Emergency/urgency handling
    - Fallback and transfer behaviors

    If dossier_content is provided, it will be injected into the prompt
    to enable answering detailed business-specific questions.

    Args:
        business_name: Name of the business.
        industry: Industry category (dentist, hvac, salon, etc.).
        address: Business address.
        phone: Business phone number.
        website: Business website URL.
        services: Comma-separated list of services offered.
        dossier_content: Full research dossier to inject (optional).

    Returns:
        JSON string containing:
        - system_prompt: Complete system prompt for RealtimeAgent
        - greeting: Opening greeting message
        - closing: Closing message
        - fallback_responses: List of fallback response options
        - transfer_message: Message when transferring to human
        - voicemail_message: After-hours voicemail message
        - tone: Personality tone used
        - industry: Industry classification
        - prompt_word_count: Word count of system prompt
        - success: Whether generation was successful
        - error: Error message if generation failed

    Example:
        >>> result_json = generate_voice_personality(
        ...     "Acme Dental",
        ...     "dentist",
        ...     services="cleanings,fillings,whitening"
        ... )
        >>> import json; result = json.loads(result_json)
        >>> print(result['greeting'])
    """
    # Build business data dict
    business_data = {
        "name": business_name,
        "industry": industry,
    }

    if address:
        business_data["address"] = address
    if phone:
        business_data["phone"] = phone
    if website:
        business_data["website"] = website
    if services:
        business_data["services"] = [s.strip() for s in services.split(",")]

    result = _generate_voice_personality_internal(
        business_data=business_data,
        dossier_content=dossier_content,
    )

    return json.dumps(result)


def _delete_vector_store_internal(vector_store_id: str) -> dict[str, Any]:
    """Internal implementation for deleting vector store.

    Returns a dict - the @function_tool version wraps this and returns JSON.
    """
    from integrations.openai_vectors import VectorStoreManager

    logger.info("Deleting vector store: %s", vector_store_id)

    async def _delete() -> dict[str, Any]:
        """Async implementation."""
        try:
            async with VectorStoreManager() as manager:
                deleted = await manager.delete_vector_store(vector_store_id)

                return {
                    "vector_store_id": vector_store_id,
                    "deleted": deleted,
                    "success": deleted,
                    "error": None if deleted else "Deletion returned false",
                }

        except Exception as e:
            logger.error("Error deleting vector store: %s", e)
            return {
                "vector_store_id": vector_store_id,
                "deleted": False,
                "success": False,
                "error": str(e),
            }

    # Run async code in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _delete())
                return future.result()
        else:
            return loop.run_until_complete(_delete())
    except RuntimeError:
        return asyncio.run(_delete())


@function_tool
def delete_vector_store(vector_store_id: str) -> str:
    """Delete a vector store when no longer needed.

    Cleans up vector store resources to manage costs and storage.
    Use this when a lead is no longer active or the voice agent
    configuration needs to be recreated.

    Args:
        vector_store_id: The ID of the vector store to delete (vs_xxx...).

    Returns:
        JSON string containing:
        - vector_store_id: The vector store ID
        - deleted: Whether deletion was successful
        - success: Whether operation completed successfully
        - error: Error message if deletion failed

    Example:
        >>> result_json = delete_vector_store("vs_abc123...")
        >>> import json; result = json.loads(result_json)
        >>> if result['deleted']:
        ...     print("Vector store cleaned up")
    """
    result = _delete_vector_store_internal(vector_store_id)
    return json.dumps(result)


def _assemble_voice_agent_internal(
    lead_data: dict[str, Any],
    dossier_content: str,
    dossier_status: str = "complete",
) -> AssemblyResult:
    """Internal implementation for full voice agent assembly.

    This orchestrates the complete assembly process:
    1. Create vector store with dossier
    2. Generate personality prompt with dossier injection
    3. Return configuration for RealtimeAgent
    """
    from datetime import datetime, timezone

    lead_name = lead_data.get("name", "Unknown Business")
    lead_id = lead_data.get("id") or lead_data.get("lead_id")
    industry = lead_data.get("industry", "general")

    logger.info(
        "Assembling voice agent for: %s (lead_id=%s)",
        lead_name,
        lead_id,
    )

    errors: list[str] = []
    config = VoiceAgentConfig(
        lead_id=lead_id,
        lead_name=lead_name,
        industry=industry,
        dossier_status=dossier_status,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    # Step 1: Create vector store with dossier
    logger.info("Step 1: Creating vector store for %s", lead_name)
    vs_result = _create_vector_store_internal(
        name=lead_name,
        dossier_content=dossier_content,
        metadata={"lead_id": str(lead_id)} if lead_id else None,
    )

    vector_store_info = vs_result
    if vs_result["success"]:
        config.vector_store_id = vs_result["vector_store_id"]
        logger.info(
            "Vector store created: %s (is_ready=%s)",
            config.vector_store_id,
            vs_result["is_ready"],
        )
    else:
        errors.append(f"Vector store creation failed: {vs_result.get('error')}")
        logger.error("Vector store creation failed: %s", vs_result.get("error"))

    # Step 2: Generate personality with dossier injection
    logger.info("Step 2: Generating voice personality for %s", lead_name)
    personality_result = _generate_voice_personality_internal(
        business_data=lead_data,
        dossier_content=dossier_content,
    )

    personality_template = personality_result
    if personality_result["success"]:
        config.personality_prompt = personality_result["system_prompt"]
        config.greeting = personality_result["greeting"]
        config.closing = personality_result["closing"]
        logger.info(
            "Personality generated: %d words",
            personality_result["prompt_word_count"],
        )
    else:
        errors.append(f"Personality generation failed: {personality_result.get('error')}")
        logger.error("Personality generation failed: %s", personality_result.get("error"))

    # Determine if voice agent is ready
    config.voice_agent_ready = (
        config.vector_store_id is not None
        and config.personality_prompt is not None
    )

    if not config.voice_agent_ready and errors:
        config.error = "; ".join(errors)

    success = config.voice_agent_ready
    logger.info(
        "Voice agent assembly complete for %s: success=%s, errors=%d",
        lead_name,
        success,
        len(errors),
    )

    return AssemblyResult(
        success=success,
        config=config,
        vector_store_info=vector_store_info,
        personality_template=personality_template,
        errors=errors,
    )


@function_tool
def assemble_voice_agent(
    name: str,
    dossier_content: str,
    lead_id: Optional[str] = None,
    industry: Optional[str] = None,
    address: Optional[str] = None,
    phone: Optional[str] = None,
    website: Optional[str] = None,
    dossier_status: str = "complete",
) -> str:
    """Assemble a complete voice agent for a business lead.

    This is the main function for creating a fully configured voice agent.
    It performs the complete assembly process:
    1. Creates an OpenAI Vector Store with the research dossier
    2. Generates a business-specific personality prompt with dossier injection
    3. Returns a complete configuration for RealtimeAgent

    The resulting voice agent will:
    - Answer questions accurately using the dossier content
    - Handle gotcha questions that test business knowledge
    - Book appointments following industry-specific flows
    - Transfer to humans when appropriate
    - Handle after-hours calls with voicemail

    Args:
        name: Business name.
        dossier_content: Complete research dossier in markdown format.
        lead_id: Optional lead ID for tracking.
        industry: Industry category for specialized handling.
        address: Business address.
        phone: Business phone number.
        website: Business website URL.
        dossier_status: Status of dossier ("complete", "partial", "minimal").

    Returns:
        JSON string containing:
        - success: Whether assembly was successful
        - config: Voice agent configuration dict with:
            - lead_id: Associated lead ID
            - lead_name: Business name
            - vector_store_id: OpenAI Vector Store ID
            - personality_prompt: System prompt for RealtimeAgent
            - greeting: Opening greeting
            - closing: Closing message
            - industry: Business industry
            - dossier_status: Dossier completeness status
            - voice_agent_ready: Whether fully configured
            - created_at: ISO timestamp
            - error: Error message if failed
        - vector_store_info: Vector store creation details
        - personality_template: Personality generation details
        - errors: List of any errors encountered

    Example:
        >>> result_json = assemble_voice_agent(
        ...     name="Acme Dental",
        ...     dossier_content="# Company Overview\\n\\nAcme Dental...",
        ...     industry="dentist",
        ...     lead_id="lead_123"
        ... )
        >>> import json; result = json.loads(result_json)
        >>> if result['success']:
        ...     print(f"Voice agent ready: {result['config']['vector_store_id']}")
    """
    # Build lead data dict
    lead_data = {
        "name": name,
        "lead_id": lead_id,
        "industry": industry or "general",
    }

    if address:
        lead_data["address"] = address
    if phone:
        lead_data["phone"] = phone
    if website:
        lead_data["website"] = website

    result = _assemble_voice_agent_internal(
        lead_data=lead_data,
        dossier_content=dossier_content,
        dossier_status=dossier_status,
    )

    return json.dumps(result.to_dict())


@function_tool
def get_realtime_agent_config(
    vector_store_id: str,
    personality_prompt: str,
    business_name: str,
) -> str:
    """Get configuration parameters for creating an OpenAI RealtimeAgent.

    Returns the configuration needed to instantiate a RealtimeAgent
    from the OpenAI Agents SDK with file_search capabilities.

    Note: RealtimeAgent provides automatic interruption detection and
    context management for voice interactions. The vector_store_id
    enables file_search tool for answering business-specific questions.

    Args:
        vector_store_id: Vector Store ID for file_search RAG.
        personality_prompt: System prompt for the agent.
        business_name: Business name for the agent.

    Returns:
        JSON string containing:
        - name: Agent name
        - instructions: System prompt/instructions
        - tools: List of tools to enable
        - tool_resources: Resources for file_search
        - model: Recommended model
        - voice_settings: Recommended voice configuration
        - success: Always True for this function

    Example:
        >>> config_json = get_realtime_agent_config(
        ...     "vs_abc123",
        ...     "You are the AI receptionist for Acme Dental...",
        ...     "Acme Dental"
        ... )
        >>> import json; config = json.loads(config_json)
        >>> # Use config to instantiate RealtimeAgent
    """
    config = {
        "name": f"{business_name} Voice Assistant",
        "instructions": personality_prompt,
        "tools": [
            {"type": "file_search"},
        ],
        "tool_resources": {
            "file_search": {
                "vector_store_ids": [vector_store_id],
            },
        },
        "model": "gpt-4o-realtime-preview",
        "voice_settings": {
            "voice": "alloy",
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500,
            },
        },
        "success": True,
    }

    return json.dumps(config)


# Agent instructions defining behavior and constraints
VOICE_ASSEMBLER_AGENT_INSTRUCTIONS = """You are a Voice Agent Assembler specialized in creating personalized AI voice assistants for businesses.

Your primary task is to assemble voice agents that can:
1. Answer questions about a specific business accurately using dossier content
2. Handle "gotcha" questions that test knowledge of the business
3. Book appointments following industry-specific flows
4. Provide a professional, business-appropriate phone experience

## Your Assembly Process

When given a lead with research dossier, follow these steps:

1. **Create Vector Store**
   - Use `create_vector_store_for_lead` to create an OpenAI Vector Store
   - Upload the dossier content for file_search RAG capabilities
   - The vector store enables the voice agent to answer detailed questions

2. **Generate Personality**
   - Use `generate_voice_personality` to create a business-specific prompt
   - Include the dossier content for accurate question handling
   - The personality defines tone, style, and conversation flows

3. **Full Assembly (Recommended)**
   - Use `assemble_voice_agent` for end-to-end automation
   - This creates vector store AND generates personality in one call
   - Returns complete configuration for RealtimeAgent

4. **Get RealtimeAgent Config**
   - Use `get_realtime_agent_config` to get configuration parameters
   - Returns settings for instantiating the OpenAI RealtimeAgent

## Voice Agent Capabilities

The assembled voice agents will:
- Answer business-specific questions using file_search over the dossier
- Handle appointment booking with industry-appropriate flows
- Use caller names when known
- Transfer to humans when requested or appropriate
- Handle after-hours calls gracefully
- Never make up information not in the dossier

## Important Notes

- Always provide complete dossier content for accurate voice responses
- Vector stores expire after 7 days by default (configurable)
- Use `delete_vector_store` to clean up when agents are no longer needed
- RealtimeAgent has automatic interruption detection built-in
- Voice settings use PCM16 audio format for Twilio compatibility

## Edge Cases

- **Partial dossier**: Still create agent, but mark dossier_status appropriately
- **Vector store failure**: Report error but still generate personality
- **API rate limits**: Note error and suggest retry later
- **Missing lead data**: Use defaults where possible, log warnings

## Output Format

Always report:
- Whether assembly was successful
- Vector store ID if created
- Any errors encountered
- Readiness status of the voice agent
"""

# Create the voice assembler agent instance
voice_assembler_agent = Agent(
    name="Voice Assembler Agent",
    instructions=VOICE_ASSEMBLER_AGENT_INSTRUCTIONS,
    tools=[
        create_vector_store_for_lead,
        generate_voice_personality,
        delete_vector_store,
        assemble_voice_agent,
        get_realtime_agent_config,
    ],
)
