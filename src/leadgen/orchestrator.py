"""Pipeline Orchestrator for coordinating lead generation agents.

This module provides the main orchestration logic for the lead generation pipeline.
It coordinates the 5 specialized agents in sequence:
1. Scraper Agent - Finds businesses on Google Maps
2. Research Agent - Generates comprehensive dossiers
3. Voice Assembler Agent - Creates vector stores and voice configurations
4. Frontend Deployer Agent - Deploys demo sites to Vercel
5. Sales Agent - Sends cold emails via SendGrid

The orchestrator handles:
- Pipeline stage coordination
- Error handling with retries
- Progress tracking via database
- Campaign status updates
- Graceful degradation on partial failures
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Callable, TypeVar

from models.lead import Lead, LeadStatus
from models.campaign import Campaign, CampaignStatus
from models.dossier import Dossier
from models.deployment import Deployment, DeploymentStatus
from models.database import get_db_session


logger = logging.getLogger(__name__)


# Type variable for generic retry decorator
T = TypeVar("T")


class PipelineStage(str, Enum):
    """Stages in the lead generation pipeline."""

    SCRAPING = "scraping"
    RESEARCHING = "researching"
    VOICE_ASSEMBLY = "voice_assembly"
    DEPLOYMENT = "deployment"
    EMAILING = "emailing"
    COMPLETED = "completed"


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution.

    Attributes:
        max_retries: Maximum retry attempts per lead operation.
        retry_delay_seconds: Base delay between retries (exponential backoff).
        concurrent_leads: Number of leads to process concurrently.
        skip_voice_assembly: Skip voice agent creation if True.
        skip_deployment: Skip demo site deployment if True.
        skip_email: Skip cold email sending if True.
        email_style: Email style for cold outreach.
        email_variant: A/B test variant for emails.
        twilio_number: Twilio phone number for demo sites.
        voice_websocket_url: WebSocket URL for voice agent connection.
    """

    max_retries: int = 3
    retry_delay_seconds: float = 2.0
    concurrent_leads: int = 5
    skip_voice_assembly: bool = False
    skip_deployment: bool = False
    skip_email: bool = False
    email_style: str = "humorous"
    email_variant: str = "A"
    twilio_number: Optional[str] = None
    voice_websocket_url: Optional[str] = None


@dataclass
class LeadProcessingResult:
    """Result of processing a single lead through the pipeline.

    Attributes:
        lead_id: The lead ID that was processed.
        lead_name: Business name.
        success: Overall success of processing.
        stage_results: Results from each pipeline stage.
        dossier_status: Status of research dossier.
        vector_store_id: Created vector store ID (if applicable).
        deployment_url: Demo site URL (if deployed).
        email_sent: Whether email was sent successfully.
        errors: List of errors encountered.
        processing_time_seconds: Total processing time.
    """

    lead_id: str
    lead_name: str
    success: bool = True
    stage_results: dict[str, Any] = field(default_factory=dict)
    dossier_status: Optional[str] = None
    vector_store_id: Optional[str] = None
    deployment_url: Optional[str] = None
    email_sent: bool = False
    errors: list[str] = field(default_factory=list)
    processing_time_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "lead_id": self.lead_id,
            "lead_name": self.lead_name,
            "success": self.success,
            "stage_results": self.stage_results,
            "dossier_status": self.dossier_status,
            "vector_store_id": self.vector_store_id,
            "deployment_url": self.deployment_url,
            "email_sent": self.email_sent,
            "errors": self.errors,
            "processing_time_seconds": self.processing_time_seconds,
        }


