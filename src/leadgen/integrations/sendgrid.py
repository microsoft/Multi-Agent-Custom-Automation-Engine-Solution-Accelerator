"""SendGrid email delivery client with tracking and CAN-SPAM compliance.

This module provides a client wrapper for SendGrid email delivery with
comprehensive tracking capabilities and CAN-SPAM compliance features.

Features:
- Email delivery with HTML and plain text support
- Open and click tracking
- Delivery status tracking
- Bounce and spam complaint handling
- CAN-SPAM compliant footer injection
- Batch email sending
- Email validation

Usage:
    >>> client = SendGridClient()
    >>> result = await client.send_email(
    ...     to_email="prospect@example.com",
    ...     from_email="sales@company.com",
    ...     subject="Check out your personalized demo!",
    ...     html_content="<html>...</html>",
    ...     tracking_id="lead_12345",
    ... )
    >>> print(result.message_id)
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail,
    Attachment,
    Asm,
    Category,
    ClickTracking,
    Content,
    CustomArg,
    Email,
    OpenTracking,
    Personalization,
    TrackingSettings,
    SubscriptionTracking,
)

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT_SECONDS = 30
MAX_BATCH_SIZE = 1000  # SendGrid limit per API call
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# CAN-SPAM compliant footer template
CAN_SPAM_FOOTER_HTML = """
<div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0; font-size: 12px; color: #666;">
    <p>{company_name}<br>
    {address_line1}<br>
    {city}, {state} {zip_code}<br>
    {country}</p>
    <p>You received this email because {reason}.</p>
    <p>To stop receiving these emails, <a href="{unsubscribe_url}" style="color: #0066cc;">unsubscribe here</a>.</p>
</div>
"""

CAN_SPAM_FOOTER_TEXT = """
--
{company_name}
{address_line1}
{city}, {state} {zip_code}
{country}

You received this email because {reason}.
To stop receiving these emails, visit: {unsubscribe_url}
"""


class EmailStatus(str, Enum):
    """Email delivery status values."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    SPAM_REPORT = "spam_report"
    UNSUBSCRIBED = "unsubscribed"
    DROPPED = "dropped"
    DEFERRED = "deferred"
    FAILED = "failed"


class BounceType(str, Enum):
    """Types of email bounces."""

    HARD = "hard"  # Permanent delivery failure
    SOFT = "soft"  # Temporary delivery failure
    BLOCK = "block"  # Blocked by recipient server


class SendGridError(Exception):
    """Base exception for SendGrid errors."""

    pass


class SendGridAuthError(SendGridError):
    """Raised when SendGrid authentication fails."""

    pass


class SendGridRateLimitError(SendGridError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class SendGridValidationError(SendGridError):
    """Raised when email validation fails."""

    pass


class SendGridDeliveryError(SendGridError):
    """Raised when email delivery fails."""

    pass


@dataclass
class EmailAddress:
    """Represents an email address with optional name.

    Attributes:
        email: Email address.
        name: Optional display name.
    """

    email: str
    name: Optional[str] = None

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


@dataclass
class CANSpamInfo:
    """CAN-SPAM compliance information.

    Attributes:
        company_name: Name of the sending company.
        address_line1: Street address.
        city: City name.
        state: State/province.
        zip_code: Postal/ZIP code.
        country: Country name.
        reason: Reason the recipient is receiving the email.
        unsubscribe_url: URL for unsubscribing.
    """

    company_name: str
    address_line1: str
    city: str
    state: str
    zip_code: str
    country: str = "USA"
    reason: str = "you expressed interest in our services"
    unsubscribe_url: str = "{{unsubscribe}}"

    def get_html_footer(self) -> str:
        """Generate CAN-SPAM compliant HTML footer."""
        return CAN_SPAM_FOOTER_HTML.format(
            company_name=self.company_name,
            address_line1=self.address_line1,
            city=self.city,
            state=self.state,
            zip_code=self.zip_code,
            country=self.country,
            reason=self.reason,
            unsubscribe_url=self.unsubscribe_url,
        )

    def get_text_footer(self) -> str:
        """Generate CAN-SPAM compliant plain text footer."""
        return CAN_SPAM_FOOTER_TEXT.format(
            company_name=self.company_name,
            address_line1=self.address_line1,
            city=self.city,
            state=self.state,
            zip_code=self.zip_code,
            country=self.country,
            reason=self.reason,
            unsubscribe_url=self.unsubscribe_url,
        )


@dataclass
class SendResult:
    """Result of sending an email.

    Attributes:
        message_id: SendGrid message ID for tracking.
        to_email: Recipient email address.
        status: Current delivery status.
        status_code: HTTP status code from API.
        tracking_id: Custom tracking ID (e.g., lead_id).
        sent_at: Timestamp when email was sent.
        success: Whether send operation succeeded.
        error: Error message if send failed.
    """

    message_id: Optional[str]
    to_email: str
    status: EmailStatus = EmailStatus.PENDING
    status_code: int = 0
    tracking_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "message_id": self.message_id,
            "to_email": self.to_email,
            "status": self.status.value,
            "status_code": self.status_code,
            "tracking_id": self.tracking_id,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "success": self.success,
            "error": self.error,
        }

    @property
    def is_delivered(self) -> bool:
        """Check if email was successfully delivered."""
        return self.status in [
            EmailStatus.DELIVERED,
            EmailStatus.OPENED,
            EmailStatus.CLICKED,
        ]


