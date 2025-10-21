# GitHub Issues Tool

A Python tool for exporting GitHub issues to CSV, Excel, or JSON, including comments, labels, and project status. Specifically designed for GitHub Projects V2 using the GraphQL API.

## Features

- Export issues to CSV, Excel, or JSON formats
- Include issue comments, labels, and project status
- Filter issues by state, labels, date, assignee, etc.
- Support for GitHub Projects V2 using GraphQL API
- Asynchronous processing for better performance

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/github-issues-tool.git
   cd github-issues-tool
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Usage

### As a library/tool

```python
from gh_issues_tool import export_github_issues

export_github_issues(
    repo="org/repo",
    token="your_github_token",
    include_comments=True,
    output_path="github_issues.csv"
)
```

### As a CLI

```bash
python gh_issues_tool.py --repo org/repo --token $GH_TOKEN --output github_issues.csv
```

## Dependencies

- requests
- httpx
- aiohttp
- tqdm
- openpyxl
- pandas
- tenacity
- pydantic

## License

MIT