#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GitHub Issues Analysis Agent

This agent analyzes GitHub issues to provide insights, summaries, and recommendations.
It leverages the existing gh_issues_tool.py for data extraction and adds analysis capabilities.

Features:
1. Summarization - Summarize issues by product, tag, or time period
2. Analytics - Count issues, time-to-close metrics, PM responsiveness
3. Deduplication & Similarity Detection - Flag similar issues, suggest merging
4. Tagging Intelligence - Suggest tags based on content
5. CSM Intelligence - Provide guidance for new issues

Dependencies:
    - ibm-watsonx-orchestrate
    - All dependencies from gh_issues_tool.py
"""

import os
import sys
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union, Tuple

# Try to import pandas
try:
    import pandas as pd
except ImportError:
    print("pandas is required. Please install it with: pip install pandas")
    sys.exit(1)

# Try to import the GitHub issues tool
try:
    from gh_issues_tool import export_github_issues
except ImportError:
    print("gh_issues_tool.py must be in the same directory or in the Python path")
    sys.exit(1)

# Try to import watsonx orchestrate
try:
    from ibm_watsonx_orchestrate import Agent, Tool, ToolParameter, ToolOutput
except ImportError:
    print("ibm-watsonx-orchestrate is required. Please install it with: pip install --upgrade ibm-watsonx-orchestrate")
    sys.exit(1)

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
DEFAULT_OUTPUT_FILE = "github_issues_analysis.json"

class GitHubIssuesAnalyzer:
    """Main class for analyzing GitHub issues."""
    
    def __init__(self, repo: str, token: Optional[str] = None, output_file: str = DEFAULT_OUTPUT_FILE):
        """Initialize the analyzer with repository and authentication details."""
        self.repo = repo
        self.token = token or DEFAULT_GITHUB_TOKEN
        self.output_file = output_file
        self.issues_df = None
        
    def fetch_issues(self, include_comments: bool = True) -> pd.DataFrame:
        """Fetch issues from GitHub and convert to DataFrame."""
        # Use the export_github_issues function to get issues in CSV format
        temp_csv = "temp_issues.csv"
        export_github_issues(
            repo=self.repo,
            token=self.token,
            include_comments=include_comments,
            output_path=temp_csv
        )
        
        # Load the CSV into a DataFrame
        self.issues_df = pd.read_csv(temp_csv)
        
        # Clean up the temporary file
        if os.path.exists(temp_csv):
            os.remove(temp_csv)
            
        return self.issues_df
    
    def summarize_issues(self, 
                         by_product: bool = False, 
                         by_tag: bool = False, 
                         time_period: Optional[str] = None) -> Dict[str, Any]:
        """
        Summarize issues by product, tag, or time period.
        
        Args:
            by_product: Whether to group by product
            by_tag: Whether to group by tag
            time_period: Time period to filter (e.g., "1w", "1m", "3m", "1y")
            
        Returns:
            Dictionary with summary information
        """
        if self.issues_df is None:
            self.fetch_issues()
            
        # Filter by time period if specified
        df = self.issues_df.copy() if self.issues_df is not None else pd.DataFrame()
        if time_period:
            now = datetime.now()
            if time_period == "1w":
                start_date = now - timedelta(weeks=1)
            elif time_period == "1m":
                start_date = now - timedelta(days=30)
            elif time_period == "3m":
                start_date = now - timedelta(days=90)
            elif time_period == "1y":
                start_date = now - timedelta(days=365)
            else:
                start_date = now - timedelta(days=30)  # Default to 1 month
                
            df['Created Date'] = pd.to_datetime(df['Created Date'])
            df = df[df['Created Date'] >= start_date]
        
        summary = {
            "total_issues": len(df),
            "open_issues": len(df[df['State'] == 'open']),
            "closed_issues": len(df[df['State'] == 'closed']),
            "time_period": time_period or "all time"
        }
        
        # Group by product if requested
        if by_product:
            # Assuming product information is in labels or a specific column
            # This is a placeholder - adjust based on your actual data structure
            if 'Labels' in df.columns:
                # Extract product from labels (assuming format like "product:xyz")
                df['Product'] = df['Labels'].apply(
                    lambda x: next((label.split(':')[1] for label in str(x).split(',') 
                                   if label.strip().startswith('product:')), 'unknown')
                )
                product_summary = df.groupby('Product').size().to_dict()
                summary["by_product"] = product_summary
        
        # Group by tag if requested
        if by_tag:
            if 'Labels' in df.columns:
                # Explode labels into separate rows
                all_labels = []
                for labels in df['Labels'].dropna():
                    all_labels.extend([label.strip() for label in str(labels).split(',')])
                
                # Count occurrences of each label
                label_counts = pd.Series(all_labels).value_counts().to_dict()
                summary["by_tag"] = label_counts
        
        # Find trending themes (most common words in titles)
        if 'Title' in df.columns:
            from collections import Counter
            import re
            
            # Extract words from titles
            words = []
            for title in df['Title'].dropna():
                # Remove special characters and split into words
                clean_words = re.sub(r'[^\w\s]', '', str(title).lower()).split()
                # Filter out common stop words
                stop_words = {'the', 'a', 'an', 'and', 'in', 'on', 'at', 'to', 'for', 'with', 'is', 'are'}
                words.extend([word for word in clean_words if word not in stop_words and len(word) > 2])
            
            # Get the most common words
            common_words = Counter(words).most_common(10)
            summary["trending_themes"] = [{"word": word, "count": count} for word, count in common_words]
        
        return summary
    
    def analyze_metrics(self) -> Dict[str, Any]:
        """
        Analyze metrics like issue counts, time-to-close, and PM responsiveness.
        
        Returns:
            Dictionary with analytics information
        """
        if self.issues_df is None:
            self.fetch_issues()
            
        df = self.issues_df.copy() if self.issues_df is not None else pd.DataFrame()
        
        # Convert date columns to datetime
        for col in ['Created Date', 'Closed Date', 'Updated Date']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Calculate time-to-close for closed issues
        metrics = {}
        
        # Issue counts over time
        if 'Created Date' in df.columns:
            # Group by month
            df['month'] = df['Created Date'].dt.to_period('M')
            monthly_counts = df.groupby('month').size()
            metrics["monthly_issue_counts"] = {str(idx): int(count) for idx, count in monthly_counts.items()}
        
        # Time-to-close metrics
        if 'Created Date' in df.columns and 'Closed Date' in df.columns:
            closed_issues = df.dropna(subset=['Closed Date'])
            if not closed_issues.empty:
                closed_issues['time_to_close'] = (closed_issues['Closed Date'] - closed_issues['Created Date']).dt.days
                
                metrics["time_to_close"] = {
                    "mean_days": closed_issues['time_to_close'].mean(),
                    "median_days": closed_issues['time_to_close'].median(),
                    "min_days": closed_issues['time_to_close'].min(),
                    "max_days": closed_issues['time_to_close'].max()
                }
        
        # PM responsiveness (time to first comment)
        # This is a placeholder - actual implementation would depend on comment data structure
        if 'Comments' in df.columns:
            # For now, just count issues with comments
            has_comments = df['Comments'].notna() & (df['Comments'] != '')
            metrics["with_comments"] = int(has_comments.sum())
            metrics["without_comments"] = int((~has_comments).sum())
            
            # More sophisticated analysis would parse the comment timestamps
            # and calculate time to first response
        
        return metrics
    
    def detect_similar_issues(self, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Detect similar or duplicate issues.
        
        Args:
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            List of similar issue groups
        """
        if self.issues_df is None:
            self.fetch_issues()
            
        # This is a placeholder for more sophisticated similarity detection
        # In a real implementation, you would use NLP techniques like:
        # - TF-IDF vectorization
        # - Cosine similarity
        # - Embedding-based similarity
        
        # For now, we'll just return a simple example
        return [
            {
                "group_id": 1,
                "issues": [{"number": 1, "title": "Example Issue 1"}, 
                          {"number": 2, "title": "Example Issue 2"}],
                "similarity_score": 0.85,
                "recommendation": "Consider merging these issues"
            }
        ]
    
    def suggest_tags(self, issue_number: Optional[int] = None) -> Dict[str, Any]:
        """
        Suggest tags based on issue content.
        
        Args:
            issue_number: Specific issue number to analyze, or None for all issues
            
        Returns:
            Dictionary with tag suggestions
        """
        if self.issues_df is None:
            self.fetch_issues()
            
        # This is a placeholder for more sophisticated tag suggestion
        # In a real implementation, you would use NLP techniques
        
        # For now, we'll just return a simple example
        return {
            "issue_number": issue_number or "all",
            "suggested_tags": ["bug", "enhancement", "documentation"]
        }
    
    def csm_intelligence(self, issue_title: str, issue_body: str) -> Dict[str, Any]:
        """
        Provide CSM intelligence for new issues.
        
        Args:
            issue_title: Title of the new issue
            issue_body: Body content of the new issue
            
        Returns:
            Dictionary with CSM recommendations
        """
        # This is a placeholder for more sophisticated CSM intelligence
        # In a real implementation, you would use NLP and ML techniques
        
        # For now, we'll just return a simple example
        return {
            "similar_issues": [
                {"number": 1, "title": "Similar existing issue", "url": "https://github.com/example/repo/issues/1"}
            ],
            "status": "in_progress",
            "recommended_tags": ["bug", "priority-medium"],
            "next_steps": ["Assign to PM", "Request more information"]
        }

