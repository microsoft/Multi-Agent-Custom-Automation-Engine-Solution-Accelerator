"""Frontend Deployer Agent for automating demo site deployments to Vercel.

This module implements the Frontend Deployer Agent using OpenAI Agents SDK.
The agent automates the deployment of personalized demo sites to Vercel with
prospect-specific branding (colors, logos, business names).

Key capabilities per spec FR-5:
- Deploy personalized Next.js demo to Vercel with prospect branding
- Generate unique URLs (e.g., acme-dental.leadgen.app)
- Configure environment variables for branding injection
- Track deployment status and manage cleanup
"""

import asyncio
import concurrent.futures
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    current_module = "agents.frontend_deployer_agent"  # This module being loaded

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
DEFAULT_DEMO_FRONTEND_PATH = "src/demo-frontend"
MAX_PROJECT_NAME_LENGTH = 32
DEPLOYMENT_TIMEOUT_SECONDS = 300


@dataclass
class DeploymentConfig:
    """Configuration for a demo site deployment.

    Attributes:
        lead_id: Associated lead ID.
        lead_name: Business name.
        project_name: Vercel project name.
        project_dir: Path to demo frontend source.
        env_vars: Environment variables for branding.
        production: Whether to deploy to production.
    """

    lead_id: Optional[str]
    lead_name: str
    project_name: str
    project_dir: str
    env_vars: dict[str, str] = field(default_factory=dict)
    production: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "lead_id": self.lead_id,
            "lead_name": self.lead_name,
            "project_name": self.project_name,
            "project_dir": self.project_dir,
            "env_vars": self.env_vars,
            "production": self.production,
        }


@dataclass
class DeploymentOutput:
    """Result of a demo site deployment.

    Attributes:
        success: Whether deployment was successful.
        deployment_id: Vercel deployment ID.
        url: Production URL for the demo site.
        preview_url: Preview/staging URL.
        project_name: Vercel project name.
        lead_id: Associated lead ID.
        lead_name: Business name.
        status: Deployment status string.
        created_at: Deployment creation timestamp.
        ready_at: When deployment became ready.
        env_vars_count: Number of env vars set.
        error: Error message if deployment failed.
    """

    success: bool
    deployment_id: Optional[str] = None
    url: Optional[str] = None
    preview_url: Optional[str] = None
    project_name: Optional[str] = None
    lead_id: Optional[str] = None
    lead_name: Optional[str] = None
    status: str = "pending"
    created_at: Optional[str] = None
    ready_at: Optional[str] = None
    env_vars_count: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "deployment_id": self.deployment_id,
            "url": self.url,
            "preview_url": self.preview_url,
            "project_name": self.project_name,
            "lead_id": self.lead_id,
            "lead_name": self.lead_name,
            "status": self.status,
            "created_at": self.created_at,
            "ready_at": self.ready_at,
            "env_vars_count": self.env_vars_count,
            "error": self.error,
        }


def _sanitize_project_name(name: str, lead_id: Optional[str] = None) -> str:
    """Sanitize business name into a valid Vercel project name.

    Args:
        name: Business name to sanitize.
        lead_id: Optional lead ID to append for uniqueness.

    Returns:
        Sanitized project name suitable for Vercel.
    """
    # Convert to lowercase and replace non-alphanumeric with hyphens
    sanitized = "".join(
        c if c.isalnum() or c == "-" else "-"
        for c in name.lower()
    )

    # Remove consecutive hyphens and trim
    while "--" in sanitized:
        sanitized = sanitized.replace("--", "-")
    sanitized = sanitized.strip("-")

    # Limit length, leaving room for lead_id suffix
    if lead_id:
        # Format: {name}-{lead_id[:8]}
        max_name_len = MAX_PROJECT_NAME_LENGTH - 9  # 8 chars + hyphen
        sanitized = sanitized[:max_name_len].strip("-")
        sanitized = f"{sanitized}-{lead_id[:8]}"
    else:
        sanitized = sanitized[:MAX_PROJECT_NAME_LENGTH]

    # Ensure at least some characters
    if not sanitized:
        sanitized = "demo-site"

    return sanitized


