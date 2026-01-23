"""Sales Agent for cold email generation and delivery via SendGrid.

This module implements the sales agent using OpenAI Agents SDK.
The agent handles:
- Personalized cold email generation
- Email delivery via SendGrid
- Open/click tracking
- CAN-SPAM compliance
- Batch email campaigns
- Delivery metrics and reporting

Required for spec FR-6 (Cold Email Delivery):
- Email delivered (not bounced)
- Opens/clicks tracked
- CAN-SPAM compliant
"""

import asyncio
import concurrent.futures
import json
import logging
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
    current_module = "agents.sales_agent"  # This module being loaded

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


@dataclass
class EmailSendResult:
    """Result of sending a single cold email.

    Attributes:
        lead_id: ID of the lead this email was sent to.
        to_email: Recipient email address.
        message_id: SendGrid message ID for tracking.
        subject: Email subject line.
        status: Delivery status (sent, failed, etc.).
        sent_at: Timestamp when email was sent.
        success: Whether email was sent successfully.
        error: Error message if send failed.
    """

    lead_id: str
    to_email: str
    message_id: Optional[str] = None
    subject: str = ""
    status: str = "pending"
    sent_at: Optional[datetime] = None
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "lead_id": self.lead_id,
            "to_email": self.to_email,
            "message_id": self.message_id,
            "subject": self.subject,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class CampaignMetrics:
    """Metrics for a cold email campaign.

    Attributes:
        total_sent: Number of emails sent.
        delivered: Number of emails delivered.
        opened: Number of emails opened.
        clicked: Number of links clicked.
        bounced: Number of bounced emails.
        spam_reports: Number of spam complaints.
        delivery_rate: Percentage of sent that were delivered.
        open_rate: Percentage of delivered that were opened.
        click_rate: Percentage of opened that were clicked.
        bounce_rate: Percentage of sent that bounced.
    """

    total_sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    bounced: int = 0
    spam_reports: int = 0

    @property
    def delivery_rate(self) -> float:
        """Calculate delivery rate percentage."""
        if self.total_sent == 0:
            return 0.0
        return (self.delivered / self.total_sent) * 100

    @property
    def open_rate(self) -> float:
        """Calculate open rate percentage."""
        if self.delivered == 0:
            return 0.0
        return (self.opened / self.delivered) * 100

    @property
    def click_rate(self) -> float:
        """Calculate click rate percentage."""
        if self.opened == 0:
            return 0.0
        return (self.clicked / self.opened) * 100

    @property
    def bounce_rate(self) -> float:
        """Calculate bounce rate percentage."""
        if self.total_sent == 0:
            return 0.0
        return (self.bounced / self.total_sent) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_sent": self.total_sent,
            "delivered": self.delivered,
            "opened": self.opened,
            "clicked": self.clicked,
            "bounced": self.bounced,
            "spam_reports": self.spam_reports,
            "delivery_rate": round(self.delivery_rate, 2),
            "open_rate": round(self.open_rate, 2),
            "click_rate": round(self.click_rate, 2),
            "bounce_rate": round(self.bounce_rate, 2),
        }


