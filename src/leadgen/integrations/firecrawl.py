"""Firecrawl client for website scraping with markdown output.

This module provides a client for scraping websites using Firecrawl API,
returning content in markdown format optimized for LLM consumption.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from firecrawl import Firecrawl

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT_MS = 30000  # 30 seconds
DEFAULT_FORMATS = ["markdown"]
SUPPORTED_FORMATS = ["markdown", "html", "rawHtml", "links", "screenshot"]


class FirecrawlError(Exception):
    """Base exception for Firecrawl client errors."""

    pass


class FirecrawlRateLimitError(FirecrawlError):
    """Raised when API rate limit is exceeded."""

    pass


class FirecrawlAuthError(FirecrawlError):
    """Raised when API authentication fails."""

    pass


class FirecrawlScrapeError(FirecrawlError):
    """Raised when scraping a URL fails."""

    pass


@dataclass
class ScrapeResult:
    """Represents the result of scraping a single URL.

    Attributes:
        url: The URL that was scraped.
        markdown: Markdown content (primary output for LLM consumption).
        html: HTML content (if requested).
        raw_html: Raw HTML content (if requested).
        links: Extracted links from the page (if requested).
        metadata: Page metadata (title, description, etc.).
        success: Whether the scrape was successful.
        error: Error message if scrape failed.
    """

    url: str
    markdown: Optional[str] = None
    html: Optional[str] = None
    raw_html: Optional[str] = None
    links: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "url": self.url,
            "markdown": self.markdown,
            "html": self.html,
            "raw_html": self.raw_html,
            "links": self.links,
            "metadata": self.metadata,
            "success": self.success,
            "error": self.error,
        }

    @property
    def has_content(self) -> bool:
        """Check if any content was retrieved."""
        return bool(self.markdown or self.html or self.raw_html)

    @property
    def word_count(self) -> int:
        """Estimate word count from markdown content."""
        if not self.markdown:
            return 0
        return len(self.markdown.split())


@dataclass
class CrawlResult:
    """Represents the result of crawling multiple pages from a site.

    Attributes:
        base_url: The starting URL for the crawl.
        pages: List of scraped page results.
        total_pages: Total number of pages scraped.
        success: Whether the crawl completed successfully.
        error: Error message if crawl failed.
    """

    base_url: str
    pages: list[ScrapeResult] = field(default_factory=list)
    total_pages: int = 0
    success: bool = True
    error: Optional[str] = None

    def get_all_markdown(self) -> str:
        """Combine all markdown content into a single document."""
        content_parts = []
        for page in self.pages:
            if page.markdown:
                title = page.metadata.get("title", page.url)
                content_parts.append(f"# {title}\n\nSource: {page.url}\n\n{page.markdown}")
        return "\n\n---\n\n".join(content_parts)


class FirecrawlClient:
    """Client for Firecrawl API with async support.

    Provides methods for scraping websites and extracting content in
    markdown format, optimized for LLM consumption.

    Attributes:
        api_key: Firecrawl API key.
        timeout_ms: Request timeout in milliseconds.

    Example:
        >>> client = FirecrawlClient()
        >>> result = await client.scrape_url("https://acmedental.com")
        >>> print(result.markdown)
        # Acme Dental - Your Smile, Our Priority
        ...
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> None:
        """Initialize Firecrawl client.

        Args:
            api_key: Firecrawl API key. Defaults to FIRECRAWL_API_KEY env var.
            timeout_ms: Request timeout in milliseconds. Defaults to 30000.

        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or os.environ.get("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Firecrawl API key required. Set FIRECRAWL_API_KEY environment "
                "variable or pass api_key parameter."
            )

        self.timeout_ms = timeout_ms
        self._client = Firecrawl(api_key=self.api_key)
        logger.info("FirecrawlClient initialized with %dms timeout", timeout_ms)

    def _parse_scrape_response(
        self,
        url: str,
        response: dict[str, Any],
    ) -> ScrapeResult:
        """Parse raw API response into ScrapeResult.

        Args:
            url: The URL that was scraped.
            response: Raw response from Firecrawl API.

        Returns:
            Parsed ScrapeResult object.
        """
        # Extract metadata
        metadata = response.get("metadata", {})
        if not metadata:
            # Try alternate location for metadata
            metadata = {
                "title": response.get("title"),
                "description": response.get("description"),
                "language": response.get("language"),
                "ogImage": response.get("ogImage"),
            }
            # Remove None values
            metadata = {k: v for k, v in metadata.items() if v is not None}

        # Extract links
        links = response.get("links", [])
        if isinstance(links, str):
            links = [links]

        return ScrapeResult(
            url=url,
            markdown=response.get("markdown"),
            html=response.get("html"),
            raw_html=response.get("rawHtml"),
            links=links,
            metadata=metadata,
            success=True,
            error=None,
        )

    async def scrape_url(
        self,
        url: str,
        formats: Optional[list[str]] = None,
        only_main_content: bool = True,
        include_tags: Optional[list[str]] = None,
        exclude_tags: Optional[list[str]] = None,
        wait_for: Optional[int] = None,
    ) -> ScrapeResult:
        """Scrape a single URL and return content.

        Uses Firecrawl's scrape endpoint which handles JavaScript rendering
        automatically.

        Args:
            url: The URL to scrape.
            formats: Output formats to request (markdown, html, etc.).
                    Defaults to ["markdown"].
            only_main_content: Whether to extract only main content (removes
                              navbars, footers, etc.). Defaults to True.
            include_tags: HTML tags to include in extraction.
            exclude_tags: HTML tags to exclude from extraction.
            wait_for: Milliseconds to wait for JavaScript rendering.

        Returns:
            ScrapeResult with extracted content.

        Raises:
            FirecrawlAuthError: If API authentication fails.
            FirecrawlRateLimitError: If rate limit is exceeded.
            FirecrawlScrapeError: If scraping fails.
        """
        if formats is None:
            formats = DEFAULT_FORMATS.copy()

        # Validate formats
        for fmt in formats:
            if fmt not in SUPPORTED_FORMATS:
                logger.warning("Unsupported format '%s', ignoring", fmt)

        logger.info("Scraping URL: %s (formats: %s)", url, formats)

        # Build scrape parameters
        params: dict[str, Any] = {
            "formats": formats,
            "onlyMainContent": only_main_content,
        }

        if include_tags:
            params["includeTags"] = include_tags
        if exclude_tags:
            params["excludeTags"] = exclude_tags
        if wait_for:
            params["waitFor"] = wait_for

        loop = asyncio.get_event_loop()

        try:
            response = await loop.run_in_executor(
                None,
                lambda: self._client.scrape(url, **params),
            )

            if not response:
                logger.warning("Empty response from Firecrawl for URL: %s", url)
                return ScrapeResult(
                    url=url,
                    success=False,
                    error="Empty response from Firecrawl API",
                )

            result = self._parse_scrape_response(url, response)
            logger.info(
                "Successfully scraped %s: %d words in markdown",
                url,
                result.word_count,
            )
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to scrape %s: %s", url, error_msg)

            # Categorize errors
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise FirecrawlAuthError(f"Authentication failed: {error_msg}") from e
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                raise FirecrawlRateLimitError(f"Rate limit exceeded: {error_msg}") from e
            else:
                raise FirecrawlScrapeError(f"Scrape failed for {url}: {error_msg}") from e

    async def scrape_url_safe(
        self,
        url: str,
        formats: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> ScrapeResult:
        """Scrape a URL with error handling (returns result instead of raising).

        This method catches errors and returns a ScrapeResult with success=False
        and the error message, rather than raising exceptions.

        Args:
            url: The URL to scrape.
            formats: Output formats to request.
            **kwargs: Additional arguments passed to scrape_url.

        Returns:
            ScrapeResult (with success=False if scraping failed).
        """
        try:
            return await self.scrape_url(url, formats=formats, **kwargs)
        except FirecrawlError as e:
            logger.warning("Safe scrape failed for %s: %s", url, e)
            return ScrapeResult(
                url=url,
                success=False,
                error=str(e),
            )
        except Exception as e:
            logger.error("Unexpected error scraping %s: %s", url, e)
            return ScrapeResult(
                url=url,
                success=False,
                error=f"Unexpected error: {e}",
            )

    async def scrape_multiple_urls(
        self,
        urls: list[str],
        formats: Optional[list[str]] = None,
        concurrency: int = 3,
        **kwargs: Any,
    ) -> list[ScrapeResult]:
        """Scrape multiple URLs with controlled concurrency.

        Args:
            urls: List of URLs to scrape.
            formats: Output formats to request.
            concurrency: Maximum concurrent requests. Defaults to 3.
            **kwargs: Additional arguments passed to scrape_url_safe.

        Returns:
            List of ScrapeResult objects (one per URL).
        """
        logger.info("Scraping %d URLs with concurrency=%d", len(urls), concurrency)

        semaphore = asyncio.Semaphore(concurrency)

        async def scrape_with_limit(url: str) -> ScrapeResult:
            async with semaphore:
                return await self.scrape_url_safe(url, formats=formats, **kwargs)

        results = await asyncio.gather(*[scrape_with_limit(url) for url in urls])

        successful = sum(1 for r in results if r.success)
        logger.info(
            "Completed scraping %d URLs: %d successful, %d failed",
            len(urls),
            successful,
            len(urls) - successful,
        )

        return list(results)

    async def crawl_site(
        self,
        url: str,
        max_pages: int = 10,
        formats: Optional[list[str]] = None,
        include_paths: Optional[list[str]] = None,
        exclude_paths: Optional[list[str]] = None,
    ) -> CrawlResult:
        """Crawl a website starting from the given URL.

        Uses Firecrawl's crawl endpoint to discover and scrape multiple pages
        from a website.

        Args:
            url: The starting URL for the crawl.
            max_pages: Maximum number of pages to crawl. Defaults to 10.
            formats: Output formats to request. Defaults to ["markdown"].
            include_paths: URL path patterns to include (e.g., ["/blog/*"]).
            exclude_paths: URL path patterns to exclude.

        Returns:
            CrawlResult with all scraped pages.

        Raises:
            FirecrawlScrapeError: If crawl fails.
        """
        if formats is None:
            formats = DEFAULT_FORMATS.copy()

        logger.info("Starting crawl of %s (max_pages=%d)", url, max_pages)

        # Build crawl parameters
        params: dict[str, Any] = {
            "limit": max_pages,
            "scrapeOptions": {
                "formats": formats,
            },
        }

        if include_paths:
            params["includePaths"] = include_paths
        if exclude_paths:
            params["excludePaths"] = exclude_paths

        loop = asyncio.get_event_loop()

        try:
            response = await loop.run_in_executor(
                None,
                lambda: self._client.crawl(url, **params),
            )

            if not response:
                return CrawlResult(
                    base_url=url,
                    success=False,
                    error="Empty response from Firecrawl crawl API",
                )

            # Parse crawl results
            pages: list[ScrapeResult] = []
            data = response.get("data", [])
            if isinstance(data, list):
                for page_data in data:
                    page_url = page_data.get("url", url)
                    page_result = self._parse_scrape_response(page_url, page_data)
                    pages.append(page_result)

            result = CrawlResult(
                base_url=url,
                pages=pages,
                total_pages=len(pages),
                success=True,
            )

            logger.info(
                "Crawl complete for %s: %d pages scraped",
                url,
                result.total_pages,
            )
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("Crawl failed for %s: %s", url, error_msg)
            raise FirecrawlScrapeError(f"Crawl failed for {url}: {error_msg}") from e

    async def extract_business_info(
        self,
        url: str,
    ) -> dict[str, Any]:
        """Extract structured business information from a website.

        Scrapes the website and uses metadata to extract business-relevant
        information like name, description, services, and contact info.

        Args:
            url: Business website URL to extract info from.

        Returns:
            Dictionary with extracted business information.
        """
        result = await self.scrape_url(
            url,
            formats=["markdown", "html"],
            only_main_content=True,
        )

        business_info: dict[str, Any] = {
            "url": url,
            "success": result.success,
        }

        if result.success and result.has_content:
            metadata = result.metadata
            business_info.update({
                "title": metadata.get("title"),
                "description": metadata.get("description"),
                "og_image": metadata.get("ogImage") or metadata.get("og:image"),
                "language": metadata.get("language"),
                "markdown_content": result.markdown,
                "word_count": result.word_count,
                "links": result.links[:20],  # Limit to first 20 links
            })
        elif not result.success:
            business_info["error"] = result.error

        return business_info

    def close(self) -> None:
        """Clean up client resources."""
        # Firecrawl client doesn't require explicit cleanup,
        # but we provide this method for consistency
        pass

    async def __aenter__(self) -> "FirecrawlClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        self.close()
