# Automation Proof Of Concept for BIAB Accelerator

Write end-to-end tests for your web apps with [Playwright](https://github.com/microsoft/playwright-python) and [pytest](https://docs.pytest.org/en/stable/).

- Support for **all modern browsers** including Chromium, WebKit and Firefox.
- Support for **headless and headed** execution.
- **Built-in fixtures** that provide browser primitives to test functions.

Pre-Requisites:  

- Install Visual Studio Code: Download and Install Visual Studio Code(VSCode).
- Install NodeJS: Download and Install Node JS

Create and Activate Python Virtual Environment

- From your directory open and run cmd : "python -m venv microsoft"
This will create a virtual environment directory named microsoft inside your current directory
- To enable virtual environment, copy location for "microsoft\Scripts\activate.bat" and run from cmd

Installing Playwright Pytest from Virtual Environment

- To install libraries run "pip install -r requirements.txt"


Run test cases

- To run test cases from your 'tests/e2e-test' folder : "pytest --html=report.html --self-contained-html"

Create .env file in project root level with web app url and client credentials

- create a .env file in project root level and the application url. please refer 'sample_dotenv_file.txt' file.

## Documentation

See on [playwright.dev](https://playwright.dev/python/docs/test-runners) for examples and more detailed information.
