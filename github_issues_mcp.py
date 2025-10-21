#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GitHub Issues MCP Tool

This file defines a Multi-Cloud Platform (MCP) tool for analyzing GitHub issues.
It leverages the GitHubIssuesAnalyzer class from github_issues_agent.py.

Usage:
    This tool can be imported into watsonx.orchestrate to provide GitHub issue analysis capabilities.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

# Import the analyzer class
from github_issues_agent import GitHubIssuesAnalyzer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Constants
DEFAULT_GITHUB_TOKEN = os.getenv("GH_TOKEN")
DEFAULT_REPO = os.getenv("GH_REPO", "kwright15/github-issues-tool")

def mcp_summarize_issues(
    repo: str = DEFAULT_REPO,
    token: Optional[str] = None,
    by_product: bool = False,
    by_tag: bool = False,
    time_period: Optional[str] = None
) -> Dict[str, Any]:
    """
    MCP tool to summarize GitHub issues by product, tag, or time period.
    
    Args:
        repo: GitHub repository in format 'owner/repo'
        token: GitHub token (optional if GH_TOKEN env var is set)
        by_product: Whether to group by product
        by_tag: Whether to group by tag
        time_period: Time period to filter (e.g., "1w", "1m", "3m", "1y")
        
    Returns:
        Summary of issues
    """
    try:
        analyzer = GitHubIssuesAnalyzer(repo=repo, token=token)
        result = analyzer.summarize_issues(by_product=by_product, by_tag=by_tag, time_period=time_period)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        log.error(f"Error summarizing issues: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

def mcp_analyze_metrics(
    repo: str = DEFAULT_REPO,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    MCP tool to analyze metrics like issue counts, time-to-close, and PM responsiveness.
    
    Args:
        repo: GitHub repository in format 'owner/repo'
        token: GitHub token (optional if GH_TOKEN env var is set)
        
    Returns:
        Analytics information
    """
    try:
        analyzer = GitHubIssuesAnalyzer(repo=repo, token=token)
        result = analyzer.analyze_metrics()
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        log.error(f"Error analyzing metrics: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

def mcp_detect_similar_issues(
    repo: str = DEFAULT_REPO,
    token: Optional[str] = None,
    threshold: float = 0.7
) -> Dict[str, Any]:
    """
    MCP tool to detect similar or duplicate issues.
    
    Args:
        repo: GitHub repository in format 'owner/repo'
        token: GitHub token (optional if GH_TOKEN env var is set)
        threshold: Similarity threshold (0.0 to 1.0)
        
    Returns:
        List of similar issue groups
    """
    try:
        analyzer = GitHubIssuesAnalyzer(repo=repo, token=token)
        result = analyzer.detect_similar_issues(threshold=threshold)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        log.error(f"Error detecting similar issues: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

def mcp_suggest_tags(
    repo: str = DEFAULT_REPO,
    token: Optional[str] = None,
    issue_number: Optional[int] = None
) -> Dict[str, Any]:
    """
    MCP tool to suggest tags based on issue content.
    
    Args:
        repo: GitHub repository in format 'owner/repo'
        token: GitHub token (optional if GH_TOKEN env var is set)
        issue_number: Specific issue number to analyze, or None for all issues
        
    Returns:
        Tag suggestions
    """
    try:
        analyzer = GitHubIssuesAnalyzer(repo=repo, token=token)
        result = analyzer.suggest_tags(issue_number=issue_number)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        log.error(f"Error suggesting tags: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

def mcp_csm_intelligence(
    issue_title: str,
    issue_body: str,
    repo: str = DEFAULT_REPO,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    MCP tool to provide CSM intelligence for new issues.
    
    Args:
        issue_title: Title of the new issue
        issue_body: Body content of the new issue
        repo: GitHub repository in format 'owner/repo'
        token: GitHub token (optional if GH_TOKEN env var is set)
        
    Returns:
        CSM recommendations
    """
    try:
        analyzer = GitHubIssuesAnalyzer(repo=repo, token=token)
        result = analyzer.csm_intelligence(issue_title=issue_title, issue_body=issue_body)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        log.error(f"Error providing CSM intelligence: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

# MCP Tool definitions for watsonx.orchestrate
mcp_tools = {
    "github_issues_summarize": {
        "function": mcp_summarize_issues,
        "description": "Summarize GitHub issues by product, tag, or time period",
        "parameters": {
            "repo": {
                "type": "string",
                "description": "GitHub repository in format 'owner/repo'",
                "default": DEFAULT_REPO
            },
            "token": {
                "type": "string",
                "description": "GitHub token (optional if GH_TOKEN env var is set)",
                "required": False
            },
            "by_product": {
                "type": "boolean",
                "description": "Whether to group by product",
                "default": False
            },
            "by_tag": {
                "type": "boolean",
                "description": "Whether to group by tag",
                "default": False
            },
            "time_period": {
                "type": "string",
                "description": "Time period to filter (e.g., '1w', '1m', '3m', '1y')",
                "required": False
            }
        }
    },
    "github_issues_metrics": {
        "function": mcp_analyze_metrics,
        "description": "Analyze metrics like issue counts, time-to-close, and PM responsiveness",
        "parameters": {
            "repo": {
                "type": "string",
                "description": "GitHub repository in format 'owner/repo'",
                "default": DEFAULT_REPO
            },
            "token": {
                "type": "string",
                "description": "GitHub token (optional if GH_TOKEN env var is set)",
                "required": False
            }
        }
    },
    "github_issues_detect_similar": {
        "function": mcp_detect_similar_issues,
        "description": "Detect similar or duplicate issues",
        "parameters": {
            "repo": {
                "type": "string",
                "description": "GitHub repository in format 'owner/repo'",
                "default": DEFAULT_REPO
            },
            "token": {
                "type": "string",
                "description": "GitHub token (optional if GH_TOKEN env var is set)",
                "required": False
            },
            "threshold": {
                "type": "number",
                "description": "Similarity threshold (0.0 to 1.0)",
                "default": 0.7
            }
        }
    },
    "github_issues_suggest_tags": {
        "function": mcp_suggest_tags,
        "description": "Suggest tags based on issue content",
        "parameters": {
            "repo": {
                "type": "string",
                "description": "GitHub repository in format 'owner/repo'",
                "default": DEFAULT_REPO
            },
            "token": {
                "type": "string",
                "description": "GitHub token (optional if GH_TOKEN env var is set)",
                "required": False
            },
            "issue_number": {
                "type": "integer",
                "description": "Specific issue number to analyze, or None for all issues",
                "required": False
            }
        }
    },
    "github_issues_csm_intelligence": {
        "function": mcp_csm_intelligence,
        "description": "Provide CSM intelligence for new issues",
        "parameters": {
            "issue_title": {
                "type": "string",
                "description": "Title of the new issue"
            },
            "issue_body": {
                "type": "string",
                "description": "Body content of the new issue"
            },
            "repo": {
                "type": "string",
                "description": "GitHub repository in format 'owner/repo'",
                "default": DEFAULT_REPO
            },
            "token": {
                "type": "string",
                "description": "GitHub token (optional if GH_TOKEN env var is set)",
                "required": False
            }
        }
    }
}

# Function to register MCP tools with watsonx.orchestrate
def register_mcp_tools():
    """Register the MCP tools with watsonx.orchestrate."""
    try:
        from ibm_watsonx_orchestrate import register_tool
        
        for tool_name, tool_config in mcp_tools.items():
            register_tool(
                name=tool_name,
                description=tool_config["description"],
                function=tool_config["function"],
                parameters=tool_config["parameters"]
            )
        
        log.info(f"Successfully registered {len(mcp_tools)} GitHub Issues MCP tools")
        return True
    except Exception as e:
        log.error(f"Error registering MCP tools: {str(e)}")
        return False

if __name__ == "__main__":
    # When run directly, register the tools
    register_mcp_tools()

# Made with Bob
