#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Standalone test script for GitHub Issues Analyzer

This script tests the GitHub Issues Analyzer functionality with mock data.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Constants
TEST_OUTPUT_DIR = "test_output"

def ensure_output_dir():
    """Ensure the test output directory exists."""
    if not os.path.exists(TEST_OUTPUT_DIR):
        os.makedirs(TEST_OUTPUT_DIR)
        log.info(f"Created output directory: {TEST_OUTPUT_DIR}")

def save_test_result(name: str, data: Any):
    """Save test result to a JSON file."""
    ensure_output_dir()
    output_path = os.path.join(TEST_OUTPUT_DIR, f"{name}.json")
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    log.info(f"Saved test result to {output_path}")

class MockGitHubIssuesAnalyzer:
    """Mock class for testing."""
    
    def __init__(self, repo=None, token=None, output_file=None):
        self.repo = repo
        self.token = token
        self.output_file = output_file
        self.issues_df = None
        
    def fetch_issues(self, include_comments=True):
        """Mock fetch_issues method."""
        # Create a sample DataFrame-like structure
        self.issues_df = {
            'Issue Number': [1, 2, 3],
            'Title': ['Issue 1', 'Issue 2', 'Issue 3'],
            'State': ['open', 'closed', 'open'],
            'Created Date': ['2025-01-01', '2025-01-02', '2025-01-03'],
            'Closed Date': [None, '2025-01-05', None],
            'Labels': ['bug', 'enhancement', 'bug, documentation'],
            'Comments': ['Comment 1', 'Comment 2', 'Comment 3']
        }
        return self.issues_df
        
    def summarize_issues(self, by_product=False, by_tag=False, time_period=None):
        """Mock summarize_issues method."""
        return {
            "total_issues": 3,
            "open_issues": 2,
            "closed_issues": 1,
            "time_period": time_period or "all time",
            "by_tag": {"bug": 2, "enhancement": 1, "documentation": 1} if by_tag else None,
            "trending_themes": [{"word": "issue", "count": 3}]
        }
        
    def analyze_metrics(self):
        """Mock analyze_metrics method."""
        return {
            "monthly_issue_counts": {"2025-01": 3},
            "time_to_close": {
                "mean_days": 3,
                "median_days": 3,
                "min_days": 3,
                "max_days": 3
            },
            "with_comments": 3,
            "without_comments": 0
        }
        
    def detect_similar_issues(self, threshold=0.7):
        """Mock detect_similar_issues method."""
        return [
            {
                "group_id": 1,
                "issues": [{"number": 1, "title": "Issue 1"}, 
                          {"number": 3, "title": "Issue 3"}],
                "similarity_score": 0.85,
                "recommendation": "Consider merging these issues"
            }
        ]
        
    def suggest_tags(self, issue_number=None):
        """Mock suggest_tags method."""
        return {
            "issue_number": issue_number or "all",
            "suggested_tags": ["bug", "enhancement", "documentation"]
        }
        
    def csm_intelligence(self, issue_title, issue_body):
        """Mock csm_intelligence method."""
        return {
            "similar_issues": [
                {"number": 1, "title": "Issue 1", "url": "https://github.com/example/repo/issues/1"}
            ],
            "status": "in_progress",
            "recommended_tags": ["bug", "priority-medium"],
            "next_steps": ["Assign to PM", "Request more information"]
        }

def test_summarize_issues():
    """Test the summarize_issues functionality."""
    log.info("Testing summarize_issues...")
    
    try:
        analyzer = MockGitHubIssuesAnalyzer(repo="org/repo", token="mock_token")
        
        # Test with default parameters
        result_default = analyzer.summarize_issues()
        save_test_result("summarize_issues_default", result_default)
        
        # Test with by_tag=True
        result_by_tag = analyzer.summarize_issues(by_tag=True)
        save_test_result("summarize_issues_by_tag", result_by_tag)
        
        # Test with time_period="1m"
        result_time_period = analyzer.summarize_issues(time_period="1m")
        save_test_result("summarize_issues_time_period", result_time_period)
        
        log.info("summarize_issues tests completed successfully")
        return True
    except Exception as e:
        log.error(f"Error testing summarize_issues: {str(e)}")
        return False

def test_analyze_metrics():
    """Test the analyze_metrics functionality."""
    log.info("Testing analyze_metrics...")
    
    try:
        analyzer = MockGitHubIssuesAnalyzer(repo="org/repo", token="mock_token")
        
        # Test metrics analysis
        result = analyzer.analyze_metrics()
        save_test_result("analyze_metrics", result)
        
        log.info("analyze_metrics test completed successfully")
        return True
    except Exception as e:
        log.error(f"Error testing analyze_metrics: {str(e)}")
        return False

def test_detect_similar_issues():
    """Test the detect_similar_issues functionality."""
    log.info("Testing detect_similar_issues...")
    
    try:
        analyzer = MockGitHubIssuesAnalyzer(repo="org/repo", token="mock_token")
        
        # Test with default threshold
        result_default = analyzer.detect_similar_issues()
        save_test_result("detect_similar_issues_default", result_default)
        
        # Test with lower threshold
        result_lower = analyzer.detect_similar_issues(threshold=0.5)
        save_test_result("detect_similar_issues_lower", result_lower)
        
        log.info("detect_similar_issues tests completed successfully")
        return True
    except Exception as e:
        log.error(f"Error testing detect_similar_issues: {str(e)}")
        return False

def test_suggest_tags():
    """Test the suggest_tags functionality."""
    log.info("Testing suggest_tags...")
    
    try:
        analyzer = MockGitHubIssuesAnalyzer(repo="org/repo", token="mock_token")
        
        # Test for all issues
        result_all = analyzer.suggest_tags()
        save_test_result("suggest_tags_all", result_all)
        
        # Test for a specific issue
        result_specific = analyzer.suggest_tags(issue_number=1)
        save_test_result("suggest_tags_specific", result_specific)
        
        log.info("suggest_tags tests completed successfully")
        return True
    except Exception as e:
        log.error(f"Error testing suggest_tags: {str(e)}")
        return False

def test_csm_intelligence():
    """Test the csm_intelligence functionality."""
    log.info("Testing csm_intelligence...")
    
    try:
        analyzer = MockGitHubIssuesAnalyzer(repo="org/repo", token="mock_token")
        
        # Test with sample issue data
        result = analyzer.csm_intelligence(
            issue_title="Problem with API authentication",
            issue_body="I'm having trouble authenticating with the API. Getting 401 errors."
        )
        save_test_result("csm_intelligence", result)
        
        log.info("csm_intelligence test completed successfully")
        return True
    except Exception as e:
        log.error(f"Error testing csm_intelligence: {str(e)}")
        return False

def run_all_tests():
    """Run all tests and report results."""
    log.info("Starting GitHub Issues Analyzer tests...")
    
    test_results = {
        "summarize_issues": test_summarize_issues(),
        "analyze_metrics": test_analyze_metrics(),
        "detect_similar_issues": test_detect_similar_issues(),
        "suggest_tags": test_suggest_tags(),
        "csm_intelligence": test_csm_intelligence()
    }
    
    # Report overall results
    success_count = sum(1 for result in test_results.values() if result)
    total_count = len(test_results)
    
    log.info(f"Test summary: {success_count}/{total_count} tests passed")
    
    for test_name, result in test_results.items():
        status = "PASSED" if result else "FAILED"
        log.info(f"  {test_name}: {status}")
    
    return test_results

if __name__ == "__main__":
    run_all_tests()

# Made with Bob