@dataclass
class BatchSendResult:
    """Result of sending a batch of emails.

    Attributes:
        total: Total number of emails attempted.
        successful: Number of successful sends.
        failed: Number of failed sends.
        results: Individual results for each email.
    """

    total: int
    successful: int = 0
    failed: int = 0
    results: list[SendResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total": self.total,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": self.successful / self.total if self.total > 0 else 0,
            "results": [r.to_dict() for r in self.results],
        }

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.successful / self.total) * 100


@dataclass
class EmailStats:
    """Email delivery statistics.

    Attributes:
        sent: Number of emails sent.
        delivered: Number of emails delivered.
        opened: Number of emails opened.
        clicked: Number of links clicked.
        bounced: Number of bounced emails.
        spam_reports: Number of spam reports.
        unsubscribes: Number of unsubscribes.
    """

    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    bounced: int = 0
    spam_reports: int = 0
    unsubscribes: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "sent": self.sent,
            "delivered": self.delivered,
            "opened": self.opened,
            "clicked": self.clicked,
            "bounced": self.bounced,
            "spam_reports": self.spam_reports,
            "unsubscribes": self.unsubscribes,
            "delivery_rate": self.delivery_rate,
            "open_rate": self.open_rate,
            "click_rate": self.click_rate,
            "bounce_rate": self.bounce_rate,
        }

    @property
    def delivery_rate(self) -> float:
        """Calculate delivery rate as percentage."""
        if self.sent == 0:
            return 0.0
        return (self.delivered / self.sent) * 100

    @property
    def open_rate(self) -> float:
        """Calculate open rate as percentage of delivered."""
        if self.delivered == 0:
            return 0.0
        return (self.opened / self.delivered) * 100

    @property
    def click_rate(self) -> float:
        """Calculate click rate as percentage of opened."""
        if self.opened == 0:
            return 0.0
        return (self.clicked / self.opened) * 100

    @property
    def bounce_rate(self) -> float:
        """Calculate bounce rate as percentage of sent."""
        if self.sent == 0:
            return 0.0
        return (self.bounced / self.sent) * 100


@dataclass
class BounceRecord:
    """Record of a bounced email.

    Attributes:
        email: Bounced email address.
        bounce_type: Type of bounce (hard, soft, block).
        reason: Reason for the bounce.
        timestamp: When the bounce occurred.
        status_code: SMTP status code.
    """

    email: str
    bounce_type: BounceType
    reason: str
    timestamp: datetime
    status_code: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "email": self.email,
            "bounce_type": self.bounce_type.value,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "status_code": self.status_code,
        }


