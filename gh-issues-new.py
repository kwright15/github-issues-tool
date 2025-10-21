#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Export GitHub issues to CSV, Excel, or JSON, including comments, labels, and project status.
Specifically designed for GitHub Projects V2 using the GraphQL API.

Usages:
1) As a library/tool (recommended for Agent Lab):
   from gh_issues_tool import export_github_issues
   export_github_issues(repo="org/repo", token="...", include_comments=True, output_path="github_issues.csv")

2) As a CLI (local):
   python gh_issues_tool.py --repo org/repo --token $GH_TOKEN --output github_issues.csv

Dependencies:
    pip install -r requirements.txt
"""

import os
import sys
import csv
import html
import re
import json
import logging
import argparse
import time
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union, Set, Tuple, Literal, TypedDict, cast
from pathlib import Path
from enum import Enum
from functools import wraps

import requests

# Optional imports - will be checked at runtime
OPTIONAL_DEPS_AVAILABLE = False
try:
    import httpx
    import aiohttp
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    from tqdm import tqdm
    import pandas as pd
    from pydantic import BaseModel, Field, validator
    OPTIONAL_DEPS_AVAILABLE = True
except ImportError:
    pass

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
class ExportFormat(str, Enum):
    """Supported export formats."""
    CSV = "csv"
    EXCEL = "xlsx"
    JSON = "json"

# Field names
FIELD_STATUS = "Status"
FIELD_ISSUE_NUMBER = "Issue Number"
FIELD_TITLE = "Title"
FIELD_STATE = "State"
FIELD_CREATED_DATE = "Created Date"
FIELD_CLOSED_DATE = "Closed Date"
FIELD_UPDATED_DATE = "Updated Date"
FIELD_LABELS = "Labels"
FIELD_COMMENTS = "Comments"
FIELD_PROJECT_COLUMN = "Project Column"
FIELD_ASSIGNEES = "Assignees"
FIELD_MILESTONE = "Milestone"
FIELD_URL = "URL"
FIELD_BODY = "Body"

# Default field list for exports
DEFAULT_FIELDS = [
    FIELD_ISSUE_NUMBER,
    FIELD_TITLE,
    FIELD_STATE,
    FIELD_CREATED_DATE,
    FIELD_CLOSED_DATE,
    FIELD_LABELS,
    FIELD_COMMENTS,
    FIELD_PROJECT_COLUMN
]

# API constants
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2
RATE_LIMIT_WAIT_SECONDS = 60
BATCH_SIZE = 50
CONCURRENT_REQUESTS = 5

# ----------------------------------------------------------------------
# Logging Setup
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Defaults (can be overridden via function args or CLI)
# ----------------------------------------------------------------------
DEFAULT_GITHUB_API_URL = os.getenv("GHES_API_URL", "https://github.ibm.com/api/v3")
DEFAULT_REPO = os.getenv("GH_REPO", "customer-success-management/data-watsonx")
DEFAULT_TOKEN = os.getenv("GH_TOKEN")
DEFAULT_OUTPUT_FORMAT = ExportFormat.CSV

# ----------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------
# Define IssueFilter class based on whether pydantic is available
if OPTIONAL_DEPS_AVAILABLE:
    class IssueFilterModel(BaseModel):
        """Filter criteria for issues."""
        state: Optional[str] = None  # "open", "closed", or "all"
        labels: Optional[List[str]] = None
        since: Optional[datetime] = None
        assignee: Optional[str] = None
        creator: Optional[str] = None
        mentioned: Optional[str] = None
        milestone: Optional[str] = None

        @validator('since', pre=True)
        def parse_datetime(cls, v):
            if isinstance(v, str):
                try:
                    return datetime.fromisoformat(v.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        return datetime.strptime(v, "%Y-%m-%d")
                    except ValueError:
                        raise ValueError(f"Invalid date format: {v}")
            return v
    
    IssueFilter = IssueFilterModel
else:
    # Fallback if pydantic is not available
    class IssueFilter:
        def __init__(self, state=None, labels=None, since=None, assignee=None, 
                    creator=None, mentioned=None, milestone=None):
            self.state = state
            self.labels = labels
            self.since = since
            self.assignee = assignee
            self.creator = creator
            self.mentioned = mentioned
            self.milestone = milestone

class Issue(TypedDict, total=False):
    """Type definition for GitHub issue data."""
    number: int
    title: str
    state: str
    created_at: str
    closed_at: Optional[str]
    updated_at: str
    labels: List[Dict[str, str]]
    comments_data: List[Dict[str, Any]]
    project_column: Optional[str]
    assignees: List[Dict[str, str]]
    milestone: Optional[Dict[str, Any]]
    html_url: str
    body: Optional[str]

# ----------------------------------------------------------------------
# GitHub API Helpers
# ----------------------------------------------------------------------
def retry_decorator(max_retries=MAX_RETRIES, backoff_factor=RETRY_BACKOFF_FACTOR):
    """Simple retry decorator for when tenacity is not available."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    retries += 1
                    if retries > max_retries:
                        raise
                    wait_time = backoff_factor * (2 ** (retries - 1))
                    log.warning(f"Request failed: {str(e)}. Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
        return wrapper
    return decorator

# Define gh_paginate based on whether tenacity is available
if OPTIONAL_DEPS_AVAILABLE:
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=RETRY_BACKOFF_FACTOR),
        retry=retry_if_exception_type((requests.exceptions.RequestException, httpx.HTTPError))
    )
    def gh_paginate(url: str, *, headers: dict, params: dict | None = None) -> List[Dict[str, Any]]:
        """Fetch all items from a paginated GitHub REST API endpoint with retry logic."""
        items: List[Dict[str, Any]] = []
        params = params or {}
        
        while url:
            try:
                resp = requests.get(url, headers=headers, params=params)
                
                # Check for rate limiting
                if resp.status_code == 403 and 'X-RateLimit-Remaining' in resp.headers:
                    remaining = int(resp.headers.get('X-RateLimit-Remaining', '1'))
                    if remaining == 0:
                        reset_time = int(resp.headers.get('X-RateLimit-Reset', '0'))
                        sleep_time = max(0, reset_time - time.time()) + 1
                        log.warning(f"Rate limit exceeded. Waiting {sleep_time:.1f} seconds...")
                        time.sleep(sleep_time)
                        continue
                
                resp.raise_for_status()
                
                batch = resp.json()
                items.extend(batch if isinstance(batch, list) else batch.get("items", []))
                
                # Check for next page in Link header
                link_header = resp.headers.get("Link", "")
                next_url = None
                for link in link_header.split(","):
                    if 'rel="next"' in link:
                        next_url = link[link.find("<") + 1 : link.find(">")]
                        break
                url = next_url or ""
                    
            except requests.exceptions.RequestException as e:
                log.error(f"Error during API request: {str(e)}")
                raise
                
        return items