@dataclass
class CANSpamConfig:
    """CAN-SPAM compliance configuration.

    Required fields per CAN-SPAM Act for commercial emails.

    Attributes:
        company_name: Name of the sending company.
        address_line1: Street address.
        city: City name.
        state: State/province.
        zip_code: Postal/ZIP code.
        country: Country name.
        unsubscribe_reason: Reason the recipient is receiving the email.
    """

    company_name: str = "LeadGen AI"
    address_line1: str = "123 Demo Street"
    city: str = "San Francisco"
    state: str = "CA"
    zip_code: str = "94102"
    country: str = "USA"
    unsubscribe_reason: str = "we thought your business might benefit from AI automation"

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for email generation."""
        return {
            "company_name": self.company_name,
            "address_line1": self.address_line1,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "country": self.country,
            "unsubscribe_reason": self.unsubscribe_reason,
        }


def _generate_and_send_email_internal(
    lead_id: str,
    to_email: str,
    business_name: str,
    demo_url: str,
    industry: str = "",
    recipient_name: Optional[str] = None,
    pain_points: Optional[list[str]] = None,
    email_style: str = "humorous",
    email_variant: str = "A",
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
    can_spam_config: Optional[CANSpamConfig] = None,
) -> dict[str, Any]:
    """Internal implementation for generating and sending a cold email.

    This function combines email generation and SendGrid delivery.
    Returns a dict - the @function_tool version wraps this and returns JSON.
    """
    from integrations.sendgrid import SendGridClient, CANSpamInfo
    from utils.email_templates import (
        generate_cold_email_from_dict,
        CANSpamFooter,
    )

    logger.info(
        "Generating and sending cold email: lead_id=%s, to=%s, business=%s",
        lead_id,
        to_email,
        business_name,
    )

    async def _send() -> dict[str, Any]:
        """Async email generation and delivery."""
        result = EmailSendResult(
            lead_id=lead_id,
            to_email=to_email,
        )

        try:
            # Build email data for template generation
            email_data = {
                "name": business_name,
                "industry": industry,
                "demo_url": demo_url,
                "recipient_name": recipient_name,
                "pain_points": pain_points or [],
                "style": email_style,
                "variant": email_variant,
            }

            # Build CAN-SPAM footer config
            can_spam_dict = None
            if can_spam_config:
                can_spam_dict = can_spam_config.to_dict()

            # Generate the email
            generated_email = generate_cold_email_from_dict(
                email_data,
                can_spam_info=can_spam_dict,
            )

            result.subject = generated_email.subject

            # Create SendGrid client and send
            async with SendGridClient(
                default_from_email=from_email,
                default_from_name=from_name,
            ) as client:
                # Build CAN-SPAM info for SendGrid (separate from template footer)
                sendgrid_can_spam = None
                if can_spam_config:
                    sendgrid_can_spam = CANSpamInfo(
                        company_name=can_spam_config.company_name,
                        address_line1=can_spam_config.address_line1,
                        city=can_spam_config.city,
                        state=can_spam_config.state,
                        zip_code=can_spam_config.zip_code,
                        country=can_spam_config.country,
                        reason=can_spam_config.unsubscribe_reason,
                    )

                # Send the email
                send_result = await client.send_email(
                    to_email=to_email,
                    subject=generated_email.subject,
                    html_content=generated_email.html_content,
                    text_content=generated_email.text_content,
                    categories=["cold_email", f"industry_{industry}", f"lead_{lead_id}"],
                    tracking_id=lead_id,
                    can_spam_info=sendgrid_can_spam,
                    enable_tracking=True,
                )

                result.message_id = send_result.message_id
                result.status = send_result.status.value
                result.sent_at = send_result.sent_at
                result.success = send_result.success
                result.error = send_result.error

            logger.info(
                "Email sent: lead_id=%s, message_id=%s, success=%s",
                lead_id,
                result.message_id,
                result.success,
            )

            return {
                "result": result.to_dict(),
                "email_subject": generated_email.subject,
                "email_style": generated_email.style.value,
                "email_variant": generated_email.variant.value,
                "tokens_used": generated_email.tokens_used,
                "success": result.success,
                "error": result.error,
            }

        except ValueError as e:
            error_msg = f"Configuration error: {e}"
            logger.error("Failed to send email (config error): %s", e)
            result.success = False
            result.status = "failed"
            result.error = error_msg
            return {
                "result": result.to_dict(),
                "email_subject": result.subject,
                "email_style": email_style,
                "email_variant": email_variant,
                "tokens_used": [],
                "success": False,
                "error": error_msg,
            }
        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to send email to %s: %s", to_email, e)
            result.success = False
            result.status = "failed"
            result.error = error_msg
            return {
                "result": result.to_dict(),
                "email_subject": result.subject,
                "email_style": email_style,
                "email_variant": email_variant,
                "tokens_used": [],
                "success": False,
                "error": error_msg,
            }

    # Run async code in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _send())
                return future.result()
        else:
            return loop.run_until_complete(_send())
    except RuntimeError:
        return asyncio.run(_send())


@function_tool
def generate_and_send_cold_email(
    lead_id: str,
    to_email: str,
    business_name: str,
    demo_url: str,
    industry: str = "",
    recipient_name: str = "",
    email_style: str = "humorous",
    email_variant: str = "A",
) -> str:
    """Generate a personalized cold email and send it via SendGrid.

    This is the primary function for sending cold outreach emails. It:
    1. Generates a personalized email using industry-specific templates
    2. Applies CAN-SPAM compliant footer
    3. Sends via SendGrid with open/click tracking
    4. Returns tracking information for follow-up

    Args:
        lead_id: Unique identifier for the lead (used for tracking).
        to_email: Recipient email address.
        business_name: Name of the target business.
        demo_url: URL to the personalized demo site.
        industry: Business industry (dentist, hvac, salon, etc.).
        recipient_name: Name of the recipient (optional).
        email_style: Email style - "humorous" (default), "professional", "direct", "curiosity".
        email_variant: A/B test variant - "A" (default), "B", or "C".

    Returns:
        JSON string containing:
        - result: SendResult dict with message_id, status, timestamps
        - email_subject: The generated subject line
        - email_style: Style used for generation
        - email_variant: A/B variant used
        - tokens_used: Personalization tokens that were replaced
        - success: Whether email was sent successfully
        - error: Error message if send failed

    Example:
        >>> result_json = generate_and_send_cold_email(
        ...     lead_id="lead_12345",
        ...     to_email="owner@acmedental.com",
        ...     business_name="Acme Dental",
        ...     demo_url="https://acme-dental.demo.app",
        ...     industry="dentist"
        ... )
        >>> import json; result = json.loads(result_json)
        >>> print(f"Sent: {result['result']['message_id']}")
    """
    result = _generate_and_send_email_internal(
        lead_id=lead_id,
        to_email=to_email,
        business_name=business_name,
        demo_url=demo_url,
        industry=industry,
        recipient_name=recipient_name if recipient_name else None,
        email_style=email_style,
        email_variant=email_variant,
    )
    return json.dumps(result)


def _send_campaign_batch_internal(
    leads: list[dict[str, Any]],
    email_style: str = "humorous",
    email_variant: str = "A",
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
    can_spam_config: Optional[CANSpamConfig] = None,
) -> dict[str, Any]:
    """Internal implementation for sending a batch campaign.

    Args:
        leads: List of lead dicts with keys: id, email, name, demo_url, industry.
        email_style: Email style for all emails.
        email_variant: A/B variant for all emails.
        from_email: Sender email address.
        from_name: Sender display name.
        can_spam_config: CAN-SPAM compliance configuration.

    Returns:
        Dictionary with batch send results and summary.
    """
    logger.info("Sending campaign batch: %d leads", len(leads))

    results: list[dict[str, Any]] = []
    successful = 0
    failed = 0

    for lead in leads:
        lead_id = lead.get("id", lead.get("lead_id", "unknown"))
        to_email = lead.get("email", "")
        business_name = lead.get("name", lead.get("business_name", ""))
        demo_url = lead.get("demo_url", "")
        industry = lead.get("industry", "")
        recipient_name = lead.get("recipient_name")

        if not to_email:
            results.append({
                "lead_id": lead_id,
                "success": False,
                "error": "Missing email address",
            })
            failed += 1
            continue

        result = _generate_and_send_email_internal(
            lead_id=str(lead_id),
            to_email=to_email,
            business_name=business_name,
            demo_url=demo_url,
            industry=industry,
            recipient_name=recipient_name,
            email_style=email_style,
            email_variant=email_variant,
            from_email=from_email,
            from_name=from_name,
            can_spam_config=can_spam_config,
        )

        results.append(result)
        if result.get("success"):
            successful += 1
        else:
            failed += 1

    success_rate = (successful / len(leads) * 100) if leads else 0

    return {
        "total": len(leads),
        "successful": successful,
        "failed": failed,
        "success_rate": round(success_rate, 2),
        "results": results,
    }


@function_tool
def send_campaign_emails(
    leads_json: str,
    email_style: str = "humorous",
    email_variant: str = "A",
) -> str:
    """Send cold emails to multiple leads in a campaign batch.

    This function processes a list of leads and sends personalized
    cold emails to each. Use for bulk email campaigns.

    Args:
        leads_json: JSON string of lead array. Each lead should have:
            - id (str): Lead identifier
            - email (str): Recipient email address
            - name (str): Business name
            - demo_url (str): URL to demo site
            - industry (str): Industry category
            - recipient_name (str, optional): Contact name
        email_style: Style for all emails ("humorous", "professional", "direct", "curiosity").
        email_variant: A/B variant for all emails ("A", "B", "C").

    Returns:
        JSON string containing:
        - total: Number of leads processed
        - successful: Number of emails sent successfully
        - failed: Number of failed sends
        - success_rate: Percentage of successful sends
        - results: Array of individual send results

    Example:
        >>> leads = [
        ...     {"id": "1", "email": "a@example.com", "name": "Acme", "demo_url": "https://acme.demo.app", "industry": "dentist"},
        ...     {"id": "2", "email": "b@example.com", "name": "Best", "demo_url": "https://best.demo.app", "industry": "hvac"},
        ... ]
        >>> result = send_campaign_emails(json.dumps(leads))
    """
    try:
        leads = json.loads(leads_json)
        if not isinstance(leads, list):
            return json.dumps({
                "success": False,
                "error": "leads_json must be a JSON array",
            })
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": f"Invalid JSON: {e}",
        })

    result = _send_campaign_batch_internal(
        leads=leads,
        email_style=email_style,
        email_variant=email_variant,
    )

    return json.dumps(result)


def _get_email_stats_internal(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict[str, Any]:
    """Internal implementation for getting email delivery statistics.

    Args:
        start_date: Start date (YYYY-MM-DD format).
        end_date: End date (YYYY-MM-DD format).

    Returns:
        Dictionary with email delivery metrics.
    """
    from integrations.sendgrid import SendGridClient

    logger.info("Getting email stats: start=%s, end=%s", start_date, end_date)

    async def _get_stats() -> dict[str, Any]:
        """Async stats retrieval."""
        try:
            async with SendGridClient() as client:
                # Parse dates if provided
                start_dt = None
                end_dt = None

                if start_date:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                if end_date:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

                # Get stats from SendGrid
                stats = await client.get_stats(
                    start_date=start_dt,
                    end_date=end_dt,
                )

                metrics = CampaignMetrics(
                    total_sent=stats.sent,
                    delivered=stats.delivered,
                    opened=stats.opened,
                    clicked=stats.clicked,
                    bounced=stats.bounced,
                    spam_reports=stats.spam_reports,
                )

                return {
                    "metrics": metrics.to_dict(),
                    "start_date": start_date,
                    "end_date": end_date,
                    "success": True,
                    "error": None,
                }

        except ValueError as e:
            logger.error("Configuration error getting stats: %s", e)
            return {
                "metrics": CampaignMetrics().to_dict(),
                "start_date": start_date,
                "end_date": end_date,
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            logger.error("Error getting email stats: %s", e)
            return {
                "metrics": CampaignMetrics().to_dict(),
                "start_date": start_date,
                "end_date": end_date,
                "success": False,
                "error": str(e),
            }

    # Run async code in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_stats())
                return future.result()
        else:
            return loop.run_until_complete(_get_stats())
    except RuntimeError:
        return asyncio.run(_get_stats())


@function_tool
def get_campaign_metrics(
    start_date: str = "",
    end_date: str = "",
) -> str:
    """Get email campaign delivery metrics from SendGrid.

    Retrieves delivery, open, click, and bounce statistics
    for emails sent during the specified date range.

    Args:
        start_date: Start date in YYYY-MM-DD format. Empty for default (30 days ago).
        end_date: End date in YYYY-MM-DD format. Empty for default (today).

    Returns:
        JSON string containing:
        - metrics: CampaignMetrics dict with:
            - total_sent: Number of emails sent
            - delivered: Number delivered
            - opened: Number opened (unique)
            - clicked: Number clicked (unique)
            - bounced: Number bounced
            - spam_reports: Number of spam complaints
            - delivery_rate: Percentage delivered
            - open_rate: Percentage opened
            - click_rate: Percentage clicked
            - bounce_rate: Percentage bounced
        - start_date: Query start date
        - end_date: Query end date
        - success: Whether retrieval was successful
        - error: Error message if failed

    Example:
        >>> metrics_json = get_campaign_metrics("2024-01-01", "2024-01-31")
        >>> import json; metrics = json.loads(metrics_json)
        >>> print(f"Open rate: {metrics['metrics']['open_rate']}%")
    """
    result = _get_email_stats_internal(
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
    )
    return json.dumps(result)


def _check_email_suppression_internal(email: str) -> dict[str, Any]:
    """Internal implementation for checking if an email is suppressed.

    Args:
        email: Email address to check.

    Returns:
        Dictionary with suppression status.
    """
    from integrations.sendgrid import SendGridClient

    logger.info("Checking suppression for: %s", email)

    async def _check() -> dict[str, Any]:
        """Async suppression check."""
        try:
            async with SendGridClient() as client:
                is_suppressed = await client.check_suppression(email)

                return {
                    "email": email,
                    "is_suppressed": is_suppressed,
                    "should_send": not is_suppressed,
                    "success": True,
                    "error": None,
                }

        except ValueError as e:
            return {
                "email": email,
                "is_suppressed": False,
                "should_send": False,
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            logger.error("Error checking suppression: %s", e)
            return {
                "email": email,
                "is_suppressed": False,
                "should_send": False,
                "success": False,
                "error": str(e),
            }

    # Run async code in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _check())
                return future.result()
        else:
            return loop.run_until_complete(_check())
    except RuntimeError:
        return asyncio.run(_check())


@function_tool
def check_email_deliverability(email: str) -> str:
    """Check if an email address is safe to send to.

    Checks the SendGrid suppression list for bounces, spam reports,
    and unsubscribes. Use before sending to avoid damaging sender reputation.

    Args:
        email: Email address to check.

    Returns:
        JSON string containing:
        - email: The email address checked
        - is_suppressed: Whether email is on suppression list
        - should_send: Whether it's safe to send (inverse of is_suppressed)
        - success: Whether check was successful
        - error: Error message if failed

    Example:
        >>> result_json = check_email_deliverability("test@example.com")
        >>> import json; result = json.loads(result_json)
        >>> if result['should_send']:
        ...     print("Safe to send email")
    """
    result = _check_email_suppression_internal(email)
    return json.dumps(result)


def _get_bounce_list_internal(limit: int = 100) -> dict[str, Any]:
    """Internal implementation for getting bounced email list.

    Args:
        limit: Maximum number of records to return.

    Returns:
        Dictionary with bounce records.
    """
    from integrations.sendgrid import SendGridClient

    logger.info("Getting bounce list: limit=%d", limit)

    async def _get_bounces() -> dict[str, Any]:
        """Async bounce list retrieval."""
        try:
            async with SendGridClient() as client:
                bounces = await client.get_bounces(limit=limit)

                return {
                    "bounces": [b.to_dict() for b in bounces],
                    "count": len(bounces),
                    "success": True,
                    "error": None,
                }

        except ValueError as e:
            return {
                "bounces": [],
                "count": 0,
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            logger.error("Error getting bounces: %s", e)
            return {
                "bounces": [],
                "count": 0,
                "success": False,
                "error": str(e),
            }

    # Run async code in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_bounces())
                return future.result()
        else:
            return loop.run_until_complete(_get_bounces())
    except RuntimeError:
        return asyncio.run(_get_bounces())


@function_tool
def get_bounced_emails(limit: int = 100) -> str:
    """Get list of bounced email addresses.

    Retrieves emails that have bounced to help maintain list hygiene
    and avoid sending to invalid addresses.

    Args:
        limit: Maximum number of bounce records to return. Default 100.

    Returns:
        JSON string containing:
        - bounces: Array of bounce records with:
            - email: Bounced email address
            - bounce_type: Type of bounce (hard, soft, block)
            - reason: Bounce reason message
            - timestamp: When bounce occurred
        - count: Number of records returned
        - success: Whether retrieval was successful
        - error: Error message if failed

    Example:
        >>> bounces_json = get_bounced_emails(50)
        >>> import json; data = json.loads(bounces_json)
        >>> print(f"Found {data['count']} bounced emails")
    """
    result = _get_bounce_list_internal(limit)
    return json.dumps(result)


# Agent instructions defining behavior and constraints
SALES_AGENT_INSTRUCTIONS = """You are a Sales Agent specialized in cold email outreach campaigns.

