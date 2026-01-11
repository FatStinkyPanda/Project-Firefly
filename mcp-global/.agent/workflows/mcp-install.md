---
description: Read "mcp_bootstrap.md" and install mcp-global for this project
---



# MCP-Global Installation Workflow

This workflow guides you through the process of installing and configuring the MCP-global tools and rules for this project.

## Step 1: Initialize MCP Environment

Run the following command to initialize the MCP environment and install dependencies.

// turbo
```powershell
python mcp-global-rules/mcp.py setup --all
```

## Step 2: Configure AI Agent Rules

Copy the contents of the following files to your AI agent's configuration (System Prompt or Rules):

1. `mcp-global-rules/global_rules.md` - Primary rules for MCP tool usage.
2. `mcp-global-rules/AI_AGENT_INSTRUCTIONS.md` - Detailed instructions for the agent.

## Step 3: Register Workflows

Ensure that you have access to the workflows in `.agent/workflows`.

## Step 4: Verify Installation

Run the autocontext tool to verify that everything is working correctly.

// turbo
```powershell
python mcp-global-rules/mcp.py autocontext
```

## Completion

Once verified, you are ready to use the full scale and scope of the MCP-global and MCP server tools.