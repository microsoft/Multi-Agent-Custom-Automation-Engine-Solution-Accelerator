# GitHub Copilot Custom Instructions

This repository is for the Multi-Agent Custom Automation Engine Solution Accelerator. Please follow these instructions to ensure Copilot suggestions align with our architecture, coding standards, and best practices.

## General Guidelines
- Use Python (3.10+) for backend code, and JavaScript (ES6+) for frontend code.
- Backend: Prefer FastAPI for web APIs and asynchronous programming.
- Frontend: Use vanilla JavaScript and Bulma CSS for UI. Avoid introducing new frameworks unless necessary.
- Follow the existing folder structure: `src/backend` for backend, `src/frontend` for frontend, `infra/` for infrastructure-as-code (Bicep).
- Use Azure services (Azure OpenAI, Azure Container Apps, Azure Cosmos DB, Azure Container Registry) for cloud components.
- For infrastructure, prefer Bicep files in `infra/` over scripts. Use managed identity for authentication, never hardcode credentials.
- Always include error handling, logging, and comments for key logic.
- Use English for all code, comments, and documentation.

## Security & Compliance
- Store secrets in Azure Key Vault, not in code or config files.
- Follow the Microsoft Open Source Code of Conduct and security guidelines.
- Do not use or suggest deprecated Azure services or insecure patterns.
- Reference [OpenAI Usage Policies](https://openai.com/policies/usage-policies/) and [Azure OpenAI Code of Conduct](https://learn.microsoft.com/en-us/legal/cognitive-services/openai/code-of-conduct) for responsible AI use.

## Coding Style
- Use clear, descriptive variable and function names.
- Write modular, reusable code with separation of concerns.
- Use async/await for asynchronous operations in both Python and JavaScript.
- Prefer parameterized queries and proper indexing for database access.
- Add docstrings (Python) and JSDoc (JavaScript) for public functions.
- Use consistent indentation (4 spaces for Python, 2 spaces for JS/HTML/CSS).

## Pull Requests & Contributions
- Ensure all new code includes tests where applicable.
- Follow the repository's contribution guidelines in `CONTRIBUTING.md`.
- Reference the `README.md` and `docs/` for architecture and usage patterns.

## Azure Best Practices
- Use managed identity for Azure SDK authentication.
- Never hardcode credentials; use Key Vault.
- Validate deployments with `azd provision --preview` or `az deployment group what-if` before running them.
- Prefer `azd` for deployments; use Bicep for IaC.
- Enable logging, monitoring, and error handling for all Azure resources.

## Responsible AI
- Default to GPT-4o for LLM tasks unless otherwise specified.
- Enable caching for reliability and cost control.
- Do not use the system for medical or financial advice.

---
For more details, see the `README.md`, `docs/`, and `documentation/` folders.