@dataclass
class CampaignResult:
    """Result of a full campaign execution.

    Attributes:
        campaign_id: The campaign ID.
        success: Overall campaign success.
        total_leads: Total leads found.
        processed_leads: Successfully processed leads.
        failed_leads: Failed leads.
        lead_results: Individual lead processing results.
        errors: Campaign-level errors.
        started_at: Execution start time.
        completed_at: Execution end time.
        duration_seconds: Total execution duration.
    """

    campaign_id: str
    success: bool = True
    total_leads: int = 0
    processed_leads: int = 0
    failed_leads: int = 0
    lead_results: list[LeadProcessingResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "campaign_id": self.campaign_id,
            "success": self.success,
            "total_leads": self.total_leads,
            "processed_leads": self.processed_leads,
            "failed_leads": self.failed_leads,
            "lead_results": [r.to_dict() for r in self.lead_results],
            "errors": self.errors,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }


async def retry_with_backoff(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 2.0,
    **kwargs: Any,
) -> T:
    """Execute a function with exponential backoff retry logic.

    Args:
        func: Function to execute (sync or async).
        *args: Positional arguments for the function.
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds (doubles each retry).
        **kwargs: Keyword arguments for the function.

    Returns:
        The function result on success.

    Raises:
        The last exception if all retries fail.
    """
    last_exception: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "Attempt %d/%d failed: %s. Retrying in %.1fs...",
                    attempt + 1,
                    max_retries + 1,
                    str(e),
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "All %d attempts failed. Last error: %s",
                    max_retries + 1,
                    str(e),
                )

    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected retry loop exit")