Your primary task is to send personalized cold emails to business leads and track campaign performance.

## Your Capabilities

1. **Generate and Send Cold Emails**
   - Use `generate_and_send_cold_email` for individual lead emails
   - Personalize with business name, industry, and demo URL
   - Choose appropriate email style (humorous, professional, direct, curiosity)
   - Select A/B test variants for optimization

2. **Batch Campaign Sending**
   - Use `send_campaign_emails` for sending to multiple leads
   - Process arrays of leads efficiently
   - Track success/failure rates for the batch

3. **Campaign Metrics**
   - Use `get_campaign_metrics` to check delivery performance
   - Monitor open rates, click rates, bounce rates
   - Identify campaign health issues

4. **Deliverability Management**
   - Use `check_email_deliverability` before sending to new addresses
   - Use `get_bounced_emails` to identify problem addresses
   - Maintain sender reputation by avoiding suppressed addresses

## Best Practices

1. **Email Style Selection**
   - Use "humorous" (default) for most cold outreach - it stands out
   - Use "professional" for more conservative industries (legal, medical)
   - Use "direct" when brevity is valued
   - Use "curiosity" for A/B testing engagement

2. **A/B Testing**
   - Rotate variants A, B, C to test subject lines
   - Track which variants get better open/click rates
   - Report findings for campaign optimization

3. **CAN-SPAM Compliance**
   - All emails automatically include required footer
   - Never remove or hide unsubscribe links
   - Ensure sender address is valid and monitored

4. **List Hygiene**
   - Check deliverability before large campaigns
   - Remove bounced addresses from future sends
   - Monitor spam complaint rates

5. **Timing and Pacing**
   - Don't send too many emails too quickly
   - Allow for proper tracking between batches
   - Monitor delivery rates for warmup domains

## Output Format

When reporting results, always include:
- Number of emails sent successfully vs failed
- Key metrics (delivery rate, open rate if available)
- Any errors or issues encountered
- Recommendations for improvement

## Important Notes

- Always validate email addresses before sending
- Track lead_id with each send for proper attribution
- Monitor bounce rates to protect sender reputation
- Include demo_url in every cold email
- Personalization significantly improves engagement
"""

# Create the sales agent instance
sales_agent = Agent(
    name="Sales Agent",
    instructions=SALES_AGENT_INSTRUCTIONS,
    tools=[
        generate_and_send_cold_email,
        send_campaign_emails,
        get_campaign_metrics,
        check_email_deliverability,
        get_bounced_emails,
    ],
)
