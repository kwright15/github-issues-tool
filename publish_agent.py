#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Publish GitHub Issues Analyzer agent to watsonx.orchestrate

This script publishes the GitHub Issues Analyzer agent to watsonx.orchestrate.
"""

import os
import logging
import sys
import subprocess
import yaml

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Constants
AGENT_DEFINITION_FILE = "github_issues_agent_definition.yaml"
AGENT_NAME = "GitHub Issues Analyzer"

def register_tools():
    """Register the MCP tools with watsonx.orchestrate."""
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

def validate_agent_definition():
    """Validate the agent definition file."""
    try:
        if not os.path.exists(AGENT_DEFINITION_FILE):
            log.error(f"Agent definition file not found: {AGENT_DEFINITION_FILE}")
            return False
        
        with open(AGENT_DEFINITION_FILE, 'r') as f:
            agent_def = yaml.safe_load(f)
        
        required_fields = ['name', 'description', 'tools', 'instructions', 'model']
        for field in required_fields:
            if field not in agent_def:
                log.error(f"Missing required field in agent definition: {field}")
                return False
        
        log.info("Agent definition is valid")
        return True
    except Exception as e:
        log.error(f"Error validating agent definition: {str(e)}")
        return False

def publish_agent():
    """Publish the agent to watsonx.orchestrate."""
    try:
        # Check if orchestrate CLI is available
        try:
            subprocess.run(['orchestrate', '--version'], check=True, capture_output=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            log.error("orchestrate CLI not found. Make sure it's installed and in your PATH")
            return False
        
        # Publish the agent
        log.info(f"Publishing agent: {AGENT_NAME}")
        result = subprocess.run(
            ['orchestrate', 'agent', 'create', '--file', AGENT_DEFINITION_FILE],
            check=True,
            capture_output=True,
            text=True
        )
        
        log.info(f"Agent published successfully: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Error publishing agent: {e.stderr.strip() if e.stderr else str(e)}")
        return False
    except Exception as e:
        log.error(f"Error publishing agent: {str(e)}")
        return False

def main():
    """Main function to publish the agent."""
    log.info("Starting GitHub Issues Analyzer agent publication process")
    
    # Step 1: Validate agent definition
    if not validate_agent_definition():
        return False
    
    # Step 2: Register tools
    if not register_tools():
        return False
    
    # Step 3: Publish agent
    if not publish_agent():
        return False
    
    log.info(f"Successfully published {AGENT_NAME} agent to watsonx.orchestrate")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

# Made with Bob
