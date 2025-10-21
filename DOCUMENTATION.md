# GitHub Issues Analyzer Documentation

## Overview

The GitHub Issues Analyzer is a tool designed to analyze GitHub issues and provide insights, summaries, and recommendations. It's particularly useful for Customer Success Managers (CSMs) who need to track deployment blockers and other issues.

This tool leverages the watsonx orchestrate ADK to provide intelligent analysis capabilities, including summarization, analytics, deduplication, tagging intelligence, and CSM intelligence.

## Components

The GitHub Issues Analyzer consists of the following components:

1. **gh_issues_tool.py**: Core functionality for exporting GitHub issues to CSV, Excel, or JSON.
2. **github_issues_agent.py**: Main agent that provides analysis capabilities.
3. **github_issues_mcp.py**: MCP tools for integration with watsonx.orchestrate.
4. **test_github_issues_agent.py**: Test script for validating functionality.

## Features

### 1. Summarization

Summarize issues by product, tag, or time period:
- Group issues by product category
- Group issues by tag
- Filter issues by time period (e.g., 1 week, 1 month, 3 months, 1 year)
- Highlight trends and recurring themes

Example usage:
```python
from github_issues_agent import GitHubIssuesAnalyzer

analyzer = GitHubIssuesAnalyzer(repo="org/repo", token="your_github_token")
summary = analyzer.summarize_issues(by_product=True, by_tag=True, time_period="1m")
print(summary)
```

### 2. Analytics

Analyze metrics related to GitHub issues:
- Count of issues opened/closed in a timeframe
- Time-to-close metrics
- PM responsiveness (e.g., time to first comment)

Example usage:
```python
from github_issues_agent import GitHubIssuesAnalyzer

analyzer = GitHubIssuesAnalyzer(repo="org/repo", token="your_github_token")
metrics = analyzer.analyze_metrics()
print(metrics)
```

### 3. Deduplication & Similarity Detection

Identify similar or duplicate issues:
- Flag similar or duplicate issues
- Suggest merging or linking related issues

Example usage:
```python
from github_issues_agent import GitHubIssuesAnalyzer

analyzer = GitHubIssuesAnalyzer(repo="org/repo", token="your_github_token")
similar_issues = analyzer.detect_similar_issues(threshold=0.7)
print(similar_issues)
```

### 4. Tagging Intelligence

Suggest tags based on issue content:
- Recommend appropriate tags for issues
- Improve issue categorization

Example usage:
```python
from github_issues_agent import GitHubIssuesAnalyzer

analyzer = GitHubIssuesAnalyzer(repo="org/repo", token="your_github_token")
tag_suggestions = analyzer.suggest_tags(issue_number=123)
print(tag_suggestions)
```

### 5. CSM Intelligence

Provide guidance for new issues:
- Suggest similar existing issues
- Indicate if the issue has been resolved or is in progress
- Recommend tags or next steps

Example usage:
```python
from github_issues_agent import GitHubIssuesAnalyzer

analyzer = GitHubIssuesAnalyzer(repo="org/repo", token="your_github_token")
csm_recommendations = analyzer.csm_intelligence(
    issue_title="Problem with API authentication",
    issue_body="I'm having trouble authenticating with the API. Getting 401 errors."
)
print(csm_recommendations)
```

## MCP Tools

The GitHub Issues Analyzer provides the following MCP tools for integration with watsonx.orchestrate:

1. **github_issues_summarize**: Summarize GitHub issues by product, tag, or time period.
2. **github_issues_metrics**: Analyze metrics like issue counts, time-to-close, and PM responsiveness.
3. **github_issues_detect_similar**: Detect similar or duplicate issues.
4. **github_issues_suggest_tags**: Suggest tags based on issue content.
5. **github_issues_csm_intelligence**: Provide CSM intelligence for new issues.

To register these tools with watsonx.orchestrate, run:
```python
from github_issues_mcp import register_mcp_tools

register_mcp_tools()
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/kwright15/github-issues-tool.git
   cd github-issues-tool
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   pip install --upgrade ibm-watsonx-orchestrate
   ```

3. Set up environment variables:
   ```
   export GH_TOKEN=your_github_token
   export GH_REPO=your_org/your_repo
   ```

## Usage

### As a Python Library

```python
from github_issues_agent import GitHubIssuesAnalyzer

# Initialize the analyzer
analyzer = GitHubIssuesAnalyzer(
    repo="org/repo",
    token="your_github_token"
)

# Fetch issues
issues_df = analyzer.fetch_issues(include_comments=True)

# Summarize issues
summary = analyzer.summarize_issues(by_product=True, by_tag=True, time_period="1m")

# Analyze metrics
metrics = analyzer.analyze_metrics()

# Detect similar issues
similar_issues = analyzer.detect_similar_issues(threshold=0.7)

# Suggest tags
tag_suggestions = analyzer.suggest_tags(issue_number=123)

# Get CSM intelligence
csm_recommendations = analyzer.csm_intelligence(
    issue_title="Problem with API authentication",
    issue_body="I'm having trouble authenticating with the API. Getting 401 errors."
)
```

### As MCP Tools in watsonx.orchestrate

1. Register the MCP tools:
   ```python
   from github_issues_mcp import register_mcp_tools
   
   register_mcp_tools()
   ```

2. Use the tools in your watsonx.orchestrate workflows.

## Testing

Run the test script to validate functionality:
```
python test_github_issues_agent.py
```

This will run tests for all features and save the results in the `test_output` directory.

## Requirements

- Python 3.8+
- GitHub token with appropriate permissions
- Dependencies listed in requirements.txt
- ibm-watsonx-orchestrate package

## Limitations

- The similarity detection currently uses a simple implementation and could be enhanced with more sophisticated NLP techniques.
- The CSM intelligence feature provides basic recommendations and could be improved with more advanced ML models.
- The tool assumes a specific structure for GitHub issues and may need adjustments for different repositories.

## Future Enhancements

- Implement more advanced NLP for similarity detection
- Add support for GitHub Enterprise
- Integrate with other issue tracking systems
- Enhance visualization of analytics
- Add support for automated issue tagging
- Implement more sophisticated ML models for CSM intelligence