# Branch Report Generator

This feature allows you to generate Excel reports containing branch information from GitHub repositories.

## Features

The generated Excel report includes:
- **Branch Name**: Name of each branch in the repository
- **PR Status**: Status of associated pull requests (merged, open, closed, or none)
- **Created By**: Username of the person who created the branch
- **PR URL**: Link to the associated pull request (if any)
- **Protected**: Whether the branch is protected
- **Last Commit Date**: Date and time of the last commit on the branch

## Setup

### Prerequisites

1. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up GitHub authentication (required for accessing private repositories and higher rate limits):
   ```bash
   export GITHUB_TOKEN='your_github_personal_access_token'
   ```

   To create a GitHub personal access token:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate a new token with `repo` scope for private repositories
   - For public repositories only, the token is optional but recommended to avoid rate limits

## Usage

### Method 1: API Endpoint

Use the FastAPI endpoint to generate reports:

```bash
GET /api/v4/generate_branch_report?owner=<owner>&repo=<repo>
```

**Parameters:**
- `owner` (required): Repository owner (username or organization)
- `repo` (required): Repository name

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v4/generate_branch_report?owner=microsoft&repo=Multi-Agent-Custom-Automation-Engine-Solution-Accelerator" \
  -H "user_principal_id: your-user-id" \
  -o branch_report.xlsx
```

### Method 2: Standalone Script

Run the standalone script directly:

```bash
cd src/backend
python generate_branch_report.py <owner> <repo> [output_file]
```

**Examples:**
```bash
# Generate report with default filename
python generate_branch_report.py microsoft Multi-Agent-Custom-Automation-Engine-Solution-Accelerator

# Generate report with custom filename
python generate_branch_report.py microsoft Multi-Agent-Custom-Automation-Engine-Solution-Accelerator my_report.xlsx
```

## Output Format

The Excel file contains:
- **Professional formatting** with styled headers
- **Color-coded rows** for easy reading
- **Auto-sized columns** for optimal viewing
- **Clickable PR URLs** (when applicable)

## Troubleshooting

### Rate Limiting

If you encounter rate limiting errors:
- Set the `GITHUB_TOKEN` environment variable with a valid token
- Authenticated requests have a limit of 5,000 requests per hour
- Unauthenticated requests are limited to 60 per hour

### Access Errors

If you cannot access a repository:
- Ensure the repository is public, or your token has access to private repositories
- Verify the owner and repository names are correct
- Check that your token has the necessary scopes (`repo` for private repos)

### No Data

If the report is empty:
- Verify the repository exists and has branches
- Check the console logs for specific error messages
- Ensure network connectivity to GitHub API

## API Rate Limits

GitHub API has the following rate limits:
- **Authenticated**: 5,000 requests per hour
- **Unauthenticated**: 60 requests per hour

Each repository typically requires:
- 1 request to fetch the repository
- 1 request per branch to get details
- 1 request per branch to check for pull requests

For large repositories, consider using authentication to avoid rate limits.

## Security Notes

- Never commit your `GITHUB_TOKEN` to version control
- Use environment variables or secure secret management
- Tokens should have minimal required permissions
- Regularly rotate your tokens for security

## Development

### Testing the Utility

You can test the GitHub Excel Generator utility:

```python
from common.utils.github_excel_generator import GitHubExcelGenerator

# Initialize with token
generator = GitHubExcelGenerator(github_token="your_token")

# Generate report
success = generator.generate_report("microsoft", "Multi-Agent-Custom-Automation-Engine-Solution-Accelerator", "output.xlsx")
```

### Extending the Report

To add more columns to the report, modify:
1. `github_excel_generator.py`: Update `get_branch_info()` to collect additional data
2. `github_excel_generator.py`: Update `generate_excel()` to include new columns in the spreadsheet

## Support

For issues or questions:
- Check the application logs for detailed error messages
- Review GitHub API status at https://www.githubstatus.com/
- Ensure all prerequisites are properly configured