else:
    @retry_decorator()
    def gh_paginate(url: str, *, headers: dict, params: dict | None = None) -> List[Dict[str, Any]]:
        """Fetch all items from a paginated GitHub REST API endpoint with retry logic."""
        items: List[Dict[str, Any]] = []
        params = params or {}
        
        while url:
            try:
                resp = requests.get(url, headers=headers, params=params)
                
                # Check for rate limiting
                if resp.status_code == 403 and 'X-RateLimit-Remaining' in resp.headers:
                    remaining = int(resp.headers.get('X-RateLimit-Remaining', '1'))
                    if remaining == 0:
                        reset_time = int(resp.headers.get('X-RateLimit-Reset', '0'))
                        sleep_time = max(0, reset_time - time.time()) + 1
                        log.warning(f"Rate limit exceeded. Waiting {sleep_time:.1f} seconds...")
                        time.sleep(sleep_time)
                        continue
                
                resp.raise_for_status()
                
                batch = resp.json()
                items.extend(batch if isinstance(batch, list) else batch.get("items", []))
                
                # Check for next page in Link header
                link_header = resp.headers.get("Link", "")
                next_url = None
                for link in link_header.split(","):
                    if 'rel="next"' in link:
                        next_url = link[link.find("<") + 1 : link.find(">")]
                        break
                url = next_url or ""
                    
            except requests.exceptions.RequestException as e:
                log.error(f"Error during API request: {str(e)}")
                raise
                
        return items