def _deploy_demo_site_internal(
    business_name: str,
    lead_id: Optional[str] = None,
    industry: Optional[str] = None,
    primary_color: Optional[str] = None,
    secondary_color: Optional[str] = None,
    accent_color: Optional[str] = None,
    logo_url: Optional[str] = None,
    tagline: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None,
    website: Optional[str] = None,
    twilio_number: Optional[str] = None,
    voice_websocket_url: Optional[str] = None,
    project_dir: Optional[str] = None,
    production: bool = True,
) -> DeploymentOutput:
    """Internal implementation for deploying a demo site.

    Returns DeploymentOutput - the @function_tool version wraps this and returns JSON.
    """
    from integrations.vercel import VercelDeployer, VercelCLINotFoundError
    from utils.branding_injector import BrandingConfig, inject_branding

    logger.info("Deploying demo site for: %s (lead_id=%s)", business_name, lead_id)

    # Determine project directory
    if project_dir:
        project_path = Path(project_dir)
    else:
        # Find demo-frontend relative to leadgen package
        this_file = Path(__file__).resolve()
        leadgen_root = this_file.parent.parent.parent  # src/leadgen -> src
        project_path = leadgen_root / "demo-frontend"

    # Verify project directory exists
    if not project_path.exists():
        logger.error("Demo frontend directory not found: %s", project_path)
        return DeploymentOutput(
            success=False,
            lead_id=lead_id,
            lead_name=business_name,
            status="error",
            error=f"Demo frontend directory not found: {project_path}",
        )

    # Generate project name
    project_name = _sanitize_project_name(business_name, lead_id)

    # Create branding config and generate env vars
    try:
        branding_config = BrandingConfig(
            business_name=business_name,
            primary_color=primary_color,
            secondary_color=secondary_color,
            accent_color=accent_color,
            logo_url=logo_url,
            tagline=tagline,
            industry=industry,
            phone=phone,
            address=address,
            website=website,
            twilio_number=twilio_number,
            voice_websocket_url=voice_websocket_url,
        )

        env_vars = inject_branding(
            branding_config,
            twilio_number=twilio_number,
            voice_websocket_url=voice_websocket_url,
            validate=True,
        )

        # Add lead_id to env vars for tracking
        if lead_id:
            env_vars["NEXT_PUBLIC_LEAD_ID"] = lead_id

        logger.info("Generated %d environment variables for branding", len(env_vars))

    except ValueError as e:
        logger.error("Branding configuration error: %s", e)
        return DeploymentOutput(
            success=False,
            lead_id=lead_id,
            lead_name=business_name,
            project_name=project_name,
            status="error",
            error=f"Branding configuration error: {e}",
        )

    async def _deploy() -> DeploymentOutput:
        """Async deployment implementation."""
        try:
            async with VercelDeployer() as deployer:
                result = await deployer.deploy(
                    project_dir=str(project_path),
                    project_name=project_name,
                    env_vars=env_vars,
                    production=production,
                )

                return DeploymentOutput(
                    success=result.success,
                    deployment_id=result.deployment_id,
                    url=result.url,
                    preview_url=result.preview_url,
                    project_name=result.project_name or project_name,
                    lead_id=lead_id,
                    lead_name=business_name,
                    status=result.status.value,
                    created_at=result.created_at.isoformat() if result.created_at else None,
                    ready_at=result.ready_at.isoformat() if result.ready_at else None,
                    env_vars_count=len(env_vars),
                    error=result.error,
                )

        except VercelCLINotFoundError as e:
            logger.error("Vercel CLI not found: %s", e)
            return DeploymentOutput(
                success=False,
                lead_id=lead_id,
                lead_name=business_name,
                project_name=project_name,
                status="error",
                env_vars_count=len(env_vars),
                error="Vercel CLI not installed. Run: npm install -g vercel",
            )

        except ValueError as e:
            logger.error("Vercel configuration error: %s", e)
            return DeploymentOutput(
                success=False,
                lead_id=lead_id,
                lead_name=business_name,
                project_name=project_name,
                status="error",
                env_vars_count=len(env_vars),
                error=f"Vercel configuration error: {e}",
            )

        except Exception as e:
            logger.error("Deployment error: %s", e)
            return DeploymentOutput(
                success=False,
                lead_id=lead_id,
                lead_name=business_name,
                project_name=project_name,
                status="error",
                env_vars_count=len(env_vars),
                error=str(e),
            )

    # Run async code in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _deploy())
                return future.result()
        else:
            return loop.run_until_complete(_deploy())
    except RuntimeError:
        return asyncio.run(_deploy())


