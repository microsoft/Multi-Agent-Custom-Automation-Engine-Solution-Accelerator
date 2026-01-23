#!/usr/bin/env python3
"""CLI entry point for the lead generation pipeline.

This module provides the command-line interface for running lead generation
campaigns. It handles argument parsing, environment validation, and campaign
execution through the pipeline orchestrator.

Usage:
    python main.py --zip-code 62701 --industries dentist,hvac,salon
    python main.py --zip-code 62701 --industries dentist --max-leads 10 --verbose
    python main.py --zip-code 62701 --industries hvac --skip-email --dry-run

Example:
    # Run a full campaign for dentists and HVAC in Springfield, IL
    python main.py --zip-code 62701 --industries dentist,hvac --max-leads 50

    # Test run without sending emails
    python main.py --zip-code 62701 --industries salon --skip-email --verbose
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add the leadgen directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import (
    LeadGenOrchestrator,
    PipelineConfig,
    CampaignResult,
    run_lead_gen_campaign,
)


# Configure logging
def setup_logging(verbose: bool = False, debug: bool = False) -> logging.Logger:
    """Configure logging for the CLI.

    Args:
        verbose: Enable verbose output (INFO level).
        debug: Enable debug output (DEBUG level).

    Returns:
        Configured logger instance.
    """
    level = logging.WARNING
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configure specific loggers
    logger = logging.getLogger("leadgen")
    logger.setLevel(level)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    return logger


def parse_industries(industries_str: str) -> list[str]:
    """Parse comma-separated industries string into a list.

    Args:
        industries_str: Comma-separated string of industries.

    Returns:
        List of industry strings, stripped and lowercased.
    """
    return [ind.strip().lower() for ind in industries_str.split(",") if ind.strip()]


def validate_zip_code(zip_code: str) -> bool:
    """Validate US zip code format.

    Args:
        zip_code: The zip code string to validate.

    Returns:
        True if valid, False otherwise.
    """
    # Basic US zip code validation (5 digits or 5+4 format)
    if len(zip_code) == 5:
        return zip_code.isdigit()
    elif len(zip_code) == 10 and zip_code[5] == "-":
        return zip_code[:5].isdigit() and zip_code[6:].isdigit()
    return False


def check_environment() -> dict[str, bool]:
    """Check required environment variables.

    Returns:
        Dictionary mapping env var names to their availability.
    """
    required_vars = [
        "OPENAI_API_KEY",
        "GOOGLE_MAPS_API_KEY",
        "DATABASE_URL",
    ]
    optional_vars = [
        "FIRECRAWL_API_KEY",
        "APOLLO_API_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER",
        "SENDGRID_API_KEY",
        "VERCEL_TOKEN",
    ]

    status = {}
    for var in required_vars:
        status[var] = bool(os.environ.get(var))

    for var in optional_vars:
        status[var] = bool(os.environ.get(var))

    return status


def print_env_status(status: dict[str, bool], verbose: bool = False) -> None:
    """Print environment variable status.

    Args:
        status: Dictionary of env var status.
        verbose: Include optional variables in output.
    """
    required = [
        "OPENAI_API_KEY",
        "GOOGLE_MAPS_API_KEY",
        "DATABASE_URL",
    ]
    optional = [
        "FIRECRAWL_API_KEY",
        "APOLLO_API_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER",
        "SENDGRID_API_KEY",
        "VERCEL_TOKEN",
    ]

    print("\nEnvironment Status:")
    print("-" * 40)

    missing_required = []
    for var in required:
        symbol = "\u2713" if status.get(var) else "\u2717"
        print(f"  [{symbol}] {var} (required)")
        if not status.get(var):
            missing_required.append(var)

    if verbose:
        print()
        for var in optional:
            symbol = "\u2713" if status.get(var) else "-"
            print(f"  [{symbol}] {var} (optional)")

    print("-" * 40)

    if missing_required:
        print(f"\nError: Missing required environment variables: {', '.join(missing_required)}")
        print("Set these variables before running the pipeline.")
        return False

    return True


def print_campaign_result(result: CampaignResult, verbose: bool = False) -> None:
    """Print campaign results in a formatted manner.

    Args:
        result: The campaign result to display.
        verbose: Include detailed lead results.
    """
    print("\n" + "=" * 60)
    print("CAMPAIGN RESULTS")
    print("=" * 60)

    # Status
    status_symbol = "\u2713" if result.success else "\u2717"
    print(f"\nStatus: [{status_symbol}] {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Campaign ID: {result.campaign_id}")

    # Timing
    if result.started_at:
        print(f"Started: {result.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if result.completed_at:
        print(f"Completed: {result.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {result.duration_seconds:.1f} seconds")

    # Lead Statistics
    print("\nLead Statistics:")
    print(f"  Total Leads Found: {result.total_leads}")
    print(f"  Successfully Processed: {result.processed_leads}")
    print(f"  Failed: {result.failed_leads}")

    if result.total_leads > 0:
        success_rate = (result.processed_leads / result.total_leads) * 100
        print(f"  Success Rate: {success_rate:.1f}%")

    # Errors
    if result.errors:
        print(f"\nCampaign Errors ({len(result.errors)}):")
        for error in result.errors[:5]:  # Show first 5
            print(f"  - {error[:100]}...")
        if len(result.errors) > 5:
            print(f"  ... and {len(result.errors) - 5} more")

    # Detailed results
    if verbose and result.lead_results:
        print("\nLead Details:")
        print("-" * 40)
        for lr in result.lead_results[:10]:  # Show first 10
            symbol = "\u2713" if lr.success else "\u2717"
            print(f"\n  [{symbol}] {lr.lead_name} (ID: {lr.lead_id})")
            print(f"      Dossier: {lr.dossier_status or 'N/A'}")
            if lr.vector_store_id:
                print(f"      Vector Store: {lr.vector_store_id[:20]}...")
            if lr.deployment_url:
                print(f"      Demo URL: {lr.deployment_url}")
            print(f"      Email Sent: {'Yes' if lr.email_sent else 'No'}")
            print(f"      Processing Time: {lr.processing_time_seconds:.1f}s")
            if lr.errors:
                print(f"      Errors: {len(lr.errors)}")

        if len(result.lead_results) > 10:
            print(f"\n  ... and {len(result.lead_results) - 10} more leads")

    print("\n" + "=" * 60)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="leadgen",
        description="Autonomous Lead Generation & AI Appointment-Setting System",
        epilog="""
