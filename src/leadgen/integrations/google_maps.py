"""Google Maps Places API client for lead scraping.

This module provides a client for searching businesses within a geographic
radius using Google Maps Places API with pagination support.
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import googlemaps
from googlemaps.exceptions import ApiError, TransportError, Timeout

logger = logging.getLogger(__name__)

# Constants
MILES_TO_METERS = 1609.34
DEFAULT_RADIUS_MILES = 20
MAX_RESULTS_PER_PAGE = 20
MAX_PAGES = 3  # Google Places API allows up to 3 pages (60 results total)
PAGINATION_DELAY_SECONDS = 2.0  # Required delay between pagination requests


@dataclass
class PlaceResult:
    """Represents a single place result from Google Maps.

    Attributes:
        place_id: Unique Google Places identifier.
        name: Business name.
        address: Formatted address.
        phone: Phone number (may be None).
        website: Website URL (may be None).
        rating: Average star rating (0.0-5.0).
        review_count: Number of user reviews.
        types: List of place types/categories.
        location: Latitude/longitude tuple.
        business_status: Operating status (OPERATIONAL, CLOSED, etc.).
    """

    place_id: str
    name: str
    address: str
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    types: list[str] = field(default_factory=list)
    location: Optional[tuple[float, float]] = None
    business_status: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "place_id": self.place_id,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "website": self.website,
            "rating": self.rating,
            "review_count": self.review_count,
            "types": self.types,
            "location": self.location,
            "business_status": self.business_status,
        }


@dataclass
class SearchResult:
    """Represents a paginated search result.

    Attributes:
        places: List of place results.
        total_results: Total number of results found.
        pages_fetched: Number of pages retrieved.
        next_page_token: Token for fetching next page (if available).
    """

    places: list[PlaceResult]
    total_results: int
    pages_fetched: int
    next_page_token: Optional[str] = None


class GoogleMapsClient:
    """Client for Google Maps Places API with pagination support.

    Provides methods for searching businesses within a geographic radius
    using the Places API Nearby Search endpoint.

    Attributes:
        api_key: Google Maps API key.
        radius_miles: Default search radius in miles.

    Example:
        >>> client = GoogleMapsClient()
        >>> results = await client.search_nearby(
        ...     zip_code="62701",
        ...     industry="dentist",
        ...     radius_miles=20
        ... )
        >>> for place in results.places:
        ...     print(place.name, place.phone)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        radius_miles: float = DEFAULT_RADIUS_MILES,
    ) -> None:
        """Initialize Google Maps client.

        Args:
            api_key: Google Maps API key. Defaults to GOOGLE_MAPS_API_KEY env var.
            radius_miles: Default search radius in miles. Defaults to 20.

        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google Maps API key required. Set GOOGLE_MAPS_API_KEY environment "
                "variable or pass api_key parameter."
            )

        self.radius_miles = radius_miles
        self._client = googlemaps.Client(key=self.api_key)
        logger.info(
            "GoogleMapsClient initialized with %d mile default radius",
            radius_miles,
        )

    def _get_radius_meters(self, radius_miles: Optional[float] = None) -> int:
        """Convert radius from miles to meters.

        Args:
            radius_miles: Radius in miles. Uses default if None.

        Returns:
            Radius in meters (rounded to nearest integer).
        """
        miles = radius_miles if radius_miles is not None else self.radius_miles
        return int(miles * MILES_TO_METERS)

    async def geocode_zip(self, zip_code: str) -> tuple[float, float]:
        """Convert a zip code to latitude/longitude coordinates.

        Args:
            zip_code: US zip code to geocode.

        Returns:
            Tuple of (latitude, longitude).

        Raises:
            ValueError: If zip code cannot be geocoded.
        """
        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(
                None,
                lambda: self._client.geocode(f"{zip_code}, USA"),
            )

            if not results:
                raise ValueError(f"Could not geocode zip code: {zip_code}")

            location = results[0]["geometry"]["location"]
            lat, lng = location["lat"], location["lng"]
            logger.debug("Geocoded %s to (%f, %f)", zip_code, lat, lng)
            return (lat, lng)

        except (ApiError, TransportError, Timeout) as e:
            logger.error("Failed to geocode zip code %s: %s", zip_code, e)
            raise ValueError(f"Geocoding failed for {zip_code}: {e}") from e

    def _parse_place(self, place_data: dict[str, Any]) -> PlaceResult:
        """Parse raw API response into PlaceResult.

        Args:
            place_data: Raw place data from API response.

        Returns:
            Parsed PlaceResult object.
        """
        location = place_data.get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")

        return PlaceResult(
            place_id=place_data.get("place_id", ""),
            name=place_data.get("name", ""),
            address=place_data.get("vicinity", place_data.get("formatted_address", "")),
            rating=place_data.get("rating"),
            review_count=place_data.get("user_ratings_total"),
            types=place_data.get("types", []),
            location=(lat, lng) if lat and lng else None,
            business_status=place_data.get("business_status"),
        )

    async def _fetch_place_details(
        self,
        place_id: str,
        fields: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Fetch detailed information for a single place.

        Args:
            place_id: Google Places place_id.
            fields: List of fields to retrieve. Defaults to phone and website.

        Returns:
            Dictionary with place details.
        """
        if fields is None:
            fields = ["formatted_phone_number", "website"]

        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self._client.place(place_id, fields=fields),
            )
            return result.get("result", {})
        except (ApiError, TransportError, Timeout) as e:
            logger.warning("Failed to fetch details for place %s: %s", place_id, e)
            return {}

    async def enrich_place_details(
        self,
        place: PlaceResult,
    ) -> PlaceResult:
        """Enrich a PlaceResult with phone and website from Place Details API.

        Args:
            place: PlaceResult to enrich.

        Returns:
            Enriched PlaceResult with phone and website populated.
        """
        details = await self._fetch_place_details(place.place_id)
        place.phone = details.get("formatted_phone_number")
        place.website = details.get("website")
        return place

    async def search_nearby(
        self,
        zip_code: Optional[str] = None,
        location: Optional[tuple[float, float]] = None,
        industry: str = "",
        radius_miles: Optional[float] = None,
        max_pages: int = MAX_PAGES,
        enrich_details: bool = True,
    ) -> SearchResult:
        """Search for businesses near a location.

        Uses Google Maps Places API Nearby Search with pagination to retrieve
        up to 60 results (3 pages of 20 results each).

        Args:
            zip_code: US zip code to search around. Either zip_code or location required.
            location: Latitude/longitude tuple. Either zip_code or location required.
            industry: Business type/keyword to search for (e.g., "dentist", "hvac").
            radius_miles: Search radius in miles. Defaults to 20.
            max_pages: Maximum number of pages to fetch (1-3). Defaults to 3.
            enrich_details: Whether to fetch phone/website for each result. Defaults to True.

        Returns:
            SearchResult with list of places and pagination info.

        Raises:
            ValueError: If neither zip_code nor location provided.
            ApiError: If API request fails.
        """
        if not zip_code and not location:
            raise ValueError("Either zip_code or location must be provided")

        # Geocode zip code if needed
        if location is None:
            location = await self.geocode_zip(zip_code)

        radius_meters = self._get_radius_meters(radius_miles)
        max_pages = min(max_pages, MAX_PAGES)

        logger.info(
            "Searching for '%s' within %d miles of %s (coords: %s)",
            industry,
            radius_miles or self.radius_miles,
            zip_code or "location",
            location,
        )

        all_places: list[PlaceResult] = []
        pages_fetched = 0
        next_page_token: Optional[str] = None

        loop = asyncio.get_event_loop()

        for page_num in range(max_pages):
            try:
                # Make API request
                if page_num == 0:
                    response = await loop.run_in_executor(
                        None,
                        lambda: self._client.places_nearby(
                            location=location,
                            radius=radius_meters,
                            keyword=industry,
                            type=None,
                        ),
                    )
                else:
                    # Wait before fetching next page (required by API)
                    await asyncio.sleep(PAGINATION_DELAY_SECONDS)
                    response = await loop.run_in_executor(
                        None,
                        lambda token=next_page_token: self._client.places_nearby(
                            location=location,
                            radius=radius_meters,
                            keyword=industry,
                            page_token=token,
                        ),
                    )

                # Parse results
                results = response.get("results", [])
                for place_data in results:
                    place = self._parse_place(place_data)
                    all_places.append(place)

                pages_fetched += 1
                next_page_token = response.get("next_page_token")

                logger.debug(
                    "Page %d: Found %d results. Has next page: %s",
                    page_num + 1,
                    len(results),
                    bool(next_page_token),
                )

                # Stop if no more pages
                if not next_page_token:
                    break

            except (ApiError, TransportError, Timeout) as e:
                logger.error("API error on page %d: %s", page_num + 1, e)
                if page_num == 0:
                    raise
                break

        # Enrich places with phone/website details
        if enrich_details and all_places:
            logger.info("Enriching %d places with contact details", len(all_places))
            enrichment_tasks = [self.enrich_place_details(p) for p in all_places]
            all_places = await asyncio.gather(*enrichment_tasks)

        logger.info(
            "Search complete: Found %d total results across %d pages",
            len(all_places),
            pages_fetched,
        )

        return SearchResult(
            places=all_places,
            total_results=len(all_places),
            pages_fetched=pages_fetched,
            next_page_token=next_page_token,
        )

    async def search_multiple_industries(
        self,
        zip_code: str,
        industries: list[str],
        radius_miles: Optional[float] = None,
        max_pages_per_industry: int = MAX_PAGES,
        enrich_details: bool = True,
    ) -> dict[str, SearchResult]:
        """Search for multiple industries in parallel.

        Args:
            zip_code: US zip code to search around.
            industries: List of industry keywords to search.
            radius_miles: Search radius in miles.
            max_pages_per_industry: Max pages per industry search.
            enrich_details: Whether to fetch phone/website for results.

        Returns:
            Dictionary mapping industry to SearchResult.
        """
        # Geocode once for efficiency
        location = await self.geocode_zip(zip_code)

        results: dict[str, SearchResult] = {}
        for industry in industries:
            result = await self.search_nearby(
                location=location,
                industry=industry,
                radius_miles=radius_miles,
                max_pages=max_pages_per_industry,
                enrich_details=enrich_details,
            )
            results[industry] = result

        return results

    def close(self) -> None:
        """Clean up client resources."""
        # googlemaps.Client doesn't require explicit cleanup,
        # but we provide this method for consistency
        pass

    async def __aenter__(self) -> "GoogleMapsClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        self.close()