@function_tool
def deploy_demo_site(
    business_name: str,
    lead_id: Optional[str] = None,
    industry: Optional[str] = None,
    primary_color: Optional[str] = None,
    secondary_color: Optional[str] = None,
    logo_url: Optional[str] = None,
    tagline: Optional[str] = None,
    phone: Optional[str] = None,
    twilio_number: Optional[str] = None,
    voice_websocket_url: Optional[str] = None,
    project_dir: Optional[str] = None,
) -> str:
    """Deploy a personalized demo site to Vercel with prospect branding.

    This is the main deployment function that creates a demo site with
    prospect-specific branding including business name, colors, logo,
    and contact information. The site is deployed to a unique Vercel URL.

    The deployment automatically:
    - Generates a unique project name from the business name
    - Injects branding environment variables
    - Uses industry-specific color defaults if not specified
    - Configures Twilio and voice WebSocket connections

    Args:
        business_name: Name of the business for branding.
        lead_id: Optional lead ID for tracking and URL generation.
        industry: Industry category for default colors (dentist, hvac, salon, etc.).
        primary_color: Primary brand color in hex format (e.g., "#2563eb").
        secondary_color: Secondary brand color in hex format.
        logo_url: URL to business logo image.
        tagline: Business tagline or slogan.
        phone: Business phone number for contact display.
        twilio_number: Twilio phone number for click-to-call functionality.
        voice_websocket_url: WebSocket URL for voice agent connection.
        project_dir: Optional custom path to demo frontend project.

    Returns:
        JSON string containing:
        - success: Whether deployment was successful
        - deployment_id: Vercel deployment ID
        - url: Production URL for the demo site (e.g., https://acme-dental-abc123.vercel.app)
        - preview_url: Preview URL
        - project_name: Generated Vercel project name
        - lead_id: Associated lead ID
        - lead_name: Business name
        - status: Deployment status (ready, building, error, etc.)
        - created_at: ISO timestamp when deployment started
        - ready_at: ISO timestamp when deployment became ready
        - env_vars_count: Number of environment variables configured
        - error: Error message if deployment failed

    Example:
        >>> result_json = deploy_demo_site(
        ...     "Acme Dental",
        ...     lead_id="lead_123",
        ...     industry="dentist",
        ...     phone="555-123-4567"
        ... )
        >>> import json; result = json.loads(result_json)
        >>> if result['success']:
        ...     print(f"Demo site deployed: {result['url']}")
    """
    result = _deploy_demo_site_internal(
        business_name=business_name,
        lead_id=lead_id,
        industry=industry,
        primary_color=primary_color,
        secondary_color=secondary_color,
        logo_url=logo_url,
        tagline=tagline,
        phone=phone,
        twilio_number=twilio_number,
        voice_websocket_url=voice_websocket_url,
        project_dir=project_dir,
        production=True,
    )

    return json.dumps(result.to_dict())