Examples:
  %(prog)s --zip-code 62701 --industries dentist,hvac
  %(prog)s --zip-code 90210 --industries salon --max-leads 20
  %(prog)s --zip-code 10001 --industries dentist --skip-email --verbose

For more information, see the documentation or run with --help.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Required arguments
    required = parser.add_argument_group("required arguments")
    required.add_argument(
        "--zip-code",
        "-z",
        required=True,
        help="Target US zip code for lead scraping (e.g., 62701)",
    )
    required.add_argument(
        "--industries",
        "-i",
        required=True,
        help="Comma-separated list of industries (e.g., dentist,hvac,salon)",
    )

    # Pipeline options
    pipeline = parser.add_argument_group("pipeline options")
    pipeline.add_argument(
        "--max-leads",
        "-m",
        type=int,
        default=None,
        help="Maximum number of leads to process (default: unlimited)",
    )
    pipeline.add_argument(
        "--radius",
        "-r",
        type=int,
        default=20,
        help="Search radius in miles (default: 20)",
    )
    pipeline.add_argument(
        "--concurrent",
        "-c",
        type=int,
        default=5,
        help="Number of leads to process concurrently (default: 5)",
    )

    # Skip options
    skip = parser.add_argument_group("skip options")
    skip.add_argument(
        "--skip-voice",
        action="store_true",
        help="Skip voice agent assembly",
    )
    skip.add_argument(
        "--skip-deployment",
        action="store_true",
        help="Skip demo site deployment",
    )
    skip.add_argument(
        "--skip-email",
        action="store_true",
        help="Skip cold email sending",
    )

    # Email options
    email = parser.add_argument_group("email options")
    email.add_argument(
        "--email-style",
        choices=["humorous", "professional", "direct", "curiosity"],
        default="humorous",
        help="Email template style (default: humorous)",
    )
    email.add_argument(
        "--email-variant",
        choices=["A", "B", "C"],
        default="A",
        help="A/B test variant (default: A)",
    )

    # Output options
    output = parser.add_argument_group("output options")
    output.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Save results to JSON file",
    )
    output.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    output.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    output.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress output",
    )

    # Execution options
    execution = parser.add_argument_group("execution options")
    execution.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration without running pipeline",
    )
    execution.add_argument(
        "--check-env",
        action="store_true",
        help="Check environment variables and exit",
    )

    # Retry options
    retry = parser.add_argument_group("retry options")
    retry.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts per operation (default: 3)",
    )
    retry.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="Base retry delay in seconds (default: 2.0)",
    )

    return parser


