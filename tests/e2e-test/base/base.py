"""Module for storing application-wide constants."""

import os
from dotenv import load_dotenv

# Removed unused import: from config.constants import API_URL


class BasePage:
    """Base class for some common utilities and functions."""

    def __init__(self, page):
        """Initialize the BasePage with a Playwright page instance."""
        self.page = page

    def scroll_into_view(self, locator):
        """Scroll the last element in the locator into view if needed."""
        reference_list = locator
        locator.nth(reference_list.count() - 1).scroll_into_view_if_needed()

    def is_visible(self, locator):
        """Check if the given locator is visible."""
        locator.is_visible()

    def get_first_plan_id(self):
        """Step 1: Get plan list and return the first plan ID."""
        load_dotenv()
        base_url = os.getenv("MACAE_URL_API")

        get_url = f"{base_url}/api/plans"
        headers = {
            "Accept": "*/*",
        }

        response = self.page.request.get(get_url, headers=headers, timeout=120000)

        if response.status != 200:
            raise AssertionError(
                f"❌ GET /api/plan_list failed. Expected 200, got {response.status}. "
                f"Body: {response.text()}"
            )

        plans = response.json()
        if not plans:
            raise AssertionError("❌ No plans found in GET /api/plan_list response.")

        plan_id = plans[0]["id"]
        print(f"✅ Extracted Plan ID: {plan_id}")
        return plan_id

    def approve_plan_by_id(self, plan_id: str):
        """Step 2: Approve plan using the given plan ID."""

        base_url = os.getenv("MACAE_URL_API")

        approve_url = f"{base_url}/api/plans?plan_id={plan_id}"
        headers = {
            "Accept": "*/*",
        }

        response = self.page.request.get(approve_url, headers=headers, timeout=120000)

        if response.status != 200:
            raise AssertionError(
                f"❌ GET /api/plans failed. Expected 200, got {response.status}. "
                f"Body: {response.text()}"
            )


        print("✅ GET approval successful.")