def _deploy_from_lead_data_internal(
    lead_data: dict[str, Any],
    twilio_number: Optional[str] = None,
    voice_websocket_url: Optional[str] = None,
    project_dir: Optional[str] = None,
) -> DeploymentOutput:
    """Internal implementation for deploying from lead data.

    Returns DeploymentOutput - the @function_tool version wraps this and returns JSON.
    """
    from utils.branding_injector import branding_config_from_lead, inject_branding
    from integrations.vercel import VercelDeployer, VercelCLINotFoundError

    # Extract required fields
    business_name = lead_data.get("name", "Demo Business")
    lead_id = lead_data.get("id") or lead_data.get("lead_id")

    logger.info(
        "Deploying demo site from lead data: %s (lead_id=%s)",
        business_name,
        lead_id,
    )

    # Determine project directory
    if project_dir:
        project_path = Path(project_dir)
    else:
        this_file = Path(__file__).resolve()
        leadgen_root = this_file.parent.parent.parent
        project_path = leadgen_root / "demo-frontend"

    if not project_path.exists():
        return DeploymentOutput(
            success=False,
            lead_id=lead_id,
            lead_name=business_name,
            status="error",
            error=f"Demo frontend directory not found: {project_path}",
        )

    # Generate project name
    project_name = _sanitize_project_name(business_name, lead_id)

    try:
        # Create branding config from lead data
        branding_config = branding_config_from_lead(lead_data)

        # Apply overrides
        if twilio_number:
            branding_config.twilio_number = twilio_number
        if voice_websocket_url:
            branding_config.voice_websocket_url = voice_websocket_url

        # Generate environment variables
        env_vars = inject_branding(branding_config, validate=True)

        # Add lead_id to env vars
        if lead_id:
            env_vars["NEXT_PUBLIC_LEAD_ID"] = str(lead_id)

        logger.info("Generated %d environment variables from lead data", len(env_vars))

    except ValueError as e:
        logger.error("Branding configuration error: %s", e)
        return DeploymentOutput(
            success=False,
            lead_id=lead_id,
            lead_name=business_name,
            project_name=project_name,
            status="error",
            error=f"Branding configuration error: {e}",
        )

    async def _deploy() -> DeploymentOutput:
        """Async deployment implementation."""
        try:
            async with VercelDeployer() as deployer:
                result = await deployer.deploy(
                    project_dir=str(project_path),
                    project_name=project_name,
                    env_vars=env_vars,
                    production=True,
                )

                return DeploymentOutput(
                    success=result.success,
                    deployment_id=result.deployment_id,
                    url=result.url,
                    preview_url=result.preview_url,
                    project_name=result.project_name or project_name,
                    lead_id=lead_id,
                    lead_name=business_name,
                    status=result.status.value,
                    created_at=result.created_at.isoformat() if result.created_at else None,
                    ready_at=result.ready_at.isoformat() if result.ready_at else None,
                    env_vars_count=len(env_vars),
                    error=result.error,
                )

        except VercelCLINotFoundError:
            return DeploymentOutput(
                success=False,
                lead_id=lead_id,
                lead_name=business_name,
                project_name=project_name,
                status="error",
                env_vars_count=len(env_vars),
                error="Vercel CLI not installed. Run: npm install -g vercel",
            )

        except ValueError as e:
            return DeploymentOutput(
                success=False,
                lead_id=lead_id,
                lead_name=business_name,
                project_name=project_name,
                status="error",
                env_vars_count=len(env_vars),
                error=f"Vercel configuration error: {e}",
            )

        except Exception as e:
            logger.error("Deployment error: %s", e)
            return DeploymentOutput(
                success=False,
                lead_id=lead_id,
                lead_name=business_name,
                project_name=project_name,
                status="error",
                env_vars_count=len(env_vars),
                error=str(e),
            )

    # Run async code in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _deploy())
                return future.result()
        else:
            return loop.run_until_complete(_deploy())
    except RuntimeError:
        return asyncio.run(_deploy())


