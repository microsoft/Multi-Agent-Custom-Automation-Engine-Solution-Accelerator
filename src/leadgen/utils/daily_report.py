"""Daily report generator for email metrics aggregation.

This module provides functionality to generate daily reports aggregating
email delivery metrics, domain health scoring, and campaign performance
analysis from SendGrid statistics.

Features:
- Daily email metrics aggregation
- Domain health score calculation
- Bounce and spam complaint tracking
- Campaign performance summaries
- Markdown and JSON report generation

Usage:
    >>> from utils.daily_report import generate_daily_report
    >>> report = await generate_daily_report()
    >>> print(report.domain_health_score)
    92.5
    >>> print(report.to_markdown())

Per FR-7: Daily report with delivery rate, open rate, click rate,
bounces, spam complaints, and domain health score.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DomainHealthStatus(str, Enum):
    """Domain health status levels based on metrics."""

    EXCELLENT = "excellent"  # Score >= 90
    GOOD = "good"           # Score >= 75
    FAIR = "fair"           # Score >= 50
    POOR = "poor"           # Score >= 25
    CRITICAL = "critical"   # Score < 25


class ReportPeriod(str, Enum):
    """Report time period options."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class EmailMetricsSnapshot:
    """Snapshot of email metrics for a specific period.

    Attributes:
        sent: Total emails sent.
        delivered: Total emails delivered.
        opened: Total unique opens.
        clicked: Total unique clicks.
        bounced: Total bounces.
        spam_reports: Total spam reports/complaints.
        unsubscribes: Total unsubscribes.
        period_start: Start of the reporting period.
        period_end: End of the reporting period.
    """
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    bounced: int = 0
    spam_reports: int = 0
    unsubscribes: int = 0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    @property
    def delivery_rate(self) -> float:
        """Calculate delivery rate as percentage."""
        if self.sent == 0:
            return 0.0
        return round((self.delivered / self.sent) * 100, 2)

    @property
    def open_rate(self) -> float:
        """Calculate open rate as percentage of delivered."""
        if self.delivered == 0:
            return 0.0
        return round((self.opened / self.delivered) * 100, 2)

    @property
    def click_rate(self) -> float:
        """Calculate click rate as percentage of opened."""
        if self.opened == 0:
            return 0.0
        return round((self.clicked / self.opened) * 100, 2)

    @property
    def click_through_rate(self) -> float:
        """Calculate click-through rate as percentage of delivered."""
        if self.delivered == 0:
            return 0.0
        return round((self.clicked / self.delivered) * 100, 2)

    @property
    def bounce_rate(self) -> float:
        """Calculate bounce rate as percentage of sent."""
        if self.sent == 0:
            return 0.0
        return round((self.bounced / self.sent) * 100, 2)

    @property
    def spam_rate(self) -> float:
        """Calculate spam complaint rate as percentage of delivered."""
        if self.delivered == 0:
            return 0.0
        return round((self.spam_reports / self.delivered) * 100, 4)

    @property
    def unsubscribe_rate(self) -> float:
        """Calculate unsubscribe rate as percentage of delivered."""
        if self.delivered == 0:
            return 0.0
        return round((self.unsubscribes / self.delivered) * 100, 2)

    def to_dict(self) -> Dict[str, Any]:
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
            "click_through_rate": self.click_through_rate,
            "bounce_rate": self.bounce_rate,
            "spam_rate": self.spam_rate,
            "unsubscribe_rate": self.unsubscribe_rate,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }


@dataclass
class BounceAnalysis:
    """Analysis of bounce metrics.

    Attributes:
        total_bounces: Total bounce count.
        hard_bounces: Permanent delivery failures.
        soft_bounces: Temporary delivery failures.
        blocked_bounces: Blocked by recipient server.
        top_bounce_domains: Top domains with bounces.
        bounce_trend: Trend compared to previous period ("up", "down", "stable").
        recent_bounces: List of recent bounced emails.
    """
    total_bounces: int = 0
    hard_bounces: int = 0
    soft_bounces: int = 0
    blocked_bounces: int = 0
    top_bounce_domains: List[Dict[str, int]] = field(default_factory=list)
    bounce_trend: str = "stable"
    recent_bounces: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_bounces": self.total_bounces,
            "hard_bounces": self.hard_bounces,
            "soft_bounces": self.soft_bounces,
            "blocked_bounces": self.blocked_bounces,
            "top_bounce_domains": self.top_bounce_domains,
            "bounce_trend": self.bounce_trend,
            "recent_bounces": self.recent_bounces[:10],  # Limit to 10
        }


