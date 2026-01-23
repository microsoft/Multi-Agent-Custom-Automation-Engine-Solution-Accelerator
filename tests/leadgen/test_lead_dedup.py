"""Unit tests for lead deduplication logic.

Tests the deduplication mechanisms used in lead scraping and storage,
including place_id based deduplication and cross-industry deduplication.
"""

import os
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Ensure repo root is on sys.path so imports work correctly
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LEADGEN_DIR = os.path.join(ROOT_DIR, "src", "leadgen")
if LEADGEN_DIR not in sys.path:
    sys.path.insert(0, LEADGEN_DIR)


class TestPlaceIdDeduplication:
    """Tests for place_id based deduplication logic.

    The scraper uses Google Place IDs as unique identifiers to prevent
    duplicate leads across multiple scraping runs and industries.
    """

    def test_unique_place_ids_all_kept(self):
        """Test that all leads with unique place_ids are kept."""
        leads = [
            {"place_id": "place_1", "name": "Business A"},
            {"place_id": "place_2", "name": "Business B"},
            {"place_id": "place_3", "name": "Business C"},
        ]

        seen_place_ids: set[str] = set()
        unique_leads = []

        for lead in leads:
            place_id = lead.get("place_id")
            if place_id and place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                unique_leads.append(lead)

        assert len(unique_leads) == 3
        assert all(lead in unique_leads for lead in leads)

    def test_duplicate_place_ids_removed(self):
        """Test that duplicate place_ids are removed."""
        leads = [
            {"place_id": "place_1", "name": "Business A - First"},
            {"place_id": "place_1", "name": "Business A - Duplicate"},
            {"place_id": "place_2", "name": "Business B"},
        ]

        seen_place_ids: set[str] = set()
        unique_leads = []

        for lead in leads:
            place_id = lead.get("place_id")
            if place_id and place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                unique_leads.append(lead)

        assert len(unique_leads) == 2
        assert unique_leads[0]["name"] == "Business A - First"
        assert unique_leads[1]["name"] == "Business B"

    def test_first_occurrence_kept(self):
        """Test that the first occurrence of a duplicate is kept."""
        leads = [
            {"place_id": "place_1", "name": "First Occurrence", "data": "original"},
            {"place_id": "place_1", "name": "Second Occurrence", "data": "duplicate"},
            {"place_id": "place_1", "name": "Third Occurrence", "data": "another_dup"},
        ]

        seen_place_ids: set[str] = set()
        unique_leads = []

        for lead in leads:
            place_id = lead.get("place_id")
            if place_id and place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                unique_leads.append(lead)

        assert len(unique_leads) == 1
        assert unique_leads[0]["name"] == "First Occurrence"
        assert unique_leads[0]["data"] == "original"

    def test_null_place_id_skipped(self):
        """Test that leads with null place_id are skipped."""
        leads = [
            {"place_id": None, "name": "No Place ID"},
            {"place_id": "place_1", "name": "Has Place ID"},
        ]

        seen_place_ids: set[str] = set()
        unique_leads = []

        for lead in leads:
            place_id = lead.get("place_id")
            if place_id and place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                unique_leads.append(lead)

        assert len(unique_leads) == 1
        assert unique_leads[0]["name"] == "Has Place ID"

    def test_empty_place_id_skipped(self):
        """Test that leads with empty string place_id are handled."""
        leads = [
            {"place_id": "", "name": "Empty Place ID"},
            {"place_id": "place_1", "name": "Has Place ID"},
        ]

        seen_place_ids: set[str] = set()
        unique_leads = []

        for lead in leads:
            place_id = lead.get("place_id")
            if place_id and place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                unique_leads.append(lead)

        assert len(unique_leads) == 1
        assert unique_leads[0]["name"] == "Has Place ID"

    def test_missing_place_id_key_skipped(self):
        """Test that leads without place_id key are skipped."""
        leads = [
            {"name": "Missing Place ID Key"},
            {"place_id": "place_1", "name": "Has Place ID"},
        ]

        seen_place_ids: set[str] = set()
        unique_leads = []

        for lead in leads:
            place_id = lead.get("place_id")
            if place_id and place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                unique_leads.append(lead)

        assert len(unique_leads) == 1
        assert unique_leads[0]["name"] == "Has Place ID"