@function_tool
def deploy_from_lead_data(
    lead_data_json: str,
    twilio_number: Optional[str] = None,
    voice_websocket_url: Optional[str] = None,
    project_dir: Optional[str] = None,
) -> str:
    """Deploy a demo site using lead data from the research pipeline.

    This is a convenience function that takes lead data (typically from
    the Research Agent's dossier) and deploys a fully branded demo site.
    It automatically extracts branding information from the lead data.

    The function expects lead data with these fields:
    - name (required): Business name
    - id or lead_id: Lead identifier
    - industry: Business industry for color defaults
    - phone: Contact phone number
    - address: Business address
    - website: Business website URL
    - logo_url: Logo image URL (if extracted)
    - primary_color: Brand color (if extracted)
    - tagline: Business tagline

    Args:
        lead_data_json: JSON string containing lead data.
        twilio_number: Override Twilio number for voice demos.
        voice_websocket_url: Override WebSocket URL for voice agent.
        project_dir: Optional custom path to demo frontend project.

    Returns:
        JSON string containing deployment result (same format as deploy_demo_site).

    Example:
        >>> lead_data = json.dumps({
        ...     "name": "Acme Dental",
        ...     "id": "lead_123",
        ...     "industry": "dentist",
        ...     "phone": "555-123-4567",
        ...     "website": "https://acme-dental.com"
        ... })
        >>> result_json = deploy_from_lead_data(lead_data)
        >>> import json; result = json.loads(result_json)
        >>> print(f"Deployed: {result['url']}")
    """
    try:
        lead_data = json.loads(lead_data_json)
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": f"Invalid lead_data_json: {e}",
            "status": "error",
        })

    result = _deploy_from_lead_data_internal(
        lead_data=lead_data,
        twilio_number=twilio_number,
        voice_websocket_url=voice_websocket_url,
        project_dir=project_dir,
    )

    return json.dumps(result.to_dict())


def _get_deployment_status_internal(deployment_id: str) -> dict[str, Any]:
    """Internal implementation for getting deployment status.

    Returns a dict - the @function_tool version wraps this and returns JSON.
    """
    from integrations.vercel import VercelDeployer

    logger.info("Getting deployment status: %s", deployment_id)

    async def _get_status() -> dict[str, Any]:
        """Async implementation."""
        try:
            async with VercelDeployer() as deployer:
                deployment = await deployer.get_deployment(deployment_id)

                if deployment is None:
                    return {
                        "found": False,
                        "deployment_id": deployment_id,
                        "error": "Deployment not found",
                    }

                return {
                    "found": True,
                    "deployment_id": deployment.deployment_id,
                    "url": deployment.url,
                    "state": deployment.state,
                    "created_at": deployment.created_at.isoformat() if deployment.created_at else None,
                    "ready_at": deployment.ready_at.isoformat() if deployment.ready_at else None,
                    "target": deployment.target,
                    "alias": deployment.alias,
                    "error": None,
                }

        except ValueError as e:
            return {
                "found": False,
                "deployment_id": deployment_id,
                "error": f"Vercel configuration error: {e}",
            }

        except Exception as e:
            logger.error("Error getting deployment status: %s", e)
            return {
                "found": False,
                "deployment_id": deployment_id,
                "error": str(e),
            }

    # Run async code in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_status())
                return future.result()
        else:
            return loop.run_until_complete(_get_status())
    except RuntimeError:
        return asyncio.run(_get_status())


@function_tool
def get_deployment_status(deployment_id: str) -> str:
    """Get the current status of a Vercel deployment.

    Use this to check if a deployment has completed successfully,
    is still building, or has encountered an error.

    Args:
        deployment_id: Vercel deployment ID (from deploy_demo_site result).

    Returns:
        JSON string containing:
        - found: Whether the deployment was found
        - deployment_id: The deployment ID
        - url: Deployment URL
        - state: Current state (READY, BUILDING, ERROR, etc.)
        - created_at: Creation timestamp
        - ready_at: Ready timestamp (if applicable)
        - target: Deployment target (production/preview)
        - alias: List of domain aliases
        - error: Error message if lookup failed

    Example:
        >>> result_json = get_deployment_status("dpl_abc123...")
        >>> import json; result = json.loads(result_json)
        >>> if result['found'] and result['state'] == 'READY':
        ...     print(f"Deployment ready at: {result['url']}")
    """
    result = _get_deployment_status_internal(deployment_id)
    return json.dumps(result)


