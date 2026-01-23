"""Vercel CLI deployment wrapper for automated demo site deployments.

This module provides a wrapper for Vercel CLI to automate demo site deployments
with prospect-specific branding and environment variables.

Features:
- Automated deployment via Vercel CLI
- Environment variable injection for branding
- Deployment status tracking
- Project creation and management
- Domain alias configuration
- Deployment cleanup

Usage:
    >>> deployer = VercelDeployer()
    >>> result = await deployer.deploy(
    ...     project_dir="/path/to/demo-frontend",
    ...     project_name="acme-dental-demo",
    ...     env_vars={"NEXT_PUBLIC_BUSINESS_NAME": "Acme Dental"},
    ... )
    >>> print(result.url)
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes for deployments
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5


class DeploymentStatus(str, Enum):
    """Deployment status values."""

    PENDING = "pending"
    BUILDING = "building"
    READY = "ready"
    ERROR = "error"
    CANCELED = "canceled"
    QUEUED = "queued"


class VercelError(Exception):
    """Base exception for Vercel errors."""

    pass


class VercelAuthError(VercelError):
    """Raised when Vercel authentication fails."""

    pass


class VercelNotFoundError(VercelError):
    """Raised when a Vercel resource is not found."""

    pass


class VercelDeploymentError(VercelError):
    """Raised when a deployment fails."""

    def __init__(self, message: str, logs: Optional[str] = None):
        super().__init__(message)
        self.logs = logs


class VercelProjectError(VercelError):
    """Raised when project operations fail."""

    pass


class VercelCLINotFoundError(VercelError):
    """Raised when Vercel CLI is not installed."""

    pass


@dataclass
class DeploymentResult:
    """Result of a Vercel deployment.

    Attributes:
        deployment_id: Unique Vercel deployment ID.
        url: Production URL for the deployment.
        preview_url: Preview/staging URL.
        project_name: Name of the Vercel project.
        status: Current deployment status.
        created_at: Timestamp when deployment was created.
        ready_at: Timestamp when deployment became ready.
        success: Whether deployment succeeded.
        error: Error message if deployment failed.
        build_logs: Build output logs.
    """

    deployment_id: Optional[str] = None
    url: Optional[str] = None
    preview_url: Optional[str] = None
    project_name: Optional[str] = None
    status: DeploymentStatus = DeploymentStatus.PENDING
    created_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    success: bool = False
    error: Optional[str] = None
    build_logs: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "deployment_id": self.deployment_id,
            "url": self.url,
            "preview_url": self.preview_url,
            "project_name": self.project_name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "ready_at": self.ready_at.isoformat() if self.ready_at else None,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class ProjectInfo:
    """Information about a Vercel project.

    Attributes:
        project_id: Unique Vercel project ID.
        name: Project name.
        framework: Detected framework (e.g., "nextjs").
        created_at: Project creation timestamp.
        updated_at: Last update timestamp.
        domains: List of domains configured.
        env_vars: List of environment variable names.
    """

    project_id: Optional[str] = None
    name: Optional[str] = None
    framework: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domains: list[str] = field(default_factory=list)
    env_vars: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "project_id": self.project_id,
            "name": self.name,
            "framework": self.framework,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "domains": self.domains,
            "env_vars": self.env_vars,
        }


@dataclass
class DeploymentInfo:
    """Information about a specific deployment.

    Attributes:
        deployment_id: Unique deployment ID.
        url: Deployment URL.
        state: Current deployment state.
        created_at: Creation timestamp.
        ready_at: Ready timestamp.
        target: Deployment target (production/preview).
        alias: List of domain aliases.
    """

    deployment_id: Optional[str] = None
    url: Optional[str] = None
    state: Optional[str] = None
    created_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    target: Optional[str] = None
    alias: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "deployment_id": self.deployment_id,
            "url": self.url,
            "state": self.state,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "ready_at": self.ready_at.isoformat() if self.ready_at else None,
            "target": self.target,
            "alias": self.alias,
        }


class VercelDeployer:
    """Wrapper for Vercel CLI to automate demo site deployments.

    Provides methods for deploying Next.js projects to Vercel with
    environment variable injection for prospect-specific branding.

    Attributes:
        token: Vercel API token.
        team_id: Optional Vercel team ID.
        scope: Optional scope (team slug or ID).

    Example:
        >>> deployer = VercelDeployer()
        >>> result = await deployer.deploy(
        ...     project_dir="./demo-frontend",
        ...     project_name="acme-dental-demo",
        ...     env_vars={
        ...         "NEXT_PUBLIC_BUSINESS_NAME": "Acme Dental",
        ...         "NEXT_PUBLIC_PRIMARY_COLOR": "#0066cc",
        ...     },
        ... )
        >>> print(f"Deployed to: {result.url}")
    """

    def __init__(
        self,
        token: Optional[str] = None,
        team_id: Optional[str] = None,
        scope: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize Vercel deployer.

        Args:
            token: Vercel API token. Defaults to VERCEL_TOKEN env var.
            team_id: Vercel team ID. Defaults to VERCEL_TEAM_ID env var.
            scope: Vercel scope (team slug). Defaults to VERCEL_SCOPE env var.
            timeout_seconds: CLI command timeout. Defaults to 300 seconds.

        Raises:
            ValueError: If token is not provided.
            VercelCLINotFoundError: If Vercel CLI is not installed.
        """
        self.token = token or os.environ.get("VERCEL_TOKEN")
        if not self.token:
            raise ValueError(
                "Vercel token required. Set VERCEL_TOKEN environment "
                "variable or pass token parameter."
            )

        self.team_id = team_id or os.environ.get("VERCEL_TEAM_ID")
        self.scope = scope or os.environ.get("VERCEL_SCOPE")
        self.timeout_seconds = timeout_seconds

        # Verify CLI is installed
        self._verify_cli_installed()

        logger.info(
            "VercelDeployer initialized (team_id=%s, scope=%s)",
            self.team_id or "not set",
            self.scope or "not set",
        )

    def _verify_cli_installed(self) -> None:
        """Verify that Vercel CLI is installed.

        Raises:
            VercelCLINotFoundError: If CLI is not found.
        """
        if shutil.which("vercel") is None:
            raise VercelCLINotFoundError(
                "Vercel CLI not found. Install with: npm install -g vercel"
            )

    def _build_base_args(self) -> list[str]:
        """Build base CLI arguments with auth and scope.

        Returns:
            List of base CLI arguments.
        """
        args = ["vercel", "--token", self.token]

        if self.scope:
            args.extend(["--scope", self.scope])
        elif self.team_id:
            args.extend(["--scope", self.team_id])

        return args

    async def _run_cli(
        self,
        args: list[str],
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> tuple[int, str, str]:
        """Run Vercel CLI command asynchronously.

        Args:
            args: CLI arguments.
            cwd: Working directory for the command.
            timeout: Command timeout in seconds.

        Returns:
            Tuple of (return_code, stdout, stderr).

        Raises:
            VercelAuthError: If authentication fails.
            VercelError: If CLI command fails.
        """
        timeout = timeout or self.timeout_seconds

        logger.debug("Running Vercel CLI: %s", " ".join(args[:5]) + "...")

        loop = asyncio.get_event_loop()

        def run_subprocess():
            try:
                result = subprocess.run(
                    args,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env={**os.environ, "VERCEL_TOKEN": self.token},
                )
                return result.returncode, result.stdout, result.stderr
            except subprocess.TimeoutExpired as e:
                return -1, "", f"Command timed out after {timeout} seconds"
            except Exception as e:
                return -1, "", str(e)

        return_code, stdout, stderr = await loop.run_in_executor(None, run_subprocess)

        # Check for auth errors
        if "not_authorized" in stderr.lower() or "unauthorized" in stderr.lower():
            raise VercelAuthError(f"Authentication failed: {stderr}")

        return return_code, stdout, stderr

    async def deploy(
        self,
        project_dir: str,
        project_name: Optional[str] = None,
        env_vars: Optional[dict[str, str]] = None,
        production: bool = True,
        force: bool = False,
        build_env: Optional[dict[str, str]] = None,
        regions: Optional[list[str]] = None,
        prebuilt: bool = False,
    ) -> DeploymentResult:
        """Deploy a project to Vercel.

        Args:
            project_dir: Path to the project directory.
            project_name: Name for the Vercel project.
            env_vars: Environment variables to set for the deployment.
            production: Deploy to production (vs preview). Defaults to True.
            force: Force deployment even if no changes. Defaults to False.
            build_env: Environment variables only for the build.
            regions: List of regions for deployment.
            prebuilt: Use prebuilt output. Defaults to False.

        Returns:
            DeploymentResult with deployment details.

        Raises:
            VercelDeploymentError: If deployment fails.
        """
        logger.info(
            "Deploying project: dir=%s, name=%s, production=%s",
            project_dir,
            project_name,
            production,
        )

        # Validate project directory
        project_path = Path(project_dir)
        if not project_path.exists():
            return DeploymentResult(
                status=DeploymentStatus.ERROR,
                error=f"Project directory not found: {project_dir}",
            )

        # Build CLI arguments
        args = self._build_base_args()

        if project_name:
            args.extend(["--name", project_name])

        if production:
            args.append("--prod")

        if force:
            args.append("--force")

        if prebuilt:
            args.append("--prebuilt")

        # Add regions
        if regions:
            for region in regions:
                args.extend(["--regions", region])

        # Add environment variables
        if env_vars:
            for key, value in env_vars.items():
                args.extend(["--env", f"{key}={value}"])

        # Add build environment variables
        if build_env:
            for key, value in build_env.items():
                args.extend(["--build-env", f"{key}={value}"])

        # Request JSON output
        args.extend(["--yes", "--json"])

        # Add project directory
        args.append(str(project_path.absolute()))

        created_at = datetime.now(timezone.utc)

        # Execute deployment with retries
        for attempt in range(MAX_RETRIES):
            return_code, stdout, stderr = await self._run_cli(args)

            if return_code == 0:
                break

            if attempt < MAX_RETRIES - 1:
                logger.warning(
                    "Deployment attempt %d failed, retrying in %d seconds: %s",
                    attempt + 1,
                    RETRY_DELAY_SECONDS,
                    stderr,
                )
                await asyncio.sleep(RETRY_DELAY_SECONDS)
        else:
            # All retries failed
            return DeploymentResult(
                project_name=project_name,
                status=DeploymentStatus.ERROR,
                created_at=created_at,
                error=f"Deployment failed after {MAX_RETRIES} attempts: {stderr}",
                build_logs=stdout,
            )

        # Parse deployment output
        try:
            # Vercel CLI outputs JSON lines, get the last complete JSON object
            deployment_data = None
            for line in stdout.strip().split("\n"):
                line = line.strip()
                if line.startswith("{"):
                    try:
                        deployment_data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

            if not deployment_data:
                # Try to extract URL from plain text output
                url = stdout.strip().split("\n")[-1].strip()
                if url.startswith("http"):
                    return DeploymentResult(
                        url=url,
                        preview_url=url,
                        project_name=project_name,
                        status=DeploymentStatus.READY,
                        created_at=created_at,
                        ready_at=datetime.now(timezone.utc),
                        success=True,
                    )
                raise ValueError("Could not parse deployment output")

            # Extract deployment info from JSON
            deployment_id = deployment_data.get("id")
            url = deployment_data.get("url")
            if url and not url.startswith("http"):
                url = f"https://{url}"

            alias_urls = deployment_data.get("alias", [])
            preview_url = url
            if alias_urls:
                # Production URL is usually in alias
                url = f"https://{alias_urls[0]}" if alias_urls[0] else url

            state = deployment_data.get("readyState", "READY")
            status = self._parse_status(state)

            result = DeploymentResult(
                deployment_id=deployment_id,
                url=url,
                preview_url=preview_url,
                project_name=deployment_data.get("name", project_name),
                status=status,
                created_at=created_at,
                ready_at=datetime.now(timezone.utc) if status == DeploymentStatus.READY else None,
                success=status == DeploymentStatus.READY,
                build_logs=stdout,
            )

            logger.info(
                "Deployment complete: id=%s, url=%s, status=%s",
                deployment_id,
                url,
                status.value,
            )

            return result

        except Exception as e:
            logger.error("Failed to parse deployment output: %s", str(e))
            return DeploymentResult(
                project_name=project_name,
                status=DeploymentStatus.ERROR,
                created_at=created_at,
                error=f"Failed to parse deployment output: {str(e)}",
                build_logs=stdout,
            )

    def _parse_status(self, state: str) -> DeploymentStatus:
        """Parse Vercel state to DeploymentStatus.

        Args:
            state: Vercel deployment state string.

        Returns:
            DeploymentStatus enum value.
        """
        state_upper = state.upper()
        if state_upper in ["READY", "SUCCEEDED"]:
            return DeploymentStatus.READY
        elif state_upper in ["BUILDING", "INITIALIZING"]:
            return DeploymentStatus.BUILDING
        elif state_upper in ["ERROR", "FAILED"]:
            return DeploymentStatus.ERROR
        elif state_upper == "CANCELED":
            return DeploymentStatus.CANCELED
        elif state_upper == "QUEUED":
            return DeploymentStatus.QUEUED
        else:
            return DeploymentStatus.PENDING

    async def get_deployment(self, deployment_id: str) -> Optional[DeploymentInfo]:
        """Get information about a specific deployment.

        Args:
            deployment_id: Vercel deployment ID.

        Returns:
            DeploymentInfo if found, None otherwise.
        """
        logger.info("Getting deployment info: %s", deployment_id)

        args = self._build_base_args()
        args.extend(["inspect", deployment_id, "--json"])

        return_code, stdout, stderr = await self._run_cli(args)

        if return_code != 0:
            if "not found" in stderr.lower():
                return None
            logger.error("Failed to get deployment: %s", stderr)
            return None

        try:
            data = json.loads(stdout)

            created_at = None
            if data.get("createdAt"):
                created_at = datetime.fromtimestamp(
                    data["createdAt"] / 1000, tz=timezone.utc
                )

            ready_at = None
            if data.get("ready"):
                ready_at = datetime.fromtimestamp(
                    data["ready"] / 1000, tz=timezone.utc
                )

            return DeploymentInfo(
                deployment_id=data.get("id"),
                url=f"https://{data.get('url', '')}" if data.get("url") else None,
                state=data.get("readyState"),
                created_at=created_at,
                ready_at=ready_at,
                target=data.get("target"),
                alias=data.get("alias", []),
            )

        except json.JSONDecodeError as e:
            logger.error("Failed to parse deployment info: %s", str(e))
            return None

    async def get_project(self, project_name: str) -> Optional[ProjectInfo]:
        """Get information about a Vercel project.

        Args:
            project_name: Name of the Vercel project.

        Returns:
            ProjectInfo if found, None otherwise.
        """
        logger.info("Getting project info: %s", project_name)

        args = self._build_base_args()
        args.extend(["project", "ls", "--json"])

        return_code, stdout, stderr = await self._run_cli(args)

        if return_code != 0:
            logger.error("Failed to list projects: %s", stderr)
            return None

        try:
            projects = json.loads(stdout)

            for project in projects:
                if project.get("name") == project_name:
                    created_at = None
                    if project.get("createdAt"):
                        created_at = datetime.fromtimestamp(
                            project["createdAt"] / 1000, tz=timezone.utc
                        )

                    updated_at = None
                    if project.get("updatedAt"):
                        updated_at = datetime.fromtimestamp(
                            project["updatedAt"] / 1000, tz=timezone.utc
                        )

                    return ProjectInfo(
                        project_id=project.get("id"),
                        name=project.get("name"),
                        framework=project.get("framework"),
                        created_at=created_at,
                        updated_at=updated_at,
                    )

            return None

        except json.JSONDecodeError as e:
            logger.error("Failed to parse projects list: %s", str(e))
            return None

    async def set_env_var(
        self,
        project_name: str,
        key: str,
        value: str,
        target: str = "production",
    ) -> bool:
        """Set an environment variable for a project.

        Args:
            project_name: Name of the Vercel project.
            key: Environment variable name.
            value: Environment variable value.
            target: Target environment (production, preview, development).

        Returns:
            True if successful, False otherwise.
        """
        logger.info("Setting env var %s for project %s", key, project_name)

        args = self._build_base_args()
        args.extend([
            "env", "add", key, target,
            "--project", project_name,
        ])

        # Pass value via stdin
        loop = asyncio.get_event_loop()

        def run_subprocess():
            try:
                result = subprocess.run(
                    args,
                    input=value,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    env={**os.environ, "VERCEL_TOKEN": self.token},
                )
                return result.returncode, result.stdout, result.stderr
            except Exception as e:
                return -1, "", str(e)

        return_code, stdout, stderr = await loop.run_in_executor(None, run_subprocess)

        if return_code != 0:
            logger.error("Failed to set env var: %s", stderr)
            return False

        logger.info("Environment variable %s set successfully", key)
        return True

    async def remove_env_var(
        self,
        project_name: str,
        key: str,
        target: str = "production",
    ) -> bool:
        """Remove an environment variable from a project.

        Args:
            project_name: Name of the Vercel project.
            key: Environment variable name.
            target: Target environment.

        Returns:
            True if successful, False otherwise.
        """
        logger.info("Removing env var %s from project %s", key, project_name)

        args = self._build_base_args()
        args.extend([
            "env", "rm", key, target,
            "--project", project_name,
            "--yes",
        ])

        return_code, stdout, stderr = await self._run_cli(args)

        if return_code != 0:
            if "not found" in stderr.lower():
                logger.info("Environment variable %s not found", key)
                return True  # Consider it removed
            logger.error("Failed to remove env var: %s", stderr)
            return False

        logger.info("Environment variable %s removed successfully", key)
        return True

    async def add_domain(
        self,
        project_name: str,
        domain: str,
    ) -> bool:
        """Add a domain alias to a project.

        Args:
            project_name: Name of the Vercel project.
            domain: Domain name to add.

        Returns:
            True if successful, False otherwise.
        """
        logger.info("Adding domain %s to project %s", domain, project_name)

        args = self._build_base_args()
        args.extend([
            "domains", "add", domain,
            "--project", project_name,
        ])

        return_code, stdout, stderr = await self._run_cli(args)

        if return_code != 0:
            logger.error("Failed to add domain: %s", stderr)
            return False

        logger.info("Domain %s added successfully", domain)
        return True

    async def remove_domain(
        self,
        project_name: str,
        domain: str,
    ) -> bool:
        """Remove a domain alias from a project.

        Args:
            project_name: Name of the Vercel project.
            domain: Domain name to remove.

        Returns:
            True if successful, False otherwise.
        """
        logger.info("Removing domain %s from project %s", domain, project_name)

        args = self._build_base_args()
        args.extend([
            "domains", "rm", domain,
            "--yes",
        ])

        return_code, stdout, stderr = await self._run_cli(args)

        if return_code != 0:
            if "not found" in stderr.lower():
                return True  # Consider it removed
            logger.error("Failed to remove domain: %s", stderr)
            return False

        logger.info("Domain %s removed successfully", domain)
        return True

    async def delete_deployment(self, deployment_id: str) -> bool:
        """Delete a deployment.

        Args:
            deployment_id: Vercel deployment ID.

        Returns:
            True if successful, False otherwise.
        """
        logger.info("Deleting deployment: %s", deployment_id)

        args = self._build_base_args()
        args.extend(["remove", deployment_id, "--yes"])

        return_code, stdout, stderr = await self._run_cli(args)

        if return_code != 0:
            if "not found" in stderr.lower():
                return True  # Already deleted
            logger.error("Failed to delete deployment: %s", stderr)
            return False

        logger.info("Deployment %s deleted successfully", deployment_id)
        return True

    async def delete_project(self, project_name: str) -> bool:
        """Delete a Vercel project.

        WARNING: This deletes all deployments and domains for the project.

        Args:
            project_name: Name of the project to delete.

        Returns:
            True if successful, False otherwise.
        """
        logger.info("Deleting project: %s", project_name)

        args = self._build_base_args()
        args.extend(["project", "rm", project_name, "--yes"])

        return_code, stdout, stderr = await self._run_cli(args)

        if return_code != 0:
            if "not found" in stderr.lower():
                return True  # Already deleted
            logger.error("Failed to delete project: %s", stderr)
            return False

        logger.info("Project %s deleted successfully", project_name)
        return True

    async def list_deployments(
        self,
        project_name: Optional[str] = None,
        limit: int = 20,
    ) -> list[DeploymentInfo]:
        """List recent deployments.

        Args:
            project_name: Filter by project name.
            limit: Maximum number of deployments to return.

        Returns:
            List of DeploymentInfo objects.
        """
        logger.info("Listing deployments (project=%s, limit=%d)", project_name, limit)

        args = self._build_base_args()
        args.extend(["list", "--json"])

        if project_name:
            args.extend(["--project", project_name])

        return_code, stdout, stderr = await self._run_cli(args)

        if return_code != 0:
            logger.error("Failed to list deployments: %s", stderr)
            return []

        try:
            deployments_data = json.loads(stdout)
            deployments = []

            for dep in deployments_data[:limit]:
                created_at = None
                if dep.get("createdAt"):
                    created_at = datetime.fromtimestamp(
                        dep["createdAt"] / 1000, tz=timezone.utc
                    )

                deployments.append(
                    DeploymentInfo(
                        deployment_id=dep.get("uid"),
                        url=f"https://{dep.get('url', '')}" if dep.get("url") else None,
                        state=dep.get("state"),
                        created_at=created_at,
                        target=dep.get("target"),
                    )
                )

            return deployments

        except json.JSONDecodeError as e:
            logger.error("Failed to parse deployments list: %s", str(e))
            return []

    async def deploy_with_branding(
        self,
        project_dir: str,
        lead_id: str,
        business_name: str,
        primary_color: Optional[str] = None,
        secondary_color: Optional[str] = None,
        logo_url: Optional[str] = None,
        tagline: Optional[str] = None,
        phone_number: Optional[str] = None,
        voice_websocket_url: Optional[str] = None,
        additional_env: Optional[dict[str, str]] = None,
    ) -> DeploymentResult:
        """Deploy a demo site with prospect-specific branding.

        This is a convenience method that packages common branding
        environment variables for demo site deployments.

        Args:
            project_dir: Path to the demo frontend project.
            lead_id: Lead/prospect ID for project naming.
            business_name: Business name for branding.
            primary_color: Primary brand color (hex, e.g., "#0066cc").
            secondary_color: Secondary brand color.
            logo_url: URL to business logo.
            tagline: Business tagline or slogan.
            phone_number: Twilio phone number for click-to-call.
            voice_websocket_url: WebSocket URL for voice agent.
            additional_env: Any additional environment variables.

        Returns:
            DeploymentResult with deployment details.
        """
        # Build environment variables
        env_vars = {
            "NEXT_PUBLIC_LEAD_ID": lead_id,
            "NEXT_PUBLIC_BUSINESS_NAME": business_name,
        }

        if primary_color:
            env_vars["NEXT_PUBLIC_PRIMARY_COLOR"] = primary_color

        if secondary_color:
            env_vars["NEXT_PUBLIC_SECONDARY_COLOR"] = secondary_color

        if logo_url:
            env_vars["NEXT_PUBLIC_LOGO_URL"] = logo_url

        if tagline:
            env_vars["NEXT_PUBLIC_TAGLINE"] = tagline

        if phone_number:
            env_vars["NEXT_PUBLIC_TWILIO_NUMBER"] = phone_number

        if voice_websocket_url:
            env_vars["NEXT_PUBLIC_VOICE_WEBSOCKET_URL"] = voice_websocket_url

        if additional_env:
            env_vars.update(additional_env)

        # Generate project name from lead ID and sanitized business name
        sanitized_name = "".join(
            c if c.isalnum() or c == "-" else "-"
            for c in business_name.lower()
        )
        sanitized_name = sanitized_name[:20].strip("-")  # Limit length
        project_name = f"{sanitized_name}-{lead_id[:8]}"

        logger.info(
            "Deploying demo with branding: business=%s, project=%s",
            business_name,
            project_name,
        )

        return await self.deploy(
            project_dir=project_dir,
            project_name=project_name,
            env_vars=env_vars,
            production=True,
        )

    def close(self) -> None:
        """Clean up deployer resources."""
        logger.info("VercelDeployer closed")

    async def __aenter__(self) -> "VercelDeployer":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        self.close()