class SendGridClient:
    """Client for SendGrid email delivery with tracking.

    Provides methods for sending emails, managing tracking,
    and ensuring CAN-SPAM compliance for cold email campaigns.

    Attributes:
        api_key: SendGrid API key.
        default_from: Default sender email address.
        default_can_spam: Default CAN-SPAM compliance info.

    Example:
        >>> client = SendGridClient()
        >>> result = await client.send_email(
        ...     to_email="prospect@example.com",
        ...     from_email="sales@company.com",
        ...     subject="Your personalized AI receptionist demo",
        ...     html_content="<html>...</html>",
        ...     tracking_id="lead_12345",
        ... )
        >>> print(f"Sent email with ID: {result.message_id}")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_from_email: Optional[str] = None,
        default_from_name: Optional[str] = None,
        default_can_spam: Optional[CANSpamInfo] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize SendGrid client.

        Args:
            api_key: SendGrid API key. Defaults to SENDGRID_API_KEY env var.
            default_from_email: Default sender email. Defaults to SENDGRID_FROM_EMAIL env var.
            default_from_name: Default sender name. Defaults to SENDGRID_FROM_NAME env var.
            default_can_spam: Default CAN-SPAM compliance info.
            timeout_seconds: Request timeout in seconds. Defaults to 30.

        Raises:
            ValueError: If API key is not provided.
        """
        self.api_key = api_key or os.environ.get("SENDGRID_API_KEY")
        if not self.api_key:
            raise ValueError(
                "SendGrid API key required. Set SENDGRID_API_KEY environment "
                "variable or pass api_key parameter."
            )

        self.default_from = EmailAddress(
            email=default_from_email or os.environ.get("SENDGRID_FROM_EMAIL", ""),
            name=default_from_name or os.environ.get("SENDGRID_FROM_NAME"),
        )

        self.default_can_spam = default_can_spam
        self.timeout_seconds = timeout_seconds

        self._client = SendGridAPIClient(api_key=self.api_key)
        logger.info(
            "SendGridClient initialized (from_email=%s)",
            self.default_from.email or "not set",
        )

    def validate_email(self, email: str) -> bool:
        """Validate email address format.

        Args:
            email: Email address to validate.

        Returns:
            True if email format is valid, False otherwise.
        """
        if not email or not isinstance(email, str):
            return False
        return bool(EMAIL_REGEX.match(email.strip()))

    def _build_mail(
        self,
        to_email: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        subject: str = "",
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        reply_to: Optional[str] = None,
        categories: Optional[list[str]] = None,
        custom_args: Optional[dict[str, str]] = None,
        can_spam_info: Optional[CANSpamInfo] = None,
        enable_tracking: bool = True,
        unsubscribe_group_id: Optional[int] = None,
    ) -> Mail:
        """Build SendGrid Mail object.

        Args:
            to_email: Recipient email address.
            from_email: Sender email address.
            from_name: Sender display name.
            subject: Email subject line.
            html_content: HTML body content.
            text_content: Plain text body content.
            reply_to: Reply-to email address.
            categories: List of categories for tracking.
            custom_args: Custom arguments for webhook tracking.
            can_spam_info: CAN-SPAM compliance info.
            enable_tracking: Enable open/click tracking.
            unsubscribe_group_id: SendGrid unsubscribe group ID.

        Returns:
            Configured Mail object.
        """
        # Resolve from address
        sender_email = from_email or self.default_from.email
        sender_name = from_name or self.default_from.name

        if not sender_email:
            raise SendGridValidationError(
                "From email required. Set SENDGRID_FROM_EMAIL or pass from_email."
            )

        # Create mail object
        mail = Mail()

        # Set from address
        mail.from_email = Email(sender_email, sender_name)

        # Set to address
        personalization = Personalization()
        personalization.add_to(Email(to_email))

        # Add custom args for tracking
        if custom_args:
            for key, value in custom_args.items():
                personalization.add_custom_arg(CustomArg(key, value))

        mail.add_personalization(personalization)

        # Set subject
        mail.subject = subject

        # Apply CAN-SPAM footer if provided
        can_spam = can_spam_info or self.default_can_spam

        # Add content with CAN-SPAM footer
        if text_content:
            final_text = text_content
            if can_spam:
                final_text += can_spam.get_text_footer()
            mail.add_content(Content("text/plain", final_text))

        if html_content:
            final_html = html_content
            if can_spam:
                # Insert footer before closing body tag if present
                if "</body>" in final_html.lower():
                    footer = can_spam.get_html_footer()
                    final_html = final_html.replace("</body>", f"{footer}</body>")
                    final_html = final_html.replace("</BODY>", f"{footer}</BODY>")
                else:
                    final_html += can_spam.get_html_footer()
            mail.add_content(Content("text/html", final_html))

        # Set reply-to
        if reply_to:
            mail.reply_to = Email(reply_to)

        # Add categories for tracking
        if categories:
            for cat in categories:
                mail.add_category(Category(cat))

        # Configure tracking settings
        if enable_tracking:
            tracking = TrackingSettings()
            tracking.click_tracking = ClickTracking(enable=True, enable_text=True)
            tracking.open_tracking = OpenTracking(enable=True)

            # Add subscription tracking if group ID provided
            if unsubscribe_group_id:
                tracking.subscription_tracking = SubscriptionTracking(
                    enable=True,
                    substitution_tag="{{unsubscribe}}",
                )
                mail.asm = Asm(group_id=unsubscribe_group_id)

            mail.tracking_settings = tracking

        return mail

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        categories: Optional[list[str]] = None,
        tracking_id: Optional[str] = None,
        can_spam_info: Optional[CANSpamInfo] = None,
        enable_tracking: bool = True,
        unsubscribe_group_id: Optional[int] = None,
    ) -> SendResult:
        """Send a single email.

        Args:
            to_email: Recipient email address.
            subject: Email subject line.
            html_content: HTML body content.
            text_content: Plain text body content.
            from_email: Sender email address.
            from_name: Sender display name.
            reply_to: Reply-to email address.
            categories: List of categories for tracking.
            tracking_id: Custom tracking ID (e.g., lead_id).
            can_spam_info: CAN-SPAM compliance info.
            enable_tracking: Enable open/click tracking.
            unsubscribe_group_id: SendGrid unsubscribe group ID.

        Returns:
            SendResult with delivery status and message ID.

        Raises:
            SendGridValidationError: If email validation fails.
            SendGridDeliveryError: If email delivery fails.
        """
        logger.info("Sending email to %s (tracking_id=%s)", to_email, tracking_id)

        # Validate email
        if not self.validate_email(to_email):
            return SendResult(
                message_id=None,
                to_email=to_email,
                status=EmailStatus.FAILED,
                tracking_id=tracking_id,
                success=False,
                error=f"Invalid email address: {to_email}",
            )

        # Require at least one content type
        if not html_content and not text_content:
            return SendResult(
                message_id=None,
                to_email=to_email,
                status=EmailStatus.FAILED,
                tracking_id=tracking_id,
                success=False,
                error="Either html_content or text_content is required",
            )

        try:
            # Build custom args for webhook tracking
            custom_args = {}
            if tracking_id:
                custom_args["tracking_id"] = tracking_id

            # Build mail object
            mail = self._build_mail(
                to_email=to_email,
                from_email=from_email,
                from_name=from_name,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                reply_to=reply_to,
                categories=categories,
                custom_args=custom_args,
                can_spam_info=can_spam_info,
                enable_tracking=enable_tracking,
                unsubscribe_group_id=unsubscribe_group_id,
            )

            # Send email asynchronously
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.send(mail),
            )

            # Parse response
            status_code = response.status_code
            message_id = None

            # Extract message ID from headers
            if hasattr(response, "headers"):
                message_id = response.headers.get("X-Message-Id")

            # Determine status based on response code
            if status_code in [200, 201, 202]:
                status = EmailStatus.SENT
                success = True
                error = None
            else:
                status = EmailStatus.FAILED
                success = False
                error = f"SendGrid returned status code {status_code}"

            result = SendResult(
                message_id=message_id,
                to_email=to_email,
                status=status,
                status_code=status_code,
                tracking_id=tracking_id,
                sent_at=datetime.now(timezone.utc) if success else None,
                success=success,
                error=error,
            )

            logger.info(
                "Email sent: to=%s, message_id=%s, status=%s",
                to_email,
                message_id,
                status.value,
            )

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to send email to %s: %s", to_email, error_msg)

            # Determine error type
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise SendGridAuthError(f"Authentication failed: {error_msg}") from e
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                retry_after = None
                # Try to extract retry-after header
                raise SendGridRateLimitError(
                    f"Rate limit exceeded: {error_msg}",
                    retry_after=retry_after,
                ) from e
            else:
                return SendResult(
                    message_id=None,
                    to_email=to_email,
                    status=EmailStatus.FAILED,
                    tracking_id=tracking_id,
                    success=False,
                    error=error_msg,
                )

    async def send_batch(
        self,
        recipients: list[dict[str, Any]],
        subject: str,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        categories: Optional[list[str]] = None,
        can_spam_info: Optional[CANSpamInfo] = None,
        enable_tracking: bool = True,
        batch_size: int = 100,
    ) -> BatchSendResult:
        """Send emails to multiple recipients.

        Each recipient can have personalized fields that get merged
        into the email content.

        Args:
            recipients: List of recipient dicts with 'email' and optional 'name', 'tracking_id'.
            subject: Email subject line (can include personalization tokens).
            html_content: HTML body content (can include personalization tokens).
            text_content: Plain text body content.
            from_email: Sender email address.
            from_name: Sender display name.
            categories: List of categories for tracking.
            can_spam_info: CAN-SPAM compliance info.
            enable_tracking: Enable open/click tracking.
            batch_size: Number of emails to send concurrently.

        Returns:
            BatchSendResult with summary and individual results.

        Example:
            >>> recipients = [
            ...     {"email": "john@example.com", "name": "John", "tracking_id": "lead_1"},
            ...     {"email": "jane@example.com", "name": "Jane", "tracking_id": "lead_2"},
            ... ]
            >>> result = await client.send_batch(
            ...     recipients=recipients,
            ...     subject="Hello {{name}}!",
            ...     html_content="<p>Hi {{name}}, check out your demo!</p>",
            ... )
        """
        logger.info("Sending batch email to %d recipients", len(recipients))

        if len(recipients) > MAX_BATCH_SIZE:
            logger.warning(
                "Batch size %d exceeds max %d, will process in chunks",
                len(recipients),
                MAX_BATCH_SIZE,
            )

        results: list[SendResult] = []
        successful = 0
        failed = 0

        # Process in batches
        for i in range(0, len(recipients), batch_size):
            batch = recipients[i : i + batch_size]

            # Create tasks for concurrent sending
            tasks = []
            for recipient in batch:
                email = recipient.get("email", "")
                tracking_id = recipient.get("tracking_id")

                task = self.send_email(
                    to_email=email,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                    from_email=from_email,
                    from_name=from_name,
                    categories=categories,
                    tracking_id=tracking_id,
                    can_spam_info=can_spam_info,
                    enable_tracking=enable_tracking,
                )
                tasks.append(task)

            # Execute batch concurrently
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    results.append(
                        SendResult(
                            message_id=None,
                            to_email="unknown",
                            status=EmailStatus.FAILED,
                            success=False,
                            error=str(result),
                        )
                    )
                    failed += 1
                elif isinstance(result, SendResult):
                    results.append(result)
                    if result.success:
                        successful += 1
                    else:
                        failed += 1

            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(recipients):
                await asyncio.sleep(0.1)

        batch_result = BatchSendResult(
            total=len(recipients),
            successful=successful,
            failed=failed,
            results=results,
        )

        logger.info(
            "Batch send complete: total=%d, successful=%d, failed=%d, rate=%.1f%%",
            batch_result.total,
            batch_result.successful,
            batch_result.failed,
            batch_result.success_rate,
        )

        return batch_result

    async def get_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        aggregated_by: str = "day",
    ) -> EmailStats:
        """Get email delivery statistics.

        Args:
            start_date: Start date for stats. Defaults to 30 days ago.
            end_date: End date for stats. Defaults to today.
            aggregated_by: Aggregation period ('day', 'week', 'month').

        Returns:
            EmailStats with delivery metrics.

        Note:
            This method requires access to SendGrid's Stats API.
        """
        logger.info("Getting email stats (aggregated_by=%s)", aggregated_by)

        loop = asyncio.get_event_loop()

        try:
            # Build query parameters
            params = {"aggregated_by": aggregated_by}

            if start_date:
                params["start_date"] = start_date.strftime("%Y-%m-%d")
            if end_date:
                params["end_date"] = end_date.strftime("%Y-%m-%d")

            # Make API request
            response = await loop.run_in_executor(
                None,
                lambda: self._client.client.stats.get(query_params=params),
            )

            # Parse response
            stats = EmailStats()

            if response.status_code == 200:
                import json

                data = json.loads(response.body)

                for day_stats in data:
                    if "stats" in day_stats:
                        for stat_block in day_stats["stats"]:
                            metrics = stat_block.get("metrics", {})
                            stats.sent += metrics.get("requests", 0)
                            stats.delivered += metrics.get("delivered", 0)
                            stats.opened += metrics.get("unique_opens", 0)
                            stats.clicked += metrics.get("unique_clicks", 0)
                            stats.bounced += metrics.get("bounces", 0)
                            stats.spam_reports += metrics.get("spam_reports", 0)
                            stats.unsubscribes += metrics.get("unsubscribes", 0)

            logger.info(
                "Retrieved stats: sent=%d, delivered=%d, opened=%d",
                stats.sent,
                stats.delivered,
                stats.opened,
            )

            return stats

        except Exception as e:
            logger.error("Failed to get stats: %s", str(e))
            return EmailStats()

    async def get_bounces(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[BounceRecord]:
        """Get list of bounced emails.

        Args:
            start_time: Start time for bounce lookup.
            end_time: End time for bounce lookup.
            limit: Maximum number of records to return.

        Returns:
            List of BounceRecord objects.

        Note:
            This method requires access to SendGrid's Suppressions API.
        """
        logger.info("Getting bounces (limit=%d)", limit)

        loop = asyncio.get_event_loop()

        try:
            params = {"limit": limit}

            if start_time:
                params["start_time"] = int(start_time.timestamp())
            if end_time:
                params["end_time"] = int(end_time.timestamp())

            response = await loop.run_in_executor(
                None,
                lambda: self._client.client.suppression.bounces.get(query_params=params),
            )

            bounces: list[BounceRecord] = []

            if response.status_code == 200:
                import json

                data = json.loads(response.body)

                for bounce in data:
                    bounce_type = BounceType.HARD
                    if "soft" in bounce.get("reason", "").lower():
                        bounce_type = BounceType.SOFT
                    elif "block" in bounce.get("reason", "").lower():
                        bounce_type = BounceType.BLOCK

                    bounces.append(
                        BounceRecord(
                            email=bounce.get("email", ""),
                            bounce_type=bounce_type,
                            reason=bounce.get("reason", ""),
                            timestamp=datetime.fromtimestamp(
                                bounce.get("created", 0), tz=timezone.utc
                            ),
                            status_code=bounce.get("status"),
                        )
                    )

            logger.info("Retrieved %d bounce records", len(bounces))
            return bounces

        except Exception as e:
            logger.error("Failed to get bounces: %s", str(e))
            return []

    async def add_to_suppression_list(self, email: str) -> bool:
        """Add email to global suppression list.

        Use this to prevent sending to an email address that has
        requested to unsubscribe or has bounced.

        Args:
            email: Email address to suppress.

        Returns:
            True if successfully added, False otherwise.
        """
        logger.info("Adding %s to suppression list", email)

        loop = asyncio.get_event_loop()

        try:
            response = await loop.run_in_executor(
                None,
                lambda: self._client.client.asm.suppressions._("global").post(
                    request_body={"recipient_emails": [email]}
                ),
            )

            success = response.status_code in [200, 201]

            if success:
                logger.info("Added %s to suppression list", email)
            else:
                logger.warning(
                    "Failed to add %s to suppression list: %s",
                    email,
                    response.body,
                )

            return success

        except Exception as e:
            logger.error("Failed to add to suppression list: %s", str(e))
            return False

    async def check_suppression(self, email: str) -> bool:
        """Check if email is on suppression list.

        Args:
            email: Email address to check.

        Returns:
            True if email is suppressed, False otherwise.
        """
        logger.info("Checking suppression for %s", email)

        loop = asyncio.get_event_loop()

        try:
            response = await loop.run_in_executor(
                None,
                lambda: self._client.client.suppression.bounces._(email).get(),
            )

            # If we get a 200, the email is on the bounce list
            if response.status_code == 200:
                import json

                data = json.loads(response.body)
                return len(data) > 0

            return False

        except Exception as e:
            logger.error("Failed to check suppression: %s", str(e))
            return False

    def close(self) -> None:
        """Clean up client resources."""
        logger.info("SendGridClient closed")

    async def __aenter__(self) -> "SendGridClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        self.close()
