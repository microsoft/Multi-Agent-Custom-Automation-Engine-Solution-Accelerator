"""Configuration and shared fixtures for pytest automation test suite."""

import atexit
import io
import logging
import os

import pytest
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from config.constants import URL  # Explicit import instead of wildcard

# Uncomment if login is to be used
# from pages.loginPage import LoginPage


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
    report.title = "Test Automation MACAE-v3 GP"


log_streams = {}


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
    """Inject captured logs into HTML report for each test."""
    outcome = yield
    report = outcome.get_result()

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

