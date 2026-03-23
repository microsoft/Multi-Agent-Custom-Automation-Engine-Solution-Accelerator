"""Configuration and shared fixtures for pytest automation test suite."""

import atexit
import glob
import io
import logging
import os
from datetime import datetime

import pytest
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from pytest_html import extras

from config.constants import URL  # Explicit import instead of wildcard

# Uncomment if login is to be used
# from pages.loginPage import LoginPage

# Create screenshots directory if it doesn't exist
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Configuration for screenshot behavior
# Capture screenshots for all tests by default, set CAPTURE_ALL_SCREENSHOTS=false to disable
CAPTURE_ALL_SCREENSHOTS = os.getenv('CAPTURE_ALL_SCREENSHOTS', 'true').lower() == 'true'

log_streams = {}


def clean_screenshot_filename(test_name):
    """Clean test name to create valid filename for screenshots."""
    # Replace invalid characters for Windows filenames
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', '[', ']']
    clean_name = test_name
    for char in invalid_chars:
        clean_name = clean_name.replace(char, "_")
    # Replace spaces with underscores
    clean_name = clean_name.replace(" ", "_")
    # Remove duplicate underscores
    clean_name = "_".join(filter(None, clean_name.split("_")))
    # Truncate if too long (Windows has 255 char limit)
    if len(clean_name) > 100:
        clean_name = clean_name[:100]
    return clean_name


