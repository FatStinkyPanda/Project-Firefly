# 🚀 MCP-Global Bootstrap Instructions

This document allows any AI agent to install the complete MCP-Global system into a project.

## Prerequisites
- The `mcp-global` directory (containing this file) must be present in the project root.
- **Python 3.8+** installed and in PATH.
- **Git** installed (required for hooks).

## Installation

### Windows (PowerShell)
Run the automated installer. This will copy the rules to your project root, install git hooks, and build the initial index.

```powershell
# Run the installer script
powershell -ExecutionPolicy Bypass -File mcp-global/mcp-global-rules/install.ps1
```

### Linux / Mac
```bash
chmod +x mcp-global/mcp-global-rules/install.sh
./mcp-global/mcp-global-rules/install.sh
```

## Post-Install Verification
1.  **Context Check**: Run `python mcp-global-rules/mcp.py autocontext`.
2.  **Hooks**: Check that `.git/hooks/pre-commit` exists.
3.  **Docs**: Read `AI_AGENT_MCP.md` (generated in root) for available commands.

## System Integrity
The `mcp-global` folder contains the "Golden Copy" of the system.
- **Do not modify** files inside `mcp-global/` directly.
- The installer copies them to `mcp-global-rules/` in your project root.
- If you need to update the system, update `mcp-global/` and re-run the installer.