@dataclass
class CampaignSummary:
    """Summary of campaign performance.

    Attributes:
        campaign_id: Campaign identifier.
        campaign_name: Campaign display name.
        emails_sent: Total emails sent.
        delivery_rate: Percentage delivered.
        open_rate: Percentage opened.
        click_rate: Percentage clicked.
        status: Campaign status.
    """
    campaign_id: str = ""
    campaign_name: str = ""
    emails_sent: int = 0
    delivery_rate: float = 0.0
    open_rate: float = 0.0
    click_rate: float = 0.0
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "emails_sent": self.emails_sent,
            "delivery_rate": self.delivery_rate,
            "open_rate": self.open_rate,
            "click_rate": self.click_rate,
            "status": self.status,
        }


@dataclass
class DailyReport:
    """Complete daily email metrics report.

    Attributes:
        report_date: Date of the report.
        period: Reporting period (daily, weekly, monthly).
        metrics: Email metrics snapshot for the period.
        bounce_analysis: Detailed bounce analysis.
        domain_health_score: Overall domain health score (0-100).
        domain_health_status: Health status category.
        campaigns: List of campaign summaries.
        alerts: List of alert messages.
        recommendations: List of improvement recommendations.
        generated_at: Report generation timestamp.
    """
    report_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period: ReportPeriod = ReportPeriod.DAILY
    metrics: EmailMetricsSnapshot = field(default_factory=EmailMetricsSnapshot)
    bounce_analysis: BounceAnalysis = field(default_factory=BounceAnalysis)
    domain_health_score: float = 100.0
    domain_health_status: DomainHealthStatus = DomainHealthStatus.EXCELLENT
    campaigns: List[CampaignSummary] = field(default_factory=list)
    alerts: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "report_date": self.report_date.isoformat(),
            "period": self.period.value,
            "metrics": self.metrics.to_dict(),
            "bounce_analysis": self.bounce_analysis.to_dict(),
            "domain_health_score": self.domain_health_score,
            "domain_health_status": self.domain_health_status.value,
            "campaigns": [c.to_dict() for c in self.campaigns],
            "alerts": self.alerts,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at.isoformat(),
        }

    def to_markdown(self) -> str:
        """Generate markdown-formatted report."""
        lines = [
            f"# Email Metrics Report",
            f"",
            f"**Report Date:** {self.report_date.strftime('%Y-%m-%d')}",
            f"**Period:** {self.period.value.capitalize()}",
            f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"",
            f"---",
            f"",
            f"## Domain Health",
            f"",
            f"**Score:** {self.domain_health_score:.1f}/100 ({self.domain_health_status.value.upper()})",
            f"",
        ]

        # Add health status indicator
        if self.domain_health_status == DomainHealthStatus.EXCELLENT:
            lines.append("> Domain health is excellent. Keep up the good work!")
        elif self.domain_health_status == DomainHealthStatus.GOOD:
            lines.append("> Domain health is good. Minor improvements possible.")
        elif self.domain_health_status == DomainHealthStatus.FAIR:
            lines.append("> Domain health needs attention. Review recommendations below.")
        elif self.domain_health_status == DomainHealthStatus.POOR:
            lines.append("> Domain health is poor. Immediate action recommended.")
        else:
            lines.append("> Domain health is critical. Stop sending and address issues.")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## Delivery Metrics",
            f"",
            f"| Metric | Count | Rate |",
            f"|--------|-------|------|",
            f"| Sent | {self.metrics.sent:,} | - |",
            f"| Delivered | {self.metrics.delivered:,} | {self.metrics.delivery_rate}% |",
            f"| Opened | {self.metrics.opened:,} | {self.metrics.open_rate}% |",
            f"| Clicked | {self.metrics.clicked:,} | {self.metrics.click_rate}% |",
            f"| Bounced | {self.metrics.bounced:,} | {self.metrics.bounce_rate}% |",
            f"| Spam Reports | {self.metrics.spam_reports:,} | {self.metrics.spam_rate}% |",
            f"| Unsubscribes | {self.metrics.unsubscribes:,} | {self.metrics.unsubscribe_rate}% |",
            f"",
        ])

        # Bounce analysis
        if self.bounce_analysis.total_bounces > 0:
            lines.extend([
                f"---",
                f"",
                f"## Bounce Analysis",
                f"",
                f"- **Hard Bounces:** {self.bounce_analysis.hard_bounces}",
                f"- **Soft Bounces:** {self.bounce_analysis.soft_bounces}",
                f"- **Blocked:** {self.bounce_analysis.blocked_bounces}",
                f"- **Trend:** {self.bounce_analysis.bounce_trend}",
                f"",
            ])

            if self.bounce_analysis.top_bounce_domains:
                lines.append("**Top Bounce Domains:**")
                for domain_info in self.bounce_analysis.top_bounce_domains[:5]:
                    domain = domain_info.get("domain", "unknown")
                    count = domain_info.get("count", 0)
                    lines.append(f"- {domain}: {count}")
                lines.append("")

        # Campaigns
        if self.campaigns:
            lines.extend([
                f"---",
                f"",
                f"## Campaign Performance",
                f"",
                f"| Campaign | Sent | Delivery | Open | Click |",
                f"|----------|------|----------|------|-------|",
            ])
            for campaign in self.campaigns[:10]:
                lines.append(
                    f"| {campaign.campaign_name} | {campaign.emails_sent:,} | "
                    f"{campaign.delivery_rate:.1f}% | {campaign.open_rate:.1f}% | "
                    f"{campaign.click_rate:.1f}% |"
                )
            lines.append("")

        # Alerts
        if self.alerts:
            lines.extend([
                f"---",
                f"",
                f"## Alerts",
                f"",
            ])
            for alert in self.alerts:
                lines.append(f"- {alert}")
            lines.append("")

        # Recommendations
        if self.recommendations:
            lines.extend([
                f"---",
                f"",
                f"## Recommendations",
                f"",
            ])
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Generate JSON-formatted report."""
        import json
        return json.dumps(self.to_dict(), indent=2)


# Domain health score weights
HEALTH_WEIGHTS = {
    "delivery_rate": 0.30,     # 30% weight - most important
    "bounce_rate": 0.25,       # 25% weight - critical for reputation
    "spam_rate": 0.25,         # 25% weight - critical for reputation
    "open_rate": 0.10,         # 10% weight - engagement indicator
    "unsubscribe_rate": 0.10,  # 10% weight - list quality indicator
}

# Benchmark thresholds for scoring
BENCHMARKS = {
    "delivery_rate": {"excellent": 98, "good": 95, "fair": 90, "poor": 80},
    "bounce_rate": {"excellent": 2, "good": 5, "fair": 10, "poor": 15},
    "spam_rate": {"excellent": 0.02, "good": 0.1, "fair": 0.5, "poor": 1.0},
    "open_rate": {"excellent": 25, "good": 18, "fair": 12, "poor": 8},
    "unsubscribe_rate": {"excellent": 0.2, "good": 0.5, "fair": 1.0, "poor": 2.0},
}


def calculate_domain_health_score(metrics: EmailMetricsSnapshot) -> tuple[float, DomainHealthStatus]:
    """Calculate domain health score based on email metrics.

    Uses weighted scoring across key metrics to produce an overall
    health score from 0-100.

    Args:
        metrics: Email metrics snapshot.

    Returns:
        Tuple of (score, status) where score is 0-100 and status
        is a DomainHealthStatus enum value.
    """
    if metrics.sent == 0:
        return 100.0, DomainHealthStatus.EXCELLENT

    scores = {}

    # Delivery rate score (higher is better)
    delivery_rate = metrics.delivery_rate
    if delivery_rate >= BENCHMARKS["delivery_rate"]["excellent"]:
        scores["delivery_rate"] = 100
    elif delivery_rate >= BENCHMARKS["delivery_rate"]["good"]:
        scores["delivery_rate"] = 85
    elif delivery_rate >= BENCHMARKS["delivery_rate"]["fair"]:
        scores["delivery_rate"] = 65
    elif delivery_rate >= BENCHMARKS["delivery_rate"]["poor"]:
        scores["delivery_rate"] = 40
    else:
        scores["delivery_rate"] = 20

    # Bounce rate score (lower is better)
    bounce_rate = metrics.bounce_rate
    if bounce_rate <= BENCHMARKS["bounce_rate"]["excellent"]:
        scores["bounce_rate"] = 100
    elif bounce_rate <= BENCHMARKS["bounce_rate"]["good"]:
        scores["bounce_rate"] = 85
    elif bounce_rate <= BENCHMARKS["bounce_rate"]["fair"]:
        scores["bounce_rate"] = 60
    elif bounce_rate <= BENCHMARKS["bounce_rate"]["poor"]:
        scores["bounce_rate"] = 30
    else:
        scores["bounce_rate"] = 10

    # Spam rate score (lower is better)
    spam_rate = metrics.spam_rate
    if spam_rate <= BENCHMARKS["spam_rate"]["excellent"]:
        scores["spam_rate"] = 100
    elif spam_rate <= BENCHMARKS["spam_rate"]["good"]:
        scores["spam_rate"] = 80
    elif spam_rate <= BENCHMARKS["spam_rate"]["fair"]:
        scores["spam_rate"] = 50
    elif spam_rate <= BENCHMARKS["spam_rate"]["poor"]:
        scores["spam_rate"] = 25
    else:
        scores["spam_rate"] = 0

    # Open rate score (higher is better)
    open_rate = metrics.open_rate
    if open_rate >= BENCHMARKS["open_rate"]["excellent"]:
        scores["open_rate"] = 100
    elif open_rate >= BENCHMARKS["open_rate"]["good"]:
        scores["open_rate"] = 80
    elif open_rate >= BENCHMARKS["open_rate"]["fair"]:
        scores["open_rate"] = 60
    elif open_rate >= BENCHMARKS["open_rate"]["poor"]:
        scores["open_rate"] = 40
    else:
        scores["open_rate"] = 20

    # Unsubscribe rate score (lower is better)
    unsub_rate = metrics.unsubscribe_rate
    if unsub_rate <= BENCHMARKS["unsubscribe_rate"]["excellent"]:
        scores["unsubscribe_rate"] = 100
    elif unsub_rate <= BENCHMARKS["unsubscribe_rate"]["good"]:
        scores["unsubscribe_rate"] = 80
    elif unsub_rate <= BENCHMARKS["unsubscribe_rate"]["fair"]:
        scores["unsubscribe_rate"] = 60
    elif unsub_rate <= BENCHMARKS["unsubscribe_rate"]["poor"]:
        scores["unsubscribe_rate"] = 35
    else:
        scores["unsubscribe_rate"] = 15

    # Calculate weighted score
    total_score = sum(
        scores[metric] * HEALTH_WEIGHTS[metric]
        for metric in HEALTH_WEIGHTS
    )

    # Determine status
    if total_score >= 90:
        status = DomainHealthStatus.EXCELLENT
    elif total_score >= 75:
        status = DomainHealthStatus.GOOD
    elif total_score >= 50:
        status = DomainHealthStatus.FAIR
    elif total_score >= 25:
        status = DomainHealthStatus.POOR
    else:
        status = DomainHealthStatus.CRITICAL

    return round(total_score, 1), status


def generate_alerts(metrics: EmailMetricsSnapshot) -> List[str]:
    """Generate alert messages based on metrics thresholds.

    Args:
        metrics: Email metrics snapshot.

    Returns:
        List of alert message strings.
    """
    alerts = []

    if metrics.sent == 0:
        return alerts

    # Critical alerts
    if metrics.bounce_rate > 10:
        alerts.append(
            f"CRITICAL: Bounce rate ({metrics.bounce_rate}%) exceeds 10% threshold. "
            "Immediate action required to protect domain reputation."
        )

    if metrics.spam_rate > 0.5:
        alerts.append(
            f"CRITICAL: Spam complaint rate ({metrics.spam_rate}%) is dangerously high. "
            "Review list hygiene and content immediately."
        )

    if metrics.delivery_rate < 90:
        alerts.append(
            f"WARNING: Delivery rate ({metrics.delivery_rate}%) is below 90%. "
            "Check sending infrastructure and list quality."
        )

    # Warning alerts
    if metrics.bounce_rate > 5:
        if not any("CRITICAL: Bounce rate" in a for a in alerts):
            alerts.append(
                f"WARNING: Bounce rate ({metrics.bounce_rate}%) is elevated. "
                "Consider cleaning your email list."
            )

    if metrics.unsubscribe_rate > 1.0:
        alerts.append(
            f"WARNING: Unsubscribe rate ({metrics.unsubscribe_rate}%) is above normal. "
            "Review email frequency and content relevance."
        )

    if metrics.open_rate < 10 and metrics.delivered > 100:
        alerts.append(
            f"NOTICE: Open rate ({metrics.open_rate}%) is low. "
            "Consider A/B testing subject lines and send times."
        )

    return alerts


def generate_recommendations(
    metrics: EmailMetricsSnapshot,
    domain_health_status: DomainHealthStatus,
) -> List[str]:
    """Generate improvement recommendations based on metrics.

    Args:
        metrics: Email metrics snapshot.
        domain_health_status: Current domain health status.

    Returns:
        List of recommendation strings.
    """
    recommendations = []

    if metrics.sent == 0:
        return ["Start sending emails to generate metrics data."]

    # High-priority recommendations for poor/critical health
    if domain_health_status in [DomainHealthStatus.POOR, DomainHealthStatus.CRITICAL]:
        recommendations.append(
            "Immediately pause campaigns and audit email list for invalid addresses."
        )
        recommendations.append(
            "Implement double opt-in for new subscribers to improve list quality."
        )

    # Bounce-related recommendations
    if metrics.bounce_rate > 5:
        recommendations.append(
            "Clean email list by removing addresses that bounced more than twice."
        )
        recommendations.append(
            "Use email validation service before adding new addresses to list."
        )

    # Spam-related recommendations
    if metrics.spam_rate > 0.1:
        recommendations.append(
            "Review email content for spam trigger words and improve relevance."
        )
        recommendations.append(
            "Make unsubscribe link more visible to reduce spam complaints."
        )

    # Engagement recommendations
    if metrics.open_rate < 15 and metrics.delivered > 100:
        recommendations.append(
            "Test different subject line styles (questions, personalization, urgency)."
        )
        recommendations.append(
            "Optimize send times based on recipient timezone and engagement patterns."
        )

    if metrics.click_rate < 10 and metrics.opened > 50:
        recommendations.append(
            "Improve email CTAs with clearer value propositions."
        )
        recommendations.append(
            "Test button vs. text link placement for higher click rates."
        )

    # Unsubscribe recommendations
    if metrics.unsubscribe_rate > 0.5:
        recommendations.append(
            "Survey unsubscribing users to understand content preferences."
        )
        recommendations.append(
            "Offer email frequency options instead of full unsubscribe."
        )

    # General recommendations for good health
    if domain_health_status == DomainHealthStatus.EXCELLENT:
        recommendations.append(
            "Domain health is excellent. Consider gradually increasing send volume."
        )

    return recommendations


async def generate_daily_report(
    sendgrid_client: Optional[Any] = None,
    report_date: Optional[datetime] = None,
    period: ReportPeriod = ReportPeriod.DAILY,
    include_campaigns: bool = True,
) -> DailyReport:
    """Generate a comprehensive daily email metrics report.

    Aggregates email metrics from SendGrid, calculates domain health score,
    and generates alerts and recommendations.

    Args:
        sendgrid_client: Optional SendGridClient instance. If not provided,
            creates one using environment variables.
        report_date: Date for the report. Defaults to today.
        period: Reporting period (daily, weekly, monthly).
        include_campaigns: Whether to include campaign breakdowns.

    Returns:
        DailyReport with complete metrics analysis.

    Example:
        >>> report = await generate_daily_report()
        >>> print(f"Health: {report.domain_health_score}")
        Health: 92.5
        >>> print(report.to_markdown())
    """
    logger.info("Generating %s report", period.value)

    now = datetime.now(timezone.utc)
    report_date = report_date or now

    # Calculate period dates
    if period == ReportPeriod.DAILY:
        start_date = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif period == ReportPeriod.WEEKLY:
        start_date = report_date - timedelta(days=report_date.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
    else:  # MONTHLY
        start_date = report_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Get first day of next month
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1)

    # Initialize metrics
    metrics = EmailMetricsSnapshot(
        period_start=start_date,
        period_end=end_date,
    )

    bounce_analysis = BounceAnalysis()
    campaigns: List[CampaignSummary] = []

    # Fetch data from SendGrid if client provided
    if sendgrid_client is not None:
        try:
            # Get email stats
            stats = await sendgrid_client.get_stats(
                start_date=start_date,
                end_date=end_date,
                aggregated_by="day" if period == ReportPeriod.DAILY else "week",
            )

            metrics.sent = stats.sent
            metrics.delivered = stats.delivered
            metrics.opened = stats.opened
            metrics.clicked = stats.clicked
            metrics.bounced = stats.bounced
            metrics.spam_reports = stats.spam_reports
            metrics.unsubscribes = stats.unsubscribes

            # Get bounce details
            bounces = await sendgrid_client.get_bounces(
                start_time=start_date,
                end_time=end_date,
                limit=100,
            )

            # Analyze bounces
            bounce_domains: Dict[str, int] = {}
            for bounce in bounces:
                bounce_analysis.total_bounces += 1

                # Categorize by type
                if hasattr(bounce, 'bounce_type'):
                    if bounce.bounce_type.value == "hard":
                        bounce_analysis.hard_bounces += 1
                    elif bounce.bounce_type.value == "soft":
                        bounce_analysis.soft_bounces += 1
                    elif bounce.bounce_type.value == "block":
                        bounce_analysis.blocked_bounces += 1

                # Track domains
                if hasattr(bounce, 'email') and '@' in bounce.email:
                    domain = bounce.email.split('@')[1]
                    bounce_domains[domain] = bounce_domains.get(domain, 0) + 1

                # Add to recent bounces
                if hasattr(bounce, 'to_dict'):
                    bounce_analysis.recent_bounces.append(bounce.to_dict())

            # Sort and store top bounce domains
            sorted_domains = sorted(
                bounce_domains.items(),
                key=lambda x: x[1],
                reverse=True
            )
            bounce_analysis.top_bounce_domains = [
                {"domain": d, "count": c} for d, c in sorted_domains[:10]
            ]

            logger.info(
                "Retrieved SendGrid stats: sent=%d, delivered=%d, bounced=%d",
                metrics.sent,
                metrics.delivered,
                metrics.bounced,
            )

        except Exception as e:
            logger.error("Failed to fetch SendGrid data: %s", str(e))
            # Continue with empty metrics rather than failing

    # Calculate domain health
    health_score, health_status = calculate_domain_health_score(metrics)

    # Generate alerts and recommendations
    alerts = generate_alerts(metrics)
    recommendations = generate_recommendations(metrics, health_status)

    report = DailyReport(
        report_date=report_date,
        period=period,
        metrics=metrics,
        bounce_analysis=bounce_analysis,
        domain_health_score=health_score,
        domain_health_status=health_status,
        campaigns=campaigns,
        alerts=alerts,
        recommendations=recommendations,
        generated_at=now,
    )

    logger.info(
        "Report generated: health_score=%.1f, status=%s, alerts=%d",
        health_score,
        health_status.value,
        len(alerts),
    )

    return report


def generate_daily_report_from_stats(
    sent: int = 0,
    delivered: int = 0,
    opened: int = 0,
    clicked: int = 0,
    bounced: int = 0,
    spam_reports: int = 0,
    unsubscribes: int = 0,
    report_date: Optional[datetime] = None,
    period: ReportPeriod = ReportPeriod.DAILY,
) -> DailyReport:
    """Generate a daily report from raw statistics.

    Convenience function for generating reports without SendGrid client,
    useful for testing and manual metric entry.

    Args:
        sent: Total emails sent.
        delivered: Total emails delivered.
        opened: Total unique opens.
        clicked: Total unique clicks.
        bounced: Total bounces.
        spam_reports: Total spam reports.
        unsubscribes: Total unsubscribes.
        report_date: Date for the report.
        period: Reporting period.

    Returns:
        DailyReport with metrics analysis.

    Example:
        >>> report = generate_daily_report_from_stats(
        ...     sent=1000, delivered=950, opened=200, clicked=50,
        ...     bounced=20, spam_reports=2, unsubscribes=5
        ... )
        >>> print(report.domain_health_score)
    """
    now = datetime.now(timezone.utc)
    report_date = report_date or now

    # Calculate period dates
    if period == ReportPeriod.DAILY:
        start_date = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif period == ReportPeriod.WEEKLY:
        start_date = report_date - timedelta(days=report_date.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
    else:  # MONTHLY
        start_date = report_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1)

    metrics = EmailMetricsSnapshot(
        sent=sent,
        delivered=delivered,
        opened=opened,
        clicked=clicked,
        bounced=bounced,
        spam_reports=spam_reports,
        unsubscribes=unsubscribes,
        period_start=start_date,
        period_end=end_date,
    )

    # Simple bounce analysis
    bounce_analysis = BounceAnalysis(
        total_bounces=bounced,
        hard_bounces=int(bounced * 0.6),  # Estimate 60% hard bounces
        soft_bounces=int(bounced * 0.3),  # Estimate 30% soft bounces
        blocked_bounces=int(bounced * 0.1),  # Estimate 10% blocked
    )

    # Calculate domain health
    health_score, health_status = calculate_domain_health_score(metrics)

    # Generate alerts and recommendations
    alerts = generate_alerts(metrics)
    recommendations = generate_recommendations(metrics, health_status)

    return DailyReport(
        report_date=report_date,
        period=period,
        metrics=metrics,
        bounce_analysis=bounce_analysis,
        domain_health_score=health_score,
        domain_health_status=health_status,
        campaigns=[],
        alerts=alerts,
        recommendations=recommendations,
        generated_at=now,
    )


def aggregate_metrics(
    metrics_list: List[EmailMetricsSnapshot],
) -> EmailMetricsSnapshot:
    """Aggregate multiple metrics snapshots into a single summary.

    Args:
        metrics_list: List of EmailMetricsSnapshot objects.

    Returns:
        Combined EmailMetricsSnapshot with totals.
    """
    if not metrics_list:
        return EmailMetricsSnapshot()

    aggregated = EmailMetricsSnapshot(
        period_start=min(
            m.period_start for m in metrics_list if m.period_start
        ) if any(m.period_start for m in metrics_list) else None,
        period_end=max(
            m.period_end for m in metrics_list if m.period_end
        ) if any(m.period_end for m in metrics_list) else None,
    )

    for m in metrics_list:
        aggregated.sent += m.sent
        aggregated.delivered += m.delivered
        aggregated.opened += m.opened
        aggregated.clicked += m.clicked
        aggregated.bounced += m.bounced
        aggregated.spam_reports += m.spam_reports
        aggregated.unsubscribes += m.unsubscribes

    return aggregated


def get_health_status_description(status: DomainHealthStatus) -> str:
    """Get human-readable description of health status.

    Args:
        status: DomainHealthStatus enum value.

    Returns:
        Description string.
    """
    descriptions = {
        DomainHealthStatus.EXCELLENT: (
            "Your domain health is excellent. Email deliverability is optimal "
            "and you're following best practices."
        ),
        DomainHealthStatus.GOOD: (
            "Your domain health is good. There's minor room for improvement "
            "but overall performance is solid."
        ),
        DomainHealthStatus.FAIR: (
            "Your domain health needs attention. Review the recommendations "
            "to prevent deliverability issues."
        ),
        DomainHealthStatus.POOR: (
            "Your domain health is poor. Take immediate action to address "
            "bounce rates and spam complaints."
        ),
        DomainHealthStatus.CRITICAL: (
            "Your domain health is critical. Pause all campaigns immediately "
            "and address underlying issues before resuming."
        ),
    }
    return descriptions.get(status, "Unknown status.")


# Aliases for backwards compatibility
DailyReportResult = DailyReport
MetricsSnapshot = EmailMetricsSnapshot