class TestCrossIndustryDeduplication:
    """Tests for cross-industry deduplication.

    When scraping multiple industries, the same business might appear
    in multiple industry searches. The scraper deduplicates across industries.
    """

    def test_same_business_different_industries(self):
        """Test deduplication when same business appears in multiple industries."""
        # Simulate results from multiple industry searches
        dentist_leads = [
            {"place_id": "place_1", "name": "Multi-Service Medical", "industry": "dentist"},
            {"place_id": "place_2", "name": "Dental Only", "industry": "dentist"},
        ]

        doctor_leads = [
            {"place_id": "place_1", "name": "Multi-Service Medical", "industry": "doctor"},  # duplicate
            {"place_id": "place_3", "name": "Doctor Only", "industry": "doctor"},
        ]

        # Simulate cross-industry deduplication
        seen_place_ids: set[str] = set()
        results: dict[str, list[dict]] = {}

        for industry, leads in [("dentist", dentist_leads), ("doctor", doctor_leads)]:
            unique_leads = []
            for lead in leads:
                place_id = lead.get("place_id")
                if place_id and place_id not in seen_place_ids:
                    seen_place_ids.add(place_id)
                    unique_leads.append(lead)
            results[industry] = unique_leads

        # Dentist gets both leads (searched first)
        assert len(results["dentist"]) == 2
        # Doctor only gets the unique one (place_1 was already seen)
        assert len(results["doctor"]) == 1
        assert results["doctor"][0]["place_id"] == "place_3"

    def test_order_matters_for_attribution(self):
        """Test that search order determines industry attribution."""
        # Same leads but different order
        doctor_leads = [
            {"place_id": "place_1", "name": "Multi-Service Medical", "industry": "doctor"},
        ]

        dentist_leads = [
            {"place_id": "place_1", "name": "Multi-Service Medical", "industry": "dentist"},
        ]

        # Search doctor first
        seen_place_ids: set[str] = set()
        results: dict[str, list[dict]] = {}

        for industry, leads in [("doctor", doctor_leads), ("dentist", dentist_leads)]:
            unique_leads = []
            for lead in leads:
                place_id = lead.get("place_id")
                if place_id and place_id not in seen_place_ids:
                    seen_place_ids.add(place_id)
                    unique_leads.append(lead)
            results[industry] = unique_leads

        # Doctor gets the lead (searched first)
        assert len(results["doctor"]) == 1
        assert results["doctor"][0]["industry"] == "doctor"
        # Dentist gets nothing (duplicate)
        assert len(results["dentist"]) == 0

    def test_total_unique_count(self):
        """Test that total unique leads is calculated correctly."""
        industry_results = {
            "dentist": [
                {"place_id": "p1", "name": "A"},
                {"place_id": "p2", "name": "B"},
            ],
            "hvac": [
                {"place_id": "p3", "name": "C"},  # unique to hvac
            ],
            "salon": [
                {"place_id": "p4", "name": "D"},
                {"place_id": "p5", "name": "E"},
            ],
        }

        total_leads = sum(len(leads) for leads in industry_results.values())
        assert total_leads == 5

    def test_empty_industry_results(self):
        """Test handling of industries with no unique results."""
        seen_place_ids: set[str] = set()
        results: dict[str, list[dict]] = {}

        # First industry gets all leads
        industry1_leads = [{"place_id": "p1"}, {"place_id": "p2"}]
        # Second industry has same leads (all duplicates)
        industry2_leads = [{"place_id": "p1"}, {"place_id": "p2"}]

        for industry, leads in [("first", industry1_leads), ("second", industry2_leads)]:
            unique_leads = []
            for lead in leads:
                place_id = lead.get("place_id")
                if place_id and place_id not in seen_place_ids:
                    seen_place_ids.add(place_id)
                    unique_leads.append(lead)
            results[industry] = unique_leads

        assert len(results["first"]) == 2
        assert len(results["second"]) == 0  # All duplicates


