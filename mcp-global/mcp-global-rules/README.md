# MCP Global Rules

> **AI Agent Enhancement Package** - 42 Scripts | 48 Commands | 6 Hooks

## One-Command Install

**Windows (PowerShell):**

```powershell
.\mcp-global-rules\install.ps1
```

**Linux/Mac:**

```bash
./mcp-global-rules/install.sh
```

This installs:

- All 42 Python scripts
- All 6 git hooks (enforced)
- AI agent instructions
- Initial indexes

## Quick Start

```bash
# Get help
python mcp-global-rules/mcp.py help

# Load AI context
python mcp-global-rules/mcp.py autocontext

# Search code semantically
python mcp-global-rules/mcp.py search "authentication"

# Predict bugs
python mcp-global-rules/mcp.py predict-bugs src/
```

## For AI Agents

Add `global_rules.md` to your AI agent's rules/instructions system.

## What's Included

| Category       | Commands                                                  |
| -------------- | --------------------------------------------------------- |
| **Context**    | `autocontext`, `search`, `context`, `find`                |
| **Memory**     | `remember`, `recall`, `forget`, `learn`                   |
| **Analysis**   | `review`, `security`, `profile`, `errors`, `architecture` |
| **Prediction** | `predict-bugs`, `risk-score`, `impact`, `test-gen`        |
| **Indexing**   | `index-all`, `todos`, `git-history`, `doc-index`          |
| **CI/CD**      | `github-action`, `pipeline`                               |
| **Setup**      | `setup --all`, `warm`                                     |

## Hooks (Auto-Enforced)

| Hook          | Actions                                |
| ------------- | -------------------------------------- |
| pre-commit    | Risk block, auto-fix, security, review |
| post-commit   | Learning, index update                 |
| post-checkout | Warm indexes                           |

## Requirements

- Python 3.8+
- Git (for hooks)

## License

MIT
