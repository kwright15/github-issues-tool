#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Export GitHub issues to CSV, including comments, labels, and project status.
Specifically designed for GitHub Projects V2 using the GraphQL API.

Requirements:
    pip install requests
"""

import os
import sys
import csv
import html
import re
import logging
from typing import List, Dict, Any, Optional

import requests

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
# Configuration
# ----------------------------------------------------------------------
GITHUB_API_URL = os.getenv("GHES_API_URL", "https://github.ibm.com/api/v3")
GRAPHQL_URL = GITHUB_API_URL.replace("/api/v3", "/api/graphql")
REPO = os.getenv("GH_REPO", "customer-success-management/data-watsonx")
TOKEN = os.getenv("GH_TOKEN")

if not TOKEN:
    sys.stderr.write("❌  Error: set the GH_TOKEN environment variable.\n")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "gh-issues-to-csv",
}

# ----------------------------------------------------------------------
# GitHub API Helpers
# ----------------------------------------------------------------------
def gh_paginate(url: str, *, headers: dict, params: dict | None = None) -> List[Dict[str, Any]]:
    """Fetch all items from a paginated GitHub REST API endpoint."""
    items: List[Dict[str, Any]] = []
    params = params or {}
    
    while url:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        
        batch = resp.json()
        items.extend(batch if isinstance(batch, list) else batch.get("items", []))
        
        # Check for next page in Link header
        link_header = resp.headers.get("Link", "")
        url = None
        for link in link_header.split(","):
            if 'rel="next"' in link:
                url = link[link.find("<") + 1 : link.find(">")]
                break
                
    return items

_project_status_cache = {}

def cache_all_project_statuses() -> None:
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
        org = REPO.split('/')[0]
        cursor = None
        
        while True:
            graphql_headers = {**HEADERS, "Accept": "application/vnd.github.starfox-preview+json"}
            response = requests.post(
                GRAPHQL_URL,
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
                            if value and value.get("field", {}).get("name") == "Status":
                                status = value.get("name")
                                break
                                
                        _project_status_cache[issue_number] = status
                    
                    # Check for more pages
                    page_info = items_data.get("pageInfo", {})
                    if page_info.get("hasNextPage"):
                        cursor = page_info.get("endCursor")
                    else:
                        break
                        
    except Exception as e:
        log.error(f"Error caching project statuses: {str(e)}")

def get_issue_project_column(issue_number: int) -> Optional[str]:
    """Get the project column (status) for an issue from cache."""
    return _project_status_cache.get(issue_number, None)

def get_issues(repo: str) -> List[Dict[str, Any]]:
    """Fetch all issues from a repository."""
    url = f"{GITHUB_API_URL}/repos/{repo}/issues"
    return gh_paginate(url, headers=HEADERS, params={"state": "all", "per_page": 100})

def get_comments(repo: str, issue_number: int) -> List[Dict[str, Any]]:
    """Fetch all comments for an issue."""
    url = f"{GITHUB_API_URL}/repos/{repo}/issues/{issue_number}/comments"
    return gh_paginate(url, headers=HEADERS, params={"per_page": 100})

def sanitise_for_csv(text: str) -> str:
    """Clean text for CSV output."""
    if not text:
        return ""
    text = html.unescape(text)
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()

# ----------------------------------------------------------------------
# Main Script
# ----------------------------------------------------------------------
def main() -> None:
    csv_path = "github_issues.csv"
    include_comments = os.getenv("INCLUDE_COMMENTS", "true").lower() == "true"

    # Remove old CSV if it exists
    if os.path.exists(csv_path):
        os.remove(csv_path)

    print("🔎  Fetching issues …")
    issues = get_issues(REPO)
    total_issues = len([i for i in issues if "pull_request" not in i])
    
    print("📊  Caching project statuses …")
    cache_all_project_statuses()
    
    print(f"✨  Processing {total_issues} issues" + 
          ("" if include_comments else " (skipping comments)") + 
          " …")

    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=[
                "Issue Number", "Title", "State", "Created Date", "Closed Date",
                "Labels", "Comments", "Project Column"
            ],
            quoting=csv.QUOTE_ALL,
            escapechar="\\"
        )
        writer.writeheader()

        processed = 0
        for issue in issues:
            if "pull_request" in issue:
                continue

            issue_number = issue["number"]
            
            # Get issue details
            title = sanitise_for_csv(issue.get("title", ""))
            state = issue.get("state", "")
            
            # Format dates (month day year)
            created_date = ""
            if created_at := issue.get("created_at"):
                created_date = created_at.split("T")[0]
                
            closed_date = ""
            if closed_at := issue.get("closed_at"):
                closed_date = closed_at.split("T")[0]
            
            labels = ", ".join(lbl["name"] for lbl in issue.get("labels", []))
            
            # Get comments if enabled
            comments_text = ""
            if include_comments:
                comments = get_comments(REPO, issue_number)
                comments_text = sanitise_for_csv(
                    "\n".join(f"{c['user']['login']}: {c['body']}" for c in comments)
                )
            
            # Get project column from cache
            column_name = get_issue_project_column(issue_number)
            if column_name == "No status set":
                column_name = ""

            # Write to CSV
            writer.writerow({
                "Issue Number": issue_number,
                "Title": title,
                "State": state,
                "Created Date": created_date,
                "Closed Date": closed_date,
                "Labels": labels,
                "Comments": comments_text,
                "Project Column": column_name
            })
            
            processed += 1
            print(f"✅  Processed issue #{issue_number} (total {processed})")

    print(f"\n📊  Done! CSV written to {csv_path}")

if __name__ == "__main__":
    main()