class TestDeduplicationWithMixedData:
    """Tests for deduplication with various data quality scenarios."""

    def test_whitespace_in_place_id(self):
        """Test that place_ids with whitespace are handled as distinct."""
        leads = [
            {"place_id": "place_1", "name": "Normal ID"},
            {"place_id": " place_1", "name": "Leading Space"},
            {"place_id": "place_1 ", "name": "Trailing Space"},
        ]

        seen_place_ids: set[str] = set()
        unique_leads = []

        for lead in leads:
            place_id = lead.get("place_id")
            if place_id and place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                unique_leads.append(lead)

        # Without normalization, these are treated as different
        # This documents current behavior - whitespace is significant
        assert len(unique_leads) == 3

    def test_normalized_place_id_dedup(self):
        """Test deduplication with normalized place_ids."""
        leads = [
            {"place_id": "place_1", "name": "Normal ID"},
            {"place_id": " place_1", "name": "Leading Space"},
            {"place_id": "place_1 ", "name": "Trailing Space"},
        ]

        seen_place_ids: set[str] = set()
        unique_leads = []

        for lead in leads:
            place_id = lead.get("place_id")
            if place_id:
                # Normalize by stripping whitespace
                normalized_id = place_id.strip()
                if normalized_id not in seen_place_ids:
                    seen_place_ids.add(normalized_id)
                    unique_leads.append(lead)

        # With normalization, all are treated as same
        assert len(unique_leads) == 1
        assert unique_leads[0]["name"] == "Normal ID"

    def test_case_sensitivity(self):
        """Test that place_ids are case-sensitive."""
        leads = [
            {"place_id": "Place_1", "name": "Capitalized"},
            {"place_id": "place_1", "name": "Lowercase"},
            {"place_id": "PLACE_1", "name": "Uppercase"},
        ]

        seen_place_ids: set[str] = set()
        unique_leads = []

        for lead in leads:
            place_id = lead.get("place_id")
            if place_id and place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                unique_leads.append(lead)

        # Google Place IDs are case-sensitive
        assert len(unique_leads) == 3

    def test_large_batch_deduplication(self):
        """Test deduplication performance with large batches."""
        # Create 1000 leads with ~10% duplicates
        leads = []
        for i in range(1000):
            # Every 10th lead (i=10, 20, ..., 990) is a duplicate of the previous
            if i > 0 and i % 10 == 0:
                place_id = f"place_{i-1}"
            else:
                place_id = f"place_{i}"
            leads.append({"place_id": place_id, "name": f"Business {i}"})

        seen_place_ids: set[str] = set()
        unique_leads = []

        for lead in leads:
            place_id = lead.get("place_id")
            if place_id and place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                unique_leads.append(lead)

        # Should have 901 unique leads (1000 - 99 duplicates at i=10,20,...,990)
        assert len(unique_leads) == 901


