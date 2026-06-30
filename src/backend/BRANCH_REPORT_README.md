# Quick Start: Branch Report Generator

Generate Excel reports with branch and PR information from GitHub repositories.

## Quick Demo

Run the sample generator to see an example report:

```bash
cd src/backend
python generate_sample_branch_report.py
```

This creates an Excel file in `/tmp/` with sample branch data.

## Usage Options

### Option 1: API Endpoint (Production)

```bash
curl -X GET "http://localhost:8000/api/v4/generate_branch_report?owner=microsoft&repo=YOUR-REPO" \
  -H "user_principal_id: YOUR-USER-ID" \
  -o branch_report.xlsx
```

### Option 2: Standalone Script

```bash
cd src/backend
python generate_branch_report.py microsoft YOUR-REPO output.xlsx
```

**Note:** Requires `GITHUB_TOKEN` environment variable for private repos.

### Option 3: Sample/Demo Script

```bash
cd src/backend
python generate_sample_branch_report.py
```

Uses demo data - no GitHub token required.

## Excel Report Contents

The generated Excel file includes:

| Branch Name | PR Status | Created By | PR URL | Protected |
|------------|-----------|------------|--------|-----------|
| main | none | Unknown | N/A | Yes |
| feature-branch | open | developer | github.com/... | No |
| hotfix | merged | admin | github.com/... | No |

**Columns:**
1. **Branch Name** - Name of the branch
2. **PR Status** - merged, open, closed, or none
3. **Created By** - Username who created the PR/branch
4. **PR URL** - Link to pull request (if exists)
5. **Protected** - Yes/No branch protection status

## Requirements

Install dependencies:

```bash
pip install openpyxl PyGithub
```

Or install all backend requirements:

```bash
cd src/backend
pip install -r requirements.txt
```

## Environment Setup

For accessing private repositories or avoiding rate limits:

```bash
export GITHUB_TOKEN='your_github_token_here'
```

## Output Format

- Professional Excel spreadsheet (.xlsx)
- Styled headers with blue background
- Alternating row colors for readability
- Auto-sized columns
- Clickable PR URLs

## Example Output

An example report has been generated at `/tmp/example_branch_report.xlsx` containing real branch data from this repository.

## Full Documentation

For detailed documentation, see [docs/branch_report_generator.md](../../docs/branch_report_generator.md)

## Troubleshooting

- **"No GitHub token"** - Export `GITHUB_TOKEN` or use sample generator
- **"403 Forbidden"** - Check token permissions or repository access
- **"Rate limit exceeded"** - Use authenticated requests with valid token

## Support

- Check application logs for detailed errors
- Review the full documentation for advanced usage
- Ensure all prerequisites are installed
