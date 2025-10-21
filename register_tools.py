#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Register GitHub Issues Analyzer MCP tools with watsonx.orchestrate

This script registers the MCP tools defined in github_issues_mcp.py with watsonx.orchestrate.
"""

import os
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

def main():
    """Register MCP tools with watsonx.orchestrate."""
    try:
        # Import the register_mcp_tools function
        try:
            from github_issues_mcp import register_mcp_tools
        except ImportError:
            log.error("github_issues_mcp.py must be in the same directory or in the Python path")
            return False
        
        # Register the tools
        result = register_mcp_tools()
        
        if result:
            log.info("Successfully registered GitHub Issues Analyzer MCP tools with watsonx.orchestrate")
            return True
        else:
            log.error("Failed to register MCP tools")
            return False
    except Exception as e:
        log.error(f"Error registering MCP tools: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

# Made with Bob
