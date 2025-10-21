#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for GitHub Issues Analyzer

This script tests the GitHub Issues Analyzer with sample data.
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

# Try to import the analyzer class
try:
    from github_issues_agent import GitHubIssuesAnalyzer
except ImportError:
    log.error("github_issues_agent.py must be in the same directory or in the Python path")
    import sys
    sys.exit(1)

# Constants
DEFAULT_GITHUB_TOKEN = os.getenv("GH_TOKEN")
DEFAULT_REPO = os.getenv("GH_REPO", "kwright15/github-issues-tool")
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

def test_summarize_issues():
    """Test the summarize_issues functionality."""
    log.info("Testing summarize_issues...")
    
    try:
        analyzer = GitHubIssuesAnalyzer(repo=DEFAULT_REPO, token=DEFAULT_GITHUB_TOKEN)
        
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
        analyzer = GitHubIssuesAnalyzer(repo=DEFAULT_REPO, token=DEFAULT_GITHUB_TOKEN)
        
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
        analyzer = GitHubIssuesAnalyzer(repo=DEFAULT_REPO, token=DEFAULT_GITHUB_TOKEN)
        
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
        analyzer = GitHubIssuesAnalyzer(repo=DEFAULT_REPO, token=DEFAULT_GITHUB_TOKEN)
        
        # Test for all issues
        result_all = analyzer.suggest_tags()
        save_test_result("suggest_tags_all", result_all)
        
        # Test for a specific issue (if available)
        # This assumes there's at least one issue with number 1
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
        analyzer = GitHubIssuesAnalyzer(repo=DEFAULT_REPO, token=DEFAULT_GITHUB_TOKEN)
        
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