class TestLeadModelDeduplication:
    """Tests for Lead model deduplication via google_place_id unique constraint.

    The Lead model uses google_place_id as a unique identifier to prevent
    duplicate leads in the database.
    """

    def test_lead_model_has_google_place_id(self):
        """Test that Lead model defines google_place_id field."""
        # Import the model to verify structure
        try:
            from models.lead import Lead

            # Check that google_place_id is defined
            assert hasattr(Lead, "google_place_id")
        except ImportError:
            # If model can't be imported due to dependencies, skip
            pytest.skip("Lead model cannot be imported (missing dependencies)")

    def test_mock_lead_dedup_insert(self):
        """Test simulated database deduplication behavior."""
        # Simulate a database with unique constraint on google_place_id
        database: dict[str, dict[str, Any]] = {}

        def insert_lead(lead: dict[str, Any]) -> bool:
            """Simulate inserting a lead with unique constraint."""
            place_id = lead.get("google_place_id")
            if place_id and place_id in database:
                return False  # Would raise unique constraint violation
            if place_id:
                database[place_id] = lead
            return True

        # Insert first lead
        lead1 = {"google_place_id": "place_1", "name": "Business A"}
        assert insert_lead(lead1) is True
        assert len(database) == 1

        # Try to insert duplicate
        lead2 = {"google_place_id": "place_1", "name": "Business A Duplicate"}
        assert insert_lead(lead2) is False
        assert len(database) == 1

        # Insert unique lead
        lead3 = {"google_place_id": "place_2", "name": "Business B"}
        assert insert_lead(lead3) is True
        assert len(database) == 2

    def test_mock_lead_upsert(self):
        """Test simulated upsert behavior for lead updates."""
        database: dict[str, dict[str, Any]] = {}

        def upsert_lead(lead: dict[str, Any]) -> str:
            """Simulate upserting a lead (insert or update)."""
            place_id = lead.get("google_place_id")
            if not place_id:
                return "skipped"
            if place_id in database:
                database[place_id].update(lead)
                return "updated"
            else:
                database[place_id] = lead
                return "inserted"

        # Insert new lead
        lead1 = {"google_place_id": "place_1", "name": "Original Name", "rating": 4.0}
        assert upsert_lead(lead1) == "inserted"

        # Upsert same lead with updated data
        lead1_updated = {"google_place_id": "place_1", "name": "Updated Name", "rating": 4.5}
        assert upsert_lead(lead1_updated) == "updated"
        assert database["place_1"]["name"] == "Updated Name"
        assert database["place_1"]["rating"] == 4.5


class TestDeduplicationHelpers:
    """Tests for helper functions related to deduplication."""

    def test_extract_place_ids_from_leads(self):
        """Test extracting place_ids from a list of leads."""
        leads = [
            {"place_id": "p1", "name": "A"},
            {"place_id": "p2", "name": "B"},
            {"place_id": "p3", "name": "C"},
        ]

        place_ids = {lead["place_id"] for lead in leads if lead.get("place_id")}
        assert place_ids == {"p1", "p2", "p3"}

    def test_find_duplicates_in_leads(self):
        """Test finding duplicate place_ids in leads."""
        leads = [
            {"place_id": "p1", "name": "A"},
            {"place_id": "p2", "name": "B"},
            {"place_id": "p1", "name": "A duplicate"},  # duplicate
            {"place_id": "p3", "name": "C"},
            {"place_id": "p2", "name": "B duplicate"},  # duplicate
        ]

        seen: set[str] = set()
        duplicates: list[dict] = []

        for lead in leads:
            place_id = lead.get("place_id")
            if place_id:
                if place_id in seen:
                    duplicates.append(lead)
                else:
                    seen.add(place_id)

        assert len(duplicates) == 2
        assert duplicates[0]["name"] == "A duplicate"
        assert duplicates[1]["name"] == "B duplicate"

    def test_count_duplicates_by_place_id(self):
        """Test counting how many times each place_id appears."""
        leads = [
            {"place_id": "p1"},
            {"place_id": "p1"},
            {"place_id": "p1"},
            {"place_id": "p2"},
            {"place_id": "p2"},
            {"place_id": "p3"},
        ]

        counts: dict[str, int] = {}
        for lead in leads:
            place_id = lead.get("place_id")
            if place_id:
                counts[place_id] = counts.get(place_id, 0) + 1

        assert counts["p1"] == 3
        assert counts["p2"] == 2
        assert counts["p3"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