def progress_callback(stage: str, current: int, total: int) -> None:
    """Callback to display progress during pipeline execution.

    Args:
        stage: Current pipeline stage name.
        current: Number of items completed.
        total: Total number of items.
    """
    if total > 0:
        percent = (current / total) * 100
        bar_length = 30
        filled = int(bar_length * current / total)
        bar = "\u2588" * filled + "\u2591" * (bar_length - filled)
        print(f"\r[{bar}] {percent:5.1f}% - {stage} ({current}/{total})", end="", flush=True)
    else:
        print(f"\r{stage}...", end="", flush=True)


async def run_pipeline(
    args: argparse.Namespace,
    logger: logging.Logger,
) -> Optional[CampaignResult]:
    """Run the lead generation pipeline with the given arguments.

    Args:
        args: Parsed command-line arguments.
        logger: Logger instance.

    Returns:
        CampaignResult if successful, None if validation fails.
    """
    # Parse industries
    industries = parse_industries(args.industries)
    if not industries:
        print("Error: No valid industries provided.")
        return None

    # Validate zip code
    if not validate_zip_code(args.zip_code):
        print(f"Error: Invalid zip code format: {args.zip_code}")
        print("Expected format: 12345 or 12345-6789")
        return None

    # Print configuration
    print("\nCampaign Configuration:")
    print("-" * 40)
    print(f"  Zip Code: {args.zip_code}")
    print(f"  Industries: {', '.join(industries)}")
    print(f"  Radius: {args.radius} miles")
    if args.max_leads:
        print(f"  Max Leads: {args.max_leads}")
    print(f"  Concurrent Processing: {args.concurrent}")
    print(f"  Skip Voice Assembly: {args.skip_voice}")
    print(f"  Skip Deployment: {args.skip_deployment}")
    print(f"  Skip Email: {args.skip_email}")
    if not args.skip_email:
        print(f"  Email Style: {args.email_style}")
        print(f"  Email Variant: {args.email_variant}")
    print("-" * 40)

    if args.dry_run:
        print("\n[DRY RUN] Configuration validated. No pipeline execution.")
        return None

    # Create pipeline configuration
    config = PipelineConfig(
        max_retries=args.max_retries,
        retry_delay_seconds=args.retry_delay,
        concurrent_leads=args.concurrent,
        skip_voice_assembly=args.skip_voice,
        skip_deployment=args.skip_deployment,
        skip_email=args.skip_email,
        email_style=args.email_style,
        email_variant=args.email_variant,
        twilio_number=os.environ.get("TWILIO_PHONE_NUMBER"),
        voice_websocket_url=os.environ.get("VOICE_WEBSOCKET_URL"),
    )

    # Create orchestrator with progress callback (if not quiet)
    callback = None if args.quiet else progress_callback
    orchestrator = LeadGenOrchestrator(
        config=config,
        progress_callback=callback,
    )

    # Run the campaign
    print("\nStarting lead generation campaign...")
    print()

    try:
        result = await orchestrator.run_campaign(
            zip_code=args.zip_code,
            industries=industries,
            radius_miles=args.radius,
            max_leads=args.max_leads,
        )

        # Clear progress line
        if not args.quiet:
            print("\r" + " " * 80 + "\r", end="")

        return result

    except KeyboardInterrupt:
        print("\n\nCampaign cancelled by user.")
        return None
    except Exception as e:
        logger.exception("Pipeline execution failed")
        print(f"\nError: Pipeline execution failed: {e}")
        return None


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(verbose=args.verbose, debug=args.debug)

    # Check environment option
    if args.check_env:
        status = check_environment()
        print_env_status(status, verbose=True)
        return 0 if all(status.get(v) for v in ["OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY", "DATABASE_URL"]) else 1

    # Check required environment variables
    if not args.dry_run:
        status = check_environment()
        if not print_env_status(status, verbose=args.verbose):
            return 1

    # Run the pipeline
    result = asyncio.run(run_pipeline(args, logger))

    if result is None:
        # Dry run or validation failure
        return 0 if args.dry_run else 1

    # Print results
    print_campaign_result(result, verbose=args.verbose)

    # Save results to file if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        print(f"\nResults saved to: {output_path}")

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