def _delete_deployment_internal(
    deployment_id: Optional[str] = None,
    project_name: Optional[str] = None,
) -> dict[str, Any]:
    """Internal implementation for deleting deployment or project.

    Returns a dict - the @function_tool version wraps this and returns JSON.
    """
    from integrations.vercel import VercelDeployer

    logger.info(
        "Deleting: deployment_id=%s, project_name=%s",
        deployment_id,
        project_name,
    )

    async def _delete() -> dict[str, Any]:
        """Async implementation."""
        try:
            async with VercelDeployer() as deployer:
                results = {
                    "deployment_deleted": False,
                    "project_deleted": False,
                    "errors": [],
                }

                # Delete specific deployment
                if deployment_id:
                    try:
                        deleted = await deployer.delete_deployment(deployment_id)
                        results["deployment_deleted"] = deleted
                        if not deleted:
                            results["errors"].append(f"Failed to delete deployment: {deployment_id}")
                    except Exception as e:
                        results["errors"].append(f"Deployment deletion error: {e}")

                # Delete entire project
                if project_name:
                    try:
                        deleted = await deployer.delete_project(project_name)
                        results["project_deleted"] = deleted
                        if not deleted:
                            results["errors"].append(f"Failed to delete project: {project_name}")
                    except Exception as e:
                        results["errors"].append(f"Project deletion error: {e}")

                results["success"] = (
                    (not deployment_id or results["deployment_deleted"]) and
                    (not project_name or results["project_deleted"])
                )

                return results

        except ValueError as e:
            return {
                "success": False,
                "deployment_deleted": False,
                "project_deleted": False,
                "errors": [f"Vercel configuration error: {e}"],
            }

        except Exception as e:
            logger.error("Error during deletion: %s", e)
            return {
                "success": False,
                "deployment_deleted": False,
                "project_deleted": False,
                "errors": [str(e)],
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
def delete_demo_deployment(
    deployment_id: Optional[str] = None,
    project_name: Optional[str] = None,
) -> str:
    """Delete a demo deployment or entire project from Vercel.

    Use this to clean up demo sites that are no longer needed. You can
    delete a specific deployment, an entire project, or both.

    WARNING: Deleting a project removes ALL deployments and domain
    configurations for that project.

    Args:
        deployment_id: Optional Vercel deployment ID to delete.
        project_name: Optional Vercel project name to delete entirely.

    Returns:
        JSON string containing:
        - success: Whether all requested deletions succeeded
        - deployment_deleted: Whether deployment was deleted
        - project_deleted: Whether project was deleted
        - errors: List of any error messages

    Example:
        >>> # Delete just a deployment
        >>> result = delete_demo_deployment(deployment_id="dpl_abc123")
        >>>
        >>> # Delete entire project
        >>> result = delete_demo_deployment(project_name="acme-dental-abc123")
    """
    if not deployment_id and not project_name:
        return json.dumps({
            "success": False,
            "deployment_deleted": False,
            "project_deleted": False,
            "errors": ["Must provide either deployment_id or project_name"],
        })

    result = _delete_deployment_internal(
        deployment_id=deployment_id,
        project_name=project_name,
    )
    return json.dumps(result)


def _list_deployments_internal(
    project_name: Optional[str] = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Internal implementation for listing deployments.

    Returns a dict - the @function_tool version wraps this and returns JSON.
    """
    from integrations.vercel import VercelDeployer

    logger.info("Listing deployments: project=%s, limit=%d", project_name, limit)

    async def _list() -> dict[str, Any]:
        """Async implementation."""
        try:
            async with VercelDeployer() as deployer:
                deployments = await deployer.list_deployments(
                    project_name=project_name,
                    limit=limit,
                )

                return {
                    "success": True,
                    "count": len(deployments),
                    "deployments": [
                        {
                            "deployment_id": d.deployment_id,
                            "url": d.url,
                            "state": d.state,
                            "created_at": d.created_at.isoformat() if d.created_at else None,
                            "target": d.target,
                        }
                        for d in deployments
                    ],
                    "error": None,
                }

        except ValueError as e:
            return {
                "success": False,
                "count": 0,
                "deployments": [],
                "error": f"Vercel configuration error: {e}",
            }

        except Exception as e:
            logger.error("Error listing deployments: %s", e)
            return {
                "success": False,
                "count": 0,
                "deployments": [],
                "error": str(e),
            }

    # Run async code in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _list())
                return future.result()
        else:
            return loop.run_until_complete(_list())
    except RuntimeError:
        return asyncio.run(_list())


@function_tool
def list_demo_deployments(
    project_name: Optional[str] = None,
    limit: int = 10,
) -> str:
    """List recent demo site deployments.

    Get a list of recent deployments, optionally filtered by project name.
    Useful for auditing deployed demo sites and cleaning up old deployments.

    Args:
        project_name: Optional project name to filter by.
        limit: Maximum number of deployments to return. Defaults to 10.

    Returns:
        JSON string containing:
        - success: Whether listing was successful
        - count: Number of deployments returned
        - deployments: List of deployment objects with:
            - deployment_id: Deployment ID
            - url: Deployment URL
            - state: Current state
            - created_at: Creation timestamp
            - target: Deployment target
        - error: Error message if listing failed

    Example:
        >>> result_json = list_demo_deployments(project_name="acme-dental-abc123")
        >>> import json; result = json.loads(result_json)
        >>> for deployment in result['deployments']:
        ...     print(f"{deployment['deployment_id']}: {deployment['state']}")
    """
    result = _list_deployments_internal(
        project_name=project_name,
        limit=limit,
    )
    return json.dumps(result)


# Agent instructions defining behavior and constraints
FRONTEND_DEPLOYER_AGENT_INSTRUCTIONS = """You are a Frontend Deployer Agent specialized in deploying personalized demo sites to Vercel.

Your primary task is to deploy demo sites with prospect-specific branding that showcase AI voice assistant capabilities.

## Your Deployment Process

When deploying a demo site, follow these steps:

1. **Deploy Demo Site**
   - Use `deploy_demo_site` to deploy with explicit branding parameters
   - OR use `deploy_from_lead_data` to deploy from research pipeline output
   - The deployment automatically configures all environment variables

2. **Verify Deployment**
   - Use `get_deployment_status` to confirm the deployment completed successfully
   - The demo site should load in <2 seconds per spec requirement

3. **Record Deployment**
   - Capture the deployment URL for email campaigns
   - Store the deployment_id and project_name for cleanup later

## Branding Configuration

The demo sites support these branding options:
- Business name and tagline
- Primary, secondary, and accent colors (hex format)
- Logo URL
- Contact information (phone, address, website)
- Twilio number for click-to-call
- Voice WebSocket URL for agent connection

If colors aren't specified, industry-specific defaults are used:
- Dentist: Cyan tones (#0891b2)
- HVAC: Orange tones (#ea580c)
- Salon: Pink tones (#db2777)
- Auto: Red tones (#dc2626)
- Medical: Blue tones (#2563eb)
- Legal: Indigo tones (#4f46e5)

## Deployment URLs

Each deployment gets a unique URL based on the business name:
- Format: {sanitized-name}-{lead_id}.vercel.app
- Example: acme-dental-abc12345.vercel.app

## Cleanup

Use `delete_demo_deployment` to clean up demo sites when:
- A lead is no longer active
- The demo period has expired
- The site needs to be redeployed with updates

Use `list_demo_deployments` to audit existing deployments.

## Error Handling

Common issues to handle:
- Vercel CLI not installed: Instruct user to run `npm install -g vercel`
- VERCEL_TOKEN not set: Deployment requires authentication
- Invalid branding config: Colors must be valid hex format
- Project directory not found: Ensure demo-frontend exists

## Important Notes

- Deployments take 1-2 minutes to complete building
- Environment variables are set during deployment
- Each prospect should have their own project for isolation
- Vercel CLI must be installed and VERCEL_TOKEN env var must be set
- Demo frontend directory must exist at src/demo-frontend

## Output Format

Always report:
- Deployment success/failure status
- The deployment URL (if successful)
- The project name for tracking
- Any errors encountered
"""

# Create the frontend deployer agent instance
frontend_deployer_agent = Agent(
    name="Frontend Deployer Agent",
    instructions=FRONTEND_DEPLOYER_AGENT_INSTRUCTIONS,
    tools=[
        deploy_demo_site,
        deploy_from_lead_data,
        get_deployment_status,
        delete_demo_deployment,
        list_demo_deployments,
    ],
)