@pytest.fixture(scope="session")
def login_logout():
    """Perform login once per session and yield a Playwright page instance."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        context.set_default_timeout(120000)
        page = context.new_page()
        page.goto(URL)
        page.wait_for_load_state("networkidle")

        # Uncomment below to perform actual login
        # login_page = LoginPage(page)
        # load_dotenv()
        # login_page.authenticate(os.getenv('user_name'), os.getenv('pass_word'))

        yield page
        browser.close()


@pytest.hookimpl(tryfirst=True)
def pytest_html_report_title(report):
    """Customize HTML report title."""
    report.title = "Test Automation MACAE"


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Attach a log stream to each test for capturing stdout/stderr."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.INFO)

    logger = logging.getLogger()
    logger.addHandler(handler)

    log_streams[item.nodeid] = (handler, stream)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Inject captured logs and screenshots into HTML report for each test."""
    outcome = yield
    report = outcome.get_result()

    # Screenshot logic for failures
    if report.when == "call" and report.failed:
        # Take screenshot for FAILED tests
        if "login_logout" in item.fixturenames:
            page = item.funcargs.get("login_logout")
            if page:
                try:
                    # Generate meaningful screenshot filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    clean_test_name = clean_screenshot_filename(item.name)
                    screenshot_name = f"FAILED_{clean_test_name}_{timestamp}.png"
                    screenshot_path = os.path.join(SCREENSHOTS_DIR, screenshot_name)

                    # Ensure the path is valid before taking screenshot
                    if not os.path.exists(SCREENSHOTS_DIR):
                        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

                    # Take screenshot with error handling
                    page.screenshot(path=screenshot_path, full_page=True)

                    # Verify screenshot was created successfully
                    if os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                        # Add screenshot to HTML report
                        if not hasattr(report, 'extra'):
                            report.extra = []

                        # Use relative path for HTML report
                        relative_screenshot_path = f"screenshots/{screenshot_name}"

                        # Add both image and link to report
                        report.extra.append(extras.image(relative_screenshot_path, name="Failure Screenshot"))
                        report.extra.append(extras.url(relative_screenshot_path, name="Open Screenshot"))

                        logging.info("Screenshot captured for FAILED test: %s", screenshot_path)
                    else:
                        logging.error("Screenshot file was not created or is empty: %s", screenshot_path)
                except Exception as exc:
                    logging.error("Failed to capture screenshot for failed test: %s", str(exc))
            else:
                logging.warning("Page fixture not available for screenshot in failed test: %s", item.name)
        else:
            logging.warning("login_logout fixture not available for screenshot in failed test: %s", item.name)

    # Optional: Take screenshot for all test completion (both pass and fail) if requested
    elif report.when == "call" and CAPTURE_ALL_SCREENSHOTS:
        # Take screenshot for ALL tests (success and failure) for debugging
        if "login_logout" in item.fixturenames:
            page = item.funcargs.get("login_logout")
            if page:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    status = "PASSED" if report.passed else "FAILED"
                    clean_test_name = clean_screenshot_filename(item.name)
                    screenshot_name = f"{status}_{clean_test_name}_{timestamp}.png"
                    screenshot_path = os.path.join(SCREENSHOTS_DIR, screenshot_name)

                    # Ensure the path is valid before taking screenshot
                    if not os.path.exists(SCREENSHOTS_DIR):
                        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

                    page.screenshot(path=screenshot_path, full_page=True)

                    # Verify screenshot was created successfully
                    if os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                        # Add screenshot to report for all tests when enabled
                        if not hasattr(report, 'extra'):
                            report.extra = []

                        relative_screenshot_path = f"screenshots/{screenshot_name}"
                        report.extra.append(extras.image(relative_screenshot_path, name=f"{status} Screenshot"))
                        report.extra.append(extras.url(relative_screenshot_path, name="Open Screenshot"))

                        logging.info("Screenshot captured for %s test: %s", status, screenshot_path)
                    else:
                        logging.error("Screenshot file was not created or is empty: %s", screenshot_path)
                except Exception as exc:
                    logging.error("Failed to capture screenshot: %s", str(exc))

    # Check for any debug screenshots that might have been created and attach them to the report
    if report.when == "call" and report.failed:
        # Look for debug screenshots that match the test
        debug_screenshot_patterns = [
            f"debug_*.png",
            f"debug_{item.name.lower()}.png",
            f"debug_*_{item.name.lower()}.png"
        ]

        for pattern in debug_screenshot_patterns:
            debug_screenshots = glob.glob(os.path.join(SCREENSHOTS_DIR, pattern))
            for debug_screenshot_path in debug_screenshots:
                if os.path.exists(debug_screenshot_path):
                    # Check if this screenshot was created recently (within the last minute)
                    screenshot_time = os.path.getmtime(debug_screenshot_path)
                    current_time = datetime.now().timestamp()

                    if current_time - screenshot_time < 60:  # Within the last minute
                        if not hasattr(report, 'extra'):
                            report.extra = []

                        screenshot_filename = os.path.basename(debug_screenshot_path)
                        relative_debug_path = f"screenshots/{screenshot_filename}"

                        # Add debug screenshot to report
                        report.extra.append(extras.image(relative_debug_path, name=f"Debug Screenshot: {screenshot_filename}"))
                        report.extra.append(extras.url(relative_debug_path, name=f"Open {screenshot_filename}"))

                        logging.info("Debug screenshot attached to report: %s", debug_screenshot_path)

    handler, stream = log_streams.get(item.nodeid, (None, None))

    if handler and stream:
        handler.flush()
        log_output = stream.getvalue()
        logger = logging.getLogger()
        logger.removeHandler(handler)

        report.description = f"<pre>{log_output.strip()}</pre>"
        log_streams.pop(item.nodeid, None)
    else:
        report.description = ""


def pytest_collection_modifyitems(items):
    """Rename test node IDs in HTML report based on parametrized prompts."""
    for item in items:
        if hasattr(item, "callspec"):
            prompt = item.callspec.params.get("prompt")
            if prompt:
                item._nodeid = prompt


def rename_duration_column():
    """Post-process HTML report to rename 'Duration' column to 'Execution Time'."""
    report_path = os.path.abspath("report.html")
    if not os.path.exists(report_path):
        print("Report file not found, skipping column rename.")
        return

    with open(report_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    headers = soup.select("table#results-table thead th")
    for th in headers:
        if th.text.strip() == "Duration":
            th.string = "Execution Time"
            break
    else:
        print("'Duration' column not found in report.")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(str(soup))


# Register the report modification function to run after tests

atexit.register(rename_duration_column)