class LeadGenOrchestrator:
    """Orchestrates the lead generation pipeline across all agents.

    This class coordinates the flow of leads through the pipeline stages:
    scraping -> research -> voice assembly -> deployment -> email.

    It handles error recovery, progress tracking, and database updates.

    Attributes:
        config: Pipeline configuration.
        _progress_callback: Optional callback for progress updates.
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ):
        """Initialize the orchestrator.

        Args:
            config: Pipeline configuration. Uses defaults if not provided.
            progress_callback: Optional callback(stage, current, total) for progress.
        """
        self.config = config or PipelineConfig()
        self._progress_callback = progress_callback

    def _report_progress(self, stage: str, current: int, total: int) -> None:
        """Report progress to the callback if set."""
        if self._progress_callback:
            try:
                self._progress_callback(stage, current, total)
            except Exception as e:
                logger.warning("Progress callback error: %s", e)

    async def run_campaign(
        self,
        zip_code: str,
        industries: list[str],
        radius_miles: int = 20,
        max_leads: Optional[int] = None,
    ) -> CampaignResult:
        """Execute a full lead generation campaign.

        This is the main entry point for running a campaign. It:
        1. Creates a campaign record in the database
        2. Scrapes leads from Google Maps
        3. Processes each lead through the pipeline
        4. Updates campaign status throughout
        5. Returns comprehensive results

        Args:
            zip_code: Target zip code for lead scraping.
            industries: List of industries to search (e.g., ["dentist", "hvac"]).
            radius_miles: Search radius in miles. Defaults to 20.
            max_leads: Maximum leads to process. None for no limit.

        Returns:
            CampaignResult with all campaign metrics and lead results.
        """
        started_at = datetime.now(timezone.utc)
        campaign_id: Optional[str] = None
        result = CampaignResult(
            campaign_id="",
            started_at=started_at,
        )

        try:
            # Create campaign record
            async with get_db_session() as session:
                campaign = Campaign(
                    zip_code=zip_code,
                    industries=industries,
                    radius_miles=radius_miles,
                    status=CampaignStatus.PENDING,
                )
                session.add(campaign)
                await session.flush()
                campaign_id = campaign.id
                result.campaign_id = campaign_id
                logger.info(
                    "Created campaign %s: zip=%s, industries=%s",
                    campaign_id,
                    zip_code,
                    industries,
                )

            # Stage 1: Scraping
            self._report_progress(PipelineStage.SCRAPING.value, 0, 1)
            leads = await self._scrape_leads(
                campaign_id=campaign_id,
                zip_code=zip_code,
                industries=industries,
                radius_miles=radius_miles,
                max_leads=max_leads,
            )
            result.total_leads = len(leads)

            if not leads:
                logger.warning("No leads found for campaign %s", campaign_id)
                await self._update_campaign_status(
                    campaign_id,
                    CampaignStatus.COMPLETED,
                    total_leads=0,
                )
                result.success = True
                return result

            # Update campaign with lead count
            await self._update_campaign_status(
                campaign_id,
                CampaignStatus.RESEARCHING,
                total_leads=len(leads),
            )

            # Process leads through pipeline
            self._report_progress(PipelineStage.RESEARCHING.value, 0, len(leads))

            # Process leads with concurrency control
            semaphore = asyncio.Semaphore(self.config.concurrent_leads)

            async def process_with_semaphore(lead: dict) -> LeadProcessingResult:
                async with semaphore:
                    return await self._process_single_lead(campaign_id, lead)

            # Process all leads concurrently (with semaphore limiting)
            tasks = [process_with_semaphore(lead) for lead in leads]
            lead_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for idx, lr in enumerate(lead_results):
                if isinstance(lr, Exception):
                    result.failed_leads += 1
                    result.errors.append(f"Lead {idx} failed: {str(lr)}")
                elif isinstance(lr, LeadProcessingResult):
                    result.lead_results.append(lr)
                    if lr.success:
                        result.processed_leads += 1
                    else:
                        result.failed_leads += 1

                self._report_progress(
                    PipelineStage.COMPLETED.value,
                    result.processed_leads + result.failed_leads,
                    result.total_leads,
                )

            # Update campaign final status
            final_status = (
                CampaignStatus.COMPLETED
                if result.processed_leads > 0
                else CampaignStatus.FAILED
            )
            await self._update_campaign_status(
                campaign_id,
                final_status,
                processed_leads=result.processed_leads,
                failed_leads=result.failed_leads,
            )

            result.success = result.processed_leads > 0

        except Exception as e:
            logger.exception("Campaign %s failed: %s", campaign_id, e)
            result.success = False
            result.errors.append(str(e))

            if campaign_id:
                await self._update_campaign_status(
                    campaign_id,
                    CampaignStatus.FAILED,
                    error_message=str(e),
                )

        finally:
            result.completed_at = datetime.now(timezone.utc)
            result.duration_seconds = (
                result.completed_at - started_at
            ).total_seconds()

        return result

    async def _scrape_leads(
        self,
        campaign_id: str,
        zip_code: str,
        industries: list[str],
        radius_miles: int,
        max_leads: Optional[int],
    ) -> list[dict]:
        """Execute the scraping stage using the Scraper Agent.

        Args:
            campaign_id: Campaign ID for tracking.
            zip_code: Target zip code.
            industries: Industries to search.
            radius_miles: Search radius.
            max_leads: Optional lead limit.

        Returns:
            List of scraped lead dictionaries.
        """
        from agents.scraper_agent import scrape_multiple_industries

        logger.info(
            "Scraping leads: zip=%s, industries=%s, radius=%d",
            zip_code,
            industries,
            radius_miles,
        )

        try:
            # Use the scraper agent tool directly
            results = await retry_with_backoff(
                scrape_multiple_industries,
                zip_code=zip_code,
                industries=industries,
                radius_miles=float(radius_miles),
                max_results_per_industry=max_leads or 60,
                max_retries=self.config.max_retries,
                base_delay=self.config.retry_delay_seconds,
            )

            # Flatten results from all industries
            all_leads = []
            for industry, leads in results.items():
                for lead in leads:
                    lead["campaign_id"] = campaign_id
                    all_leads.append(lead)

            # Apply max_leads limit if specified
            if max_leads and len(all_leads) > max_leads:
                all_leads = all_leads[:max_leads]

            logger.info("Scraped %d total leads", len(all_leads))

            # Save leads to database
            await self._save_leads_to_db(campaign_id, all_leads)

            return all_leads

        except Exception as e:
            logger.error("Scraping failed: %s", e)
            raise

    async def _save_leads_to_db(
        self,
        campaign_id: str,
        leads: list[dict],
    ) -> None:
        """Save scraped leads to the database.

        Args:
            campaign_id: Campaign ID for association.
            leads: List of lead dictionaries.
        """
        async with get_db_session() as session:
            for lead_data in leads:
                lead = Lead(
                    name=lead_data.get("name", ""),
                    address=lead_data.get("address", ""),
                    phone=lead_data.get("phone"),
                    website=lead_data.get("website"),
                    industry=lead_data.get("industry", ""),
                    rating=lead_data.get("rating"),
                    review_count=lead_data.get("review_count"),
                    revenue=lead_data.get("estimated_revenue"),
                    google_place_id=lead_data.get("place_id"),
                    status=LeadStatus.NEW,
                )
                session.add(lead)
                lead_data["db_id"] = lead.id

            logger.info("Saved %d leads to database", len(leads))

    async def _process_single_lead(
        self,
        campaign_id: str,
        lead_data: dict,
    ) -> LeadProcessingResult:
        """Process a single lead through all pipeline stages.

        Args:
            campaign_id: Campaign ID for tracking.
            lead_data: Lead dictionary from scraping.

        Returns:
            LeadProcessingResult with all stage outcomes.
        """
        start_time = datetime.now(timezone.utc)
        lead_id = lead_data.get("db_id", lead_data.get("place_id", "unknown"))
        lead_name = lead_data.get("name", "Unknown")

        result = LeadProcessingResult(
            lead_id=lead_id,
            lead_name=lead_name,
        )

        try:
            # Stage 2: Research
            await self._update_lead_status(lead_id, LeadStatus.RESEARCHING)
            research_result = await self._research_lead(lead_data)
            result.stage_results["research"] = research_result

            if not research_result.get("success"):
                result.errors.append(
                    f"Research failed: {research_result.get('error')}"
                )
                # Continue with partial data

            result.dossier_status = research_result.get("dossier_status", "failed")
            dossier_content = research_result.get("dossier")

            # Save dossier to database
            if dossier_content:
                await self._save_dossier_to_db(
                    lead_id,
                    dossier_content,
                    result.dossier_status,
                )

            await self._update_lead_status(lead_id, LeadStatus.RESEARCHED)

            # Stage 3: Voice Assembly (optional)
            if not self.config.skip_voice_assembly and dossier_content:
                voice_result = await self._assemble_voice_agent(lead_data, dossier_content)
                result.stage_results["voice_assembly"] = voice_result

                if voice_result.get("success"):
                    result.vector_store_id = voice_result.get("vector_store_id")
                else:
                    result.errors.append(
                        f"Voice assembly failed: {voice_result.get('error')}"
                    )

            # Stage 4: Deployment (optional)
            if not self.config.skip_deployment:
                await self._update_lead_status(lead_id, LeadStatus.DEPLOYING)
                deploy_result = await self._deploy_demo_site(lead_data)
                result.stage_results["deployment"] = deploy_result

                if deploy_result.get("success"):
                    result.deployment_url = deploy_result.get("url")
                    await self._save_deployment_to_db(
                        lead_id,
                        deploy_result,
                    )
                    await self._update_lead_status(lead_id, LeadStatus.DEPLOYED)
                else:
                    result.errors.append(
                        f"Deployment failed: {deploy_result.get('error')}"
                    )

            # Stage 5: Email (optional)
            if (
                not self.config.skip_email
                and lead_data.get("email")
                and result.deployment_url
            ):
                email_result = await self._send_cold_email(
                    lead_data,
                    result.deployment_url,
                )
                result.stage_results["email"] = email_result

                if email_result.get("success"):
                    result.email_sent = True
                    await self._update_lead_status(lead_id, LeadStatus.EMAILED)
                else:
                    result.errors.append(
                        f"Email failed: {email_result.get('error')}"
                    )

            # Determine overall success
            result.success = (
                result.dossier_status in ("complete", "partial")
                and len(result.errors) < 3  # Allow some partial failures
            )

        except Exception as e:
            logger.exception("Lead %s processing failed: %s", lead_id, e)
            result.success = False
            result.errors.append(str(e))
            await self._update_lead_status(lead_id, LeadStatus.FAILED)

        finally:
            end_time = datetime.now(timezone.utc)
            result.processing_time_seconds = (end_time - start_time).total_seconds()

        return result

    async def _research_lead(self, lead_data: dict) -> dict:
        """Execute research stage using the Research Agent.

        Args:
            lead_data: Lead dictionary with business information.

        Returns:
            Research result dictionary with dossier content.
        """
        from agents.research_agent import research_lead_comprehensive

        logger.info("Researching lead: %s", lead_data.get("name"))

        try:
            result_json = await retry_with_backoff(
                research_lead_comprehensive,
                name=lead_data.get("name", ""),
                website=lead_data.get("website"),
                address=lead_data.get("address"),
                phone=lead_data.get("phone"),
                industry=lead_data.get("industry"),
                google_rating=lead_data.get("rating"),
                review_count=lead_data.get("review_count"),
                estimated_revenue=lead_data.get("estimated_revenue"),
                max_retries=self.config.max_retries,
                base_delay=self.config.retry_delay_seconds,
            )

            result = json.loads(result_json)
            return {
                "success": result.get("success", False),
                "dossier": result.get("dossier"),
                "dossier_status": result.get("dossier_status", "failed"),
                "error": "; ".join(result.get("errors", [])) if result.get("errors") else None,
            }

        except Exception as e:
            logger.error("Research failed for %s: %s", lead_data.get("name"), e)
            return {
                "success": False,
                "dossier": None,
                "dossier_status": "failed",
                "error": str(e),
            }

    async def _assemble_voice_agent(
        self,
        lead_data: dict,
        dossier_content: str,
    ) -> dict:
        """Execute voice assembly stage using the Voice Assembler Agent.

        Args:
            lead_data: Lead dictionary with business information.
            dossier_content: Research dossier markdown content.

        Returns:
            Voice assembly result dictionary.
        """
        from agents.voice_assembler_agent import assemble_voice_agent

        logger.info("Assembling voice agent for: %s", lead_data.get("name"))

        try:
            result_json = await retry_with_backoff(
                assemble_voice_agent,
                name=lead_data.get("name", ""),
                dossier_content=dossier_content,
                lead_id=lead_data.get("db_id"),
                industry=lead_data.get("industry"),
                address=lead_data.get("address"),
                phone=lead_data.get("phone"),
                website=lead_data.get("website"),
                max_retries=self.config.max_retries,
                base_delay=self.config.retry_delay_seconds,
            )

            result = json.loads(result_json)
            config = result.get("config", {})

            return {
                "success": result.get("success", False),
                "vector_store_id": config.get("vector_store_id"),
                "personality_prompt": config.get("personality_prompt"),
                "greeting": config.get("greeting"),
                "voice_agent_ready": config.get("voice_agent_ready", False),
                "error": config.get("error"),
            }

        except Exception as e:
            logger.error("Voice assembly failed for %s: %s", lead_data.get("name"), e)
            return {
                "success": False,
                "vector_store_id": None,
                "error": str(e),
            }

    async def _deploy_demo_site(self, lead_data: dict) -> dict:
        """Execute deployment stage using the Frontend Deployer Agent.

        Args:
            lead_data: Lead dictionary with business information.

        Returns:
            Deployment result dictionary.
        """
        from agents.frontend_deployer_agent import deploy_demo_site

        logger.info("Deploying demo site for: %s", lead_data.get("name"))

        try:
            result_json = await retry_with_backoff(
                deploy_demo_site,
                business_name=lead_data.get("name", ""),
                lead_id=lead_data.get("db_id"),
                industry=lead_data.get("industry"),
                phone=lead_data.get("phone"),
                twilio_number=self.config.twilio_number,
                voice_websocket_url=self.config.voice_websocket_url,
                max_retries=self.config.max_retries,
                base_delay=self.config.retry_delay_seconds,
            )

            result = json.loads(result_json)

            return {
                "success": result.get("success", False),
                "deployment_id": result.get("deployment_id"),
                "url": result.get("url"),
                "preview_url": result.get("preview_url"),
                "project_name": result.get("project_name"),
                "status": result.get("status"),
                "error": result.get("error"),
            }

        except Exception as e:
            logger.error("Deployment failed for %s: %s", lead_data.get("name"), e)
            return {
                "success": False,
                "url": None,
                "error": str(e),
            }

    async def _send_cold_email(
        self,
        lead_data: dict,
        demo_url: str,
    ) -> dict:
        """Execute email stage using the Sales Agent.

        Args:
            lead_data: Lead dictionary with contact information.
            demo_url: URL to the deployed demo site.

        Returns:
            Email send result dictionary.
        """
        from agents.sales_agent import generate_and_send_cold_email

        logger.info("Sending cold email to: %s", lead_data.get("email"))

        try:
            result_json = await retry_with_backoff(
                generate_and_send_cold_email,
                lead_id=lead_data.get("db_id", ""),
                to_email=lead_data.get("email", ""),
                business_name=lead_data.get("name", ""),
                demo_url=demo_url,
                industry=lead_data.get("industry", ""),
                email_style=self.config.email_style,
                email_variant=self.config.email_variant,
                max_retries=self.config.max_retries,
                base_delay=self.config.retry_delay_seconds,
            )

            result = json.loads(result_json)
            send_result = result.get("result", {})

            return {
                "success": result.get("success", False),
                "message_id": send_result.get("message_id"),
                "subject": result.get("email_subject"),
                "status": send_result.get("status"),
                "error": result.get("error"),
            }

        except Exception as e:
            logger.error("Email failed for %s: %s", lead_data.get("name"), e)
            return {
                "success": False,
                "error": str(e),
            }

    async def _update_lead_status(
        self,
        lead_id: str,
        status: LeadStatus,
    ) -> None:
        """Update lead status in the database.

        Args:
            lead_id: Lead ID to update.
            status: New status to set.
        """
        try:
            async with get_db_session() as session:
                lead = await session.get(Lead, lead_id)
                if lead:
                    lead.status = status
                    logger.debug("Updated lead %s status to %s", lead_id, status.value)
        except Exception as e:
            logger.warning("Failed to update lead status: %s", e)

    async def _update_campaign_status(
        self,
        campaign_id: str,
        status: CampaignStatus,
        total_leads: Optional[int] = None,
        processed_leads: Optional[int] = None,
        failed_leads: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update campaign status in the database.

        Args:
            campaign_id: Campaign ID to update.
            status: New status to set.
            total_leads: Optional total leads count to set.
            processed_leads: Optional processed leads count to set.
            failed_leads: Optional failed leads count to set.
            error_message: Optional error message to set.
        """
        try:
            async with get_db_session() as session:
                campaign = await session.get(Campaign, campaign_id)
                if campaign:
                    campaign.status = status

                    if total_leads is not None:
                        campaign.total_leads = total_leads
                    if processed_leads is not None:
                        campaign.processed_leads = processed_leads
                    if failed_leads is not None:
                        campaign.failed_leads = failed_leads
                    if error_message is not None:
                        campaign.error_message = error_message

                    if status == CampaignStatus.SCRAPING and not campaign.started_at:
                        campaign.started_at = datetime.now(timezone.utc)
                    elif status in (
                        CampaignStatus.COMPLETED,
                        CampaignStatus.FAILED,
                        CampaignStatus.CANCELLED,
                    ):
                        campaign.completed_at = datetime.now(timezone.utc)

                    logger.debug(
                        "Updated campaign %s status to %s",
                        campaign_id,
                        status.value,
                    )
        except Exception as e:
            logger.warning("Failed to update campaign status: %s", e)

    async def _save_dossier_to_db(
        self,
        lead_id: str,
        dossier_content: str,
        dossier_status: str,
    ) -> None:
        """Save research dossier to the database.

        Args:
            lead_id: Lead ID to associate dossier with.
            dossier_content: Markdown dossier content.
            dossier_status: Status of the dossier (for logging only).
        """
        try:
            async with get_db_session() as session:
                dossier = Dossier(
                    lead_id=lead_id,
                    content=dossier_content,
                )
                session.add(dossier)
                logger.debug(
                    "Saved dossier for lead %s (status: %s)",
                    lead_id,
                    dossier_status,
                )
        except Exception as e:
            logger.warning("Failed to save dossier: %s", e)

    async def _save_deployment_to_db(
        self,
        lead_id: str,
        deploy_result: dict,
    ) -> None:
        """Save deployment record to the database.

        Args:
            lead_id: Lead ID to associate deployment with.
            deploy_result: Deployment result dictionary.
        """
        try:
            async with get_db_session() as session:
                deployment = Deployment(
                    lead_id=lead_id,
                    url=deploy_result.get("url"),
                    vercel_id=deploy_result.get("deployment_id"),
                    status=DeploymentStatus.READY,
                )
                session.add(deployment)
                logger.debug(
                    "Saved deployment for lead %s: %s",
                    lead_id,
                    deploy_result.get("url"),
                )
        except Exception as e:
            logger.warning("Failed to save deployment: %s", e)

    async def process_leads_batch(
        self,
        lead_ids: list[str],
        skip_scraping: bool = True,
    ) -> list[LeadProcessingResult]:
        """Process a batch of existing leads through the pipeline.

        Use this to reprocess leads that failed or to process
        leads from a previous scraping operation.

        Args:
            lead_ids: List of lead IDs to process.
            skip_scraping: Skip scraping stage (leads already exist).

        Returns:
            List of LeadProcessingResult for each lead.
        """
        results: list[LeadProcessingResult] = []

        async with get_db_session() as session:
            for lead_id in lead_ids:
                lead = await session.get(Lead, lead_id)
                if not lead:
                    results.append(
                        LeadProcessingResult(
                            lead_id=lead_id,
                            lead_name="Unknown",
                            success=False,
                            errors=["Lead not found"],
                        )
                    )
                    continue

                lead_data = lead.to_dict()
                lead_data["db_id"] = lead.id

                result = await self._process_single_lead("batch", lead_data)
                results.append(result)

        return results

    async def cleanup_failed_leads(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """Clean up resources for failed leads in a campaign.

        Deletes vector stores and deployments for leads that failed
        processing to avoid resource leaks.

        Args:
            campaign_id: Campaign ID to clean up.

        Returns:
            Dictionary with cleanup statistics.
        """
        from agents.voice_assembler_agent import delete_vector_store
        from agents.frontend_deployer_agent import delete_demo_deployment

        logger.info("Cleaning up failed leads for campaign %s", campaign_id)

        cleanup_stats = {
            "vector_stores_deleted": 0,
            "deployments_deleted": 0,
            "errors": [],
        }

        # This would query failed leads and clean up their resources
        # Implementation depends on how we track vector store IDs and deployments

        return cleanup_stats


# Convenience function for simple usage
async def run_lead_gen_campaign(
    zip_code: str,
    industries: list[str],
    radius_miles: int = 20,
    max_leads: Optional[int] = None,
    config: Optional[PipelineConfig] = None,
) -> CampaignResult:
    """Run a lead generation campaign with default settings.

    This is a convenience function for simple campaign execution.

    Args:
        zip_code: Target zip code.
        industries: List of industries to search.
        radius_miles: Search radius in miles.
        max_leads: Optional maximum leads to process.
        config: Optional pipeline configuration.

    Returns:
        CampaignResult with all campaign metrics.

    Example:
        >>> result = await run_lead_gen_campaign(
        ...     zip_code="62701",
        ...     industries=["dentist", "hvac"],
        ...     max_leads=10,
        ... )
        >>> print(f"Processed {result.processed_leads} leads")
    """
    orchestrator = LeadGenOrchestrator(config=config)
    return await orchestrator.run_campaign(
        zip_code=zip_code,
        industries=industries,
        radius_miles=radius_miles,
        max_leads=max_leads,
    )