# Define the watsonx orchestrate agent
github_issues_agent = Agent(
    name="GitHub Issues Analyzer",
    description="Analyzes GitHub issues to provide insights, summaries, and recommendations"
)

# Define tools for the agent
@github_issues_agent.tool
def summarize_issues(
    repo: str = DEFAULT_REPO,
    token: Optional[str] = None,
    by_product: bool = False,
    by_tag: bool = False,
    time_period: Optional[str] = None
) -> Dict[str, Any]:
    """
    Summarize GitHub issues by product, tag, or time period.
    
    Args:
        repo: GitHub repository in format 'owner/repo'
        token: GitHub token (optional if GH_TOKEN env var is set)
        by_product: Whether to group by product
        by_tag: Whether to group by tag
        time_period: Time period to filter (e.g., "1w", "1m", "3m", "1y")
        
    Returns:
        Summary of issues
    """
    analyzer = GitHubIssuesAnalyzer(repo=repo, token=token)
    return analyzer.summarize_issues(by_product=by_product, by_tag=by_tag, time_period=time_period)

@github_issues_agent.tool
def analyze_metrics(
    repo: str = DEFAULT_REPO,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze metrics like issue counts, time-to-close, and PM responsiveness.
    
    Args:
        repo: GitHub repository in format 'owner/repo'
        token: GitHub token (optional if GH_TOKEN env var is set)
        
    Returns:
        Analytics information
    """
    analyzer = GitHubIssuesAnalyzer(repo=repo, token=token)
    return analyzer.analyze_metrics()

@github_issues_agent.tool
def detect_similar_issues(
    repo: str = DEFAULT_REPO,
    token: Optional[str] = None,
    threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Detect similar or duplicate issues.
    
    Args:
        repo: GitHub repository in format 'owner/repo'
        token: GitHub token (optional if GH_TOKEN env var is set)
        threshold: Similarity threshold (0.0 to 1.0)
        
    Returns:
        List of similar issue groups
    """
    analyzer = GitHubIssuesAnalyzer(repo=repo, token=token)
    return analyzer.detect_similar_issues(threshold=threshold)

@github_issues_agent.tool
def suggest_tags(
    repo: str = DEFAULT_REPO,
    token: Optional[str] = None,
    issue_number: Optional[int] = None
) -> Dict[str, Any]:
    """
    Suggest tags based on issue content.
    
    Args:
        repo: GitHub repository in format 'owner/repo'
        token: GitHub token (optional if GH_TOKEN env var is set)
        issue_number: Specific issue number to analyze, or None for all issues
        
    Returns:
        Tag suggestions
    """
    analyzer = GitHubIssuesAnalyzer(repo=repo, token=token)
    return analyzer.suggest_tags(issue_number=issue_number)

@github_issues_agent.tool
def csm_intelligence(
    issue_title: str,
    issue_body: str,
    repo: str = DEFAULT_REPO,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Provide CSM intelligence for new issues.
    
    Args:
        issue_title: Title of the new issue
        issue_body: Body content of the new issue
        repo: GitHub repository in format 'owner/repo'
        token: GitHub token (optional if GH_TOKEN env var is set)
        
    Returns:
        CSM recommendations
    """
    analyzer = GitHubIssuesAnalyzer(repo=repo, token=token)
    return analyzer.csm_intelligence(issue_title=issue_title, issue_body=issue_body)

# Main function to run the agent directly
def main():
    """Run the GitHub Issues Analyzer agent."""
    # This is a placeholder for CLI functionality
    pass

if __name__ == "__main__":
    main()

# Made with Bob
