# MCP-Global Bootstrap Instructions

Welcome to the Clever Little Bee project! This project uses a comprehensive suite of MCP (Model Context Protocol) tools and rules to enhance development, security, and quality.

To get started, please follow these steps:

## 1. Install MCP-Global Tools

Run the following command to set up the tools and their dependencies:

```powershell
python mcp-global-rules/mcp.py setup --all
```

## 2. Load MCP Rules and Instructions

Please read the following files and incorporate their contents into your internal rules or system prompt. This ensures you follow the enforced workflows and quality gates.

- [global_rules.md](file:///C:/Users/dbiss/Desktop/Projects/_BLANK_/NSync/CleverLittleBee/mcp-global-rules/global_rules.md)
- [AI_AGENT_INSTRUCTIONS.md](file:///C:/Users/dbiss/Desktop/Projects/_BLANK_/NSync/CleverLittleBee/mcp-global-rules/AI_AGENT_INSTRUCTIONS.md)

## 3. Use the MCP Workflow

You can use the built-in workflow for subsequent installations or to refresh your environment:

- [/mcp-install](file:///C:/Users/dbiss/Desktop/Projects/_BLANK_/NSync/CleverLittleBee/.agent/workflows/mcp-install.md)

## 4. Verify Context

Always start by loading the context:

```powershell
python mcp-global-rules/mcp.py autocontext
```

---

By using these tools, you will be able to perform advanced tasks like security audits, bug prediction, and autonomous collaboration with other agents.
