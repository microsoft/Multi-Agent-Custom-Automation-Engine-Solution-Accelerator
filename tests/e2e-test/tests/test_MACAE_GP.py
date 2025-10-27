"""GP Test cases for MACAE."""

import logging
import time

import pytest

from config.constants import (employee_details, product_details,
                              prompt_question1, prompt_question2, rai_prompt)
from pages.BIAB import BIABPage

logger = logging.getLogger(__name__)


# Define test steps and prompts
test_cases = [
    ("Validate home page is loaded", lambda biab: biab.validate_home_page()),
    (
        f"Verify Run Prompt 1: '{prompt_question1}' & run all stages",
        lambda biab: (
            biab.enter_a_question(prompt_question1),
            biab.click_send_button(),
            # biab.click_my_task(),
            biab.enter_aditional_info(employee_details),
            # biab.click_aditional_send_button(),
            biab.processing_different_stage(),
        ),
    ),
    (
        f"Verify Run Prompt 2: '{prompt_question2}' & run all stages",
        lambda biab: (
            biab.click_new_task(),
            biab.enter_a_question(prompt_question2),
            biab.click_send_button(),
            # biab.click_my_task(),
            biab.enter_aditional_info(product_details),
            # biab.click_aditional_send_button(),
            biab.processing_different_stage(),
        ),
    ),
    (
        "Verify Run Prompt 3 via Quick Task - Mobile Plan Query & run all stages",
        lambda biab: (
            biab.click_new_task(),
            biab.click_mobile_plan(),
            biab.click_send_button(),
            # biab.click_my_task(),
            biab.processing_different_stage(),
        ),
    ),
    (
        f"Verify Run RAI Prompt: '{rai_prompt}' to make sure task is not created and validation message is displayed.",
        lambda biab: (
            biab.click_new_task(),
            biab.enter_a_question(rai_prompt),
            biab.validate_rai_validation_message(),
        ),
    ),
]

# Create test IDs like "01. Validate home page", "02. Run Prompt 1: ..."
test_ids = [f"{i + 1:02d}. {case[0]}" for i, case in enumerate(test_cases)]


@pytest.mark.parametrize("prompt, action", test_cases, ids=test_ids)
def test_biab_prompt_case(login_logout, prompt, action, request):
    """Each BIAB prompt runs as an individual test case with execution time logging and meaningful test step titles."""
    page = login_logout
    biab_page = BIABPage(page)
    logger.info(f"Running test step: {prompt}")

    start = time.time()
    if isinstance(action, tuple):
        for step in action:
            if callable(step):
                step()
    else:
        action(biab_page)
    end = time.time()

    duration = end - start
    logger.info(f"Execution Time for '{prompt}': {duration:.2f}s")

    # Attach execution time to pytest report
    request.node._report_sections.append(
        ("call", "log", f"Execution time: {duration:.2f}s")
    )