# Async functions only available if aiohttp is installed
if OPTIONAL_DEPS_AVAILABLE:
    async def gh_paginate_async(url: str, *, headers: dict, params: dict | None = None, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """Fetch all items from a paginated GitHub REST API endpoint asynchronously."""
        items: List[Dict[str, Any]] = []
        params = params or {}
        
        while url:
            try:
                async with session.get(url, headers=headers, params=params) as resp:
                    # Check for rate limiting
                    if resp.status == 403 and 'X-RateLimit-Remaining' in resp.headers:
                        remaining = int(resp.headers.get('X-RateLimit-Remaining', '1'))
                        if remaining == 0:
                            reset_time = int(resp.headers.get('X-RateLimit-Reset', '0'))
                            sleep_time = max(0, reset_time - time.time()) + 1
                            log.warning(f"Rate limit exceeded. Waiting {sleep_time:.1f} seconds...")
                            await asyncio.sleep(sleep_time)
                            continue
                    
                    resp.raise_for_status()
                    batch = await resp.json()
                    items.extend(batch if isinstance(batch, list) else batch.get("items", []))
                    
                    # Check for next page in Link header
                    link_header = resp.headers.get("Link", "")
                    next_url = None
                    for link in link_header.split(","):
                        if 'rel="next"' in link:
                            next_url = link[link.find("<") + 1 : link.find(">")]
                            break
                    url = next_url or ""
            except aiohttp.ClientError as e:
                log.error(f"Error during async API request: {str(e)}")
                raise
                
        return items

_project_status_cache = {}

# Define cache_all_project_statuses based on whether aiohttp is available
if OPTIONAL_DEPS_AVAILABLE:
    async def cache_all_project_statuses_async(graphql_url: str, *, headers: dict, org: str, session: aiohttp.ClientSession) -> None:
        """Pre-fetch all project statuses to avoid individual API calls."""
        try:
            query = """
            query($org: String!, $cursor: String) {
              organization(login: $org) {
                projectV2(number: 2) {
                  items(first: 100, after: $cursor) {
                    pageInfo {
                      hasNextPage
                      endCursor
                    }
                    nodes {
                      content {
                        ... on Issue {
                          number
                        }
                      }
                      fieldValues(first: 20) {
                        nodes {
                          ... on ProjectV2ItemFieldSingleSelectValue {
                            name
                            field {
                              ... on ProjectV2SingleSelectField {
                                name
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
            """
            # org taken from arguments
            cursor = None
            
            while True:
                graphql_headers = {**headers, "Accept": "application/vnd.github.starfox-preview+json"}
                async with session.post(
                    graphql_url,
                    headers=graphql_headers,
                    json={"query": query, "variables": {"org": org, "cursor": cursor}}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "errors" in data:
                            log.error(f"GraphQL errors while caching statuses: {data['errors']}")
                            return
                        
                        project_data = data.get("data", {}).get("organization", {}).get("projectV2", {})
                        if project_data:
                            items_data = project_data.get("items", {})
                            
                            for item in items_data.get("nodes", []):
                                content = item.get("content", {})
                                if not content:
                                    continue
                                    
                                issue_number = content.get("number")
                                if not issue_number:
                                    continue
                                    
                                field_values = item.get("fieldValues", {}).get("nodes", [])
                                status = "No status set"
                                
                                for value in field_values:
                                    if value and value.get("field", {}).get("name") == FIELD_STATUS:
                                        status = value.get("name")
                                        break
                                        
                                _project_status_cache[issue_number] = status
                            
                            # Check for more pages
                            page_info = items_data.get("pageInfo", {})
                            if page_info.get("hasNextPage"):
                                cursor = page_info.get("endCursor")
                            else:
                                break
                    else:
                        log.error(f"Error fetching project statuses: {response.status}")
                        break
                        
        except Exception as e:
            log.error(f"Error caching project statuses: {str(e)}")

def cache_all_project_statuses(graphql_url: str, *, headers: dict, org: str) -> None:
    """Pre-fetch all project statuses to avoid individual API calls."""
    try:
        query = """
        query($org: String!, $cursor: String) {
          organization(login: $org) {
            projectV2(number: 2) {
              items(first: 100, after: $cursor) {
                pageInfo {
                  hasNextPage
                  endCursor
                }
                nodes {
                  content {
                    ... on Issue {
                      number
                    }
                  }
                  fieldValues(first: 20) {
                    nodes {
                      ... on ProjectV2ItemFieldSingleSelectValue {
                        name
                        field {
                          ... on ProjectV2SingleSelectField {
                            name
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        # org taken from arguments
        cursor = None
        
        while True:
            graphql_headers = {**headers, "Accept": "application/vnd.github.starfox-preview+json"}
            response = requests.post(
                graphql_url,
                headers=graphql_headers,
                json={"query": query, "variables": {"org": org, "cursor": cursor}}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    log.error(f"GraphQL errors while caching statuses: {data['errors']}")
                    return
                
                project_data = data.get("data", {}).get("organization", {}).get("projectV2", {})
                if project_data:
                    items_data = project_data.get("items", {})
                    
                    for item in items_data.get("nodes", []):
                        content = item.get("content", {})
                        if not content:
                            continue
                            
                        issue_number = content.get("number")
                        if not issue_number:
                            continue
                            
                        field_values = item.get("fieldValues", {}).get("nodes", [])
                        status = "No status set"
                        
                        for value in field_values:
                            if value and value.get("field", {}).get("name") == FIELD_STATUS:
                                status = value.get("name")
                                break
                                
                        _project_status_cache[issue_number] = status
                    
                    # Check for more pages
                    page_info = items_data.get("pageInfo", {})
                    if page_info.get("hasNextPage"):
                        cursor = page_info.get("endCursor")
                    else:
                        break
            else:
                log.error(f"Error fetching project statuses: {response.status_code}")
                break
                
    except Exception as e:
        log.error(f"Error caching project statuses: {str(e)}")

def get_issue_project_column(issue_number: int) -> Optional[str]:
    """Get the project column (status) for an issue from cache."""
    return _project_status_cache.get(issue_number, None)

# GraphQL issues query only available if aiohttp is installed
if OPTIONAL_DEPS_AVAILABLE:
    async def get_issues_graphql(repo: str, *, graphql_url: str, headers: dict, session: aiohttp.ClientSession, 
                                filter_params: Optional[IssueFilter] = None) -> List[Dict[str, Any]]:
        """Fetch issues using GraphQL API for better efficiency."""
        org, repo_name = repo.split("/")
        issues = []
        cursor = None
        
        # Build filter conditions
        filter_conditions = []
        if filter_params:
            if filter_params.state and filter_params.state != "all":
                filter_conditions.append(f"states: {filter_params.state.upper()}")
            if filter_params.labels:
                labels_str = ", ".join([f'"{label}"' for label in filter_params.labels])
                filter_conditions.append(f"labels: [{labels_str}]")
            if filter_params.since:
                since_str = filter_params.since.isoformat()
                filter_conditions.append(f'filterBy: {{since: "{since_str}"}}')
        
        filter_string = ", ".join(filter_conditions)
        if filter_string:
            filter_string = f"({filter_string})"
        
        query = f"""
        query($owner: String!, $name: String!, $cursor: String) {{
          repository(owner: $owner, name: $name) {{
            issues{filter_string} (first: 100, after: $cursor, orderBy: {{field: CREATED_AT, direction: DESC}}) {{
              pageInfo {{
                hasNextPage
                endCursor
              }}
              nodes {{
                number
                title
                state
                createdAt
                closedAt
                updatedAt
                url
                bodyText
                labels(first: 10) {{
                  nodes {{
                    name
                  }}
                }}
                assignees(first: 5) {{
                  nodes {{
                    login
                  }}
                }}
                milestone {{
                  title
                }}
              }}
            }}
          }}
        }}
        """
        
        try:
            while True:
                graphql_headers = {**headers, "Accept": "application/vnd.github.starfox-preview+json"}
                async with session.post(
                    graphql_url,
                    headers=graphql_headers,
                    json={"query": query, "variables": {"owner": org, "name": repo_name, "cursor": cursor}}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "errors" in data:
                            log.error(f"GraphQL errors while fetching issues: {data['errors']}")
                            break
                        
                        issues_data = data.get("data", {}).get("repository", {}).get("issues", {})
                        
                        for issue in issues_data.get("nodes", []):
                            # Convert GraphQL format to REST API format for consistency
                            formatted_issue = {
                                "number": issue["number"],
                                "title": issue["title"],
                                "state": issue["state"].lower(),
                                "created_at": issue["createdAt"],
                                "closed_at": issue["closedAt"],
                                "updated_at": issue["updatedAt"],
                                "html_url": issue["url"],
                                "body": issue["bodyText"],
                                "labels": [{"name": label["name"]} for label in issue.get("labels", {}).get("nodes", [])],
                                "assignees": [{"login": assignee["login"]} for assignee in issue.get("assignees", {}).get("nodes", [])],
                            }
                            
                            if issue.get("milestone"):
                                formatted_issue["milestone"] = {"title": issue["milestone"]["title"]}
                            
                            issues.append(formatted_issue)
                        
                        # Check for more pages
                        page_info = issues_data.get("pageInfo", {})
                        if page_info.get("hasNextPage"):
                            cursor = page_info.get("endCursor")
                        else:
                            break
                    else:
                        log.error(f"Error fetching issues via GraphQL: {response.status}")
                        break
        except Exception as e:
            log.error(f"Error in GraphQL issues query: {str(e)}")
        
        return issues

def get_issues(repo: str, *, api_url: str, headers: dict) -> List[Dict[str, Any]]:
    """Fetch all issues from a repository."""
    url = f"{api_url}/repos/{repo}/issues"
    return gh_paginate(url, headers=headers, params={"state": "all", "per_page": 100})

def get_comments(repo: str, issue_number: int, *, api_url: str, headers: dict) -> List[Dict[str, Any]]:
    """Fetch all comments for an issue."""
    url = f"{api_url}/repos/{repo}/issues/{issue_number}/comments"
    return gh_paginate(url, headers=headers, params={"per_page": 100})

# Async comments fetching only available if aiohttp is installed
if OPTIONAL_DEPS_AVAILABLE:
    async def get_comments_async(repo: str, issue_number: int, *, api_url: str, headers: dict, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """Fetch all comments for an issue asynchronously."""
        url = f"{api_url}/repos/{repo}/issues/{issue_number}/comments"
        try:
            return await gh_paginate_async(url, headers=headers, params={"per_page": 100}, session=session)
        except Exception as e:
            log.warning(f"Failed to fetch comments for issue #{issue_number}: {str(e)}")
            return []

    async def process_issues_batch(issues: List[Dict[str, Any]], repo: str, *, api_url: str, headers: dict, 
                                include_comments: bool) -> List[Issue]:
        """Process a batch of issues concurrently."""
        processed_issues: List[Issue] = []
        
        async with aiohttp.ClientSession() as session:
            if include_comments:
                # Fetch comments for all issues in the batch concurrently
                tasks = []
                for issue in issues:
                    if "pull_request" not in issue:
                        task = get_comments_async(repo, issue["number"], api_url=api_url, headers=headers, session=session)
                        tasks.append((issue, task))
                
                # Process results as they complete
                for issue, task in tasks:
                    try:
                        comments = await task
                        issue_data = cast(Issue, issue)
                        issue_data["comments_data"] = comments
                        processed_issues.append(issue_data)
                    except Exception as e:
                        log.error(f"Error processing issue #{issue['number']}: {str(e)}")
            else:
                # No comments needed, just process the issues
                for issue in issues:
                    if "pull_request" not in issue:
                        issue_data = cast(Issue, issue)
                        issue_data["comments_data"] = []
                        processed_issues.append(issue_data)
        
        return processed_issues

def sanitise_for_csv(text: str) -> str:
    """Clean text for CSV output."""
    if not text:
        return ""
    text = html.unescape(text)
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()

def validate_repo_format(repo: str) -> bool:
    """Validate repository format (org/repo)."""
    return bool(re.match(r'^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$', repo))

def validate_token(token: str) -> bool:
    """Basic validation for GitHub token format."""
    # Most tokens are at least 40 chars and alphanumeric
    return bool(token and len(token) >= 40 and re.match(r'^[a-zA-Z0-9_-]+$', token))

def get_export_format(output_path: str) -> ExportFormat:
    """Determine export format from file extension."""
    ext = os.path.splitext(output_path)[1].lower()
    if ext == '.xlsx':
        return ExportFormat.EXCEL
    elif ext == '.json':
        return ExportFormat.JSON
    else:
        return ExportFormat.CSV

# ----------------------------------------------------------------------
# Export functions
# ----------------------------------------------------------------------
def export_to_csv(issues: List[Issue], output_path: str, fields: List[str]) -> None:
    """Export issues to CSV format."""
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=fields,
            quoting=csv.QUOTE_ALL,
            escapechar="\\"
        )
        writer.writeheader()
        
        for issue in issues:
            row: Dict[str, str] = {field: "" for field in fields}
            
            if FIELD_ISSUE_NUMBER in fields and "number" in issue:
                row[FIELD_ISSUE_NUMBER] = str(issue["number"])
            
            if FIELD_TITLE in fields:
                row[FIELD_TITLE] = sanitise_for_csv(issue.get("title", ""))
            
            if FIELD_STATE in fields:
                row[FIELD_STATE] = issue.get("state", "")
            
            if FIELD_CREATED_DATE in fields and "created_at" in issue:
                row[FIELD_CREATED_DATE] = issue["created_at"].split("T")[0] if issue["created_at"] else ""
            
            if FIELD_CLOSED_DATE in fields and "closed_at" in issue:
                row[FIELD_CLOSED_DATE] = issue["closed_at"].split("T")[0] if issue["closed_at"] else ""
                
            if FIELD_UPDATED_DATE in fields and "updated_at" in issue:
                row[FIELD_UPDATED_DATE] = issue["updated_at"].split("T")[0] if issue["updated_at"] else ""
            
            if FIELD_LABELS in fields:
                row[FIELD_LABELS] = ", ".join(lbl["name"] for lbl in issue.get("labels", []))
            
            if FIELD_COMMENTS in fields and "comments_data" in issue:
                row[FIELD_COMMENTS] = sanitise_for_csv(
                    "\n".join(f"{c['user']['login']}: {c['body']}" for c in issue.get("comments_data", []))
                )
            
            if FIELD_PROJECT_COLUMN in fields and "number" in issue:
                column_name = get_issue_project_column(issue["number"])
                row[FIELD_PROJECT_COLUMN] = "" if column_name == "No status set" or column_name is None else column_name
                
            if FIELD_ASSIGNEES in fields:
                row[FIELD_ASSIGNEES] = ", ".join(a["login"] for a in issue.get("assignees", []))
                
            if FIELD_MILESTONE in fields and "milestone" in issue and issue["milestone"]:
                row[FIELD_MILESTONE] = issue["milestone"]["title"]
                
            if FIELD_URL in fields:
                row[FIELD_URL] = issue.get("html_url", "")
                
            if FIELD_BODY in fields:
                row[FIELD_BODY] = sanitise_for_csv(issue.get("body") or "")
            
            writer.writerow(row)

def export_to_excel(issues: List[Issue], output_path: str, fields: List[str]) -> None:
    """Export issues to Excel format."""
    if not OPTIONAL_DEPS_AVAILABLE:
        raise ImportError("pandas and openpyxl are required for Excel export. Install with: pip install pandas openpyxl")
        
    # Convert issues to pandas DataFrame
    data = []
    for issue in issues:
        row = {}
        
        if FIELD_ISSUE_NUMBER in fields and "number" in issue:
            row[FIELD_ISSUE_NUMBER] = issue["number"]
        
        if FIELD_TITLE in fields:
            row[FIELD_TITLE] = sanitise_for_csv(issue.get("title", ""))
        
        if FIELD_STATE in fields:
            row[FIELD_STATE] = issue.get("state", "")
        
        if FIELD_CREATED_DATE in fields and "created_at" in issue:
            row[FIELD_CREATED_DATE] = issue["created_at"].split("T")[0] if issue["created_at"] else ""
        
        if FIELD_CLOSED_DATE in fields and "closed_

# Made with Bob
