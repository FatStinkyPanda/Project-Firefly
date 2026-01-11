# MCP AI Agent Instructions - ENFORCED WORKFLOWS

## Overview

This document defines **mandatory workflows** for AI agents working with MCP-enabled projects. These workflows are automatically enforced via git hooks.

## Continuous Development Mode (Orchestration)
For "Always-On" development task:
1. **Take Ownership**: You are the Orchestrator. Manage the lifecycle.
2. **Check Triggers**: Review "Agent Manager" for external events/bug reports.
3. **Cycle Models**: Use the most appropriate model (Gemini/Claude/Local) for the sub-task.
4. **Enforce Quality**: Do not mark "Done" until `mcp review`, `mcp security`, and `mcp test` pass 100%.

## Required Tool Usage

AI agents MUST use these tools when working on code:

### Before Making Changes
```bash
python mcp.py context "what I'm working on"   # Get relevant context
python mcp.py find "component name"           # Find related files
python mcp.py deps src/                       # Understand dependencies
```

### During Development
```bash
python mcp.py docs src/ --write               # Add docstrings as you go
python mcp.py fix src/                        # Auto-fix issues
python mcp.py review src/                     # Check quality continuously
```

### Before Committing
```bash
python mcp.py review src/ --strict            # Full review
python mcp.py security src/                   # Security audit
python mcp.py deadcode src/                   # Find unused code
python mcp.py coverage src/                   # Check doc coverage
```

### Before Pushing
```bash
python mcp.py architecture src/               # Validate structure
python mcp.py profile src/                    # Check complexity
python mcp.py summarize --output SUMMARY.md   # Update context
```

## Automatic Enforcement

These hooks run automatically:

| Hook | Tools Run | Blocking |
|------|-----------|----------|
| pre-commit | review, security, coverage, errors, profile | Yes (on errors) |
| pre-push | security, architecture, coverage, deps | Yes (strict) |
| commit-msg | Context enrichment | No |

## Quality Gates

Commits are BLOCKED if:
- Security scan finds CRITICAL issues
- Code review finds errors
- Doc coverage < 50% (pre-push)
- Architecture violations exist

## MCP Memory

Always record actions:
```bash
mcp record action "Implemented feature X"
mcp record decision "Chose approach Y because Z"
mcp record todo "Need to refactor W later"
```

## Workflow Example

```bash
# 1. Start by understanding context
python mcp.py context "authentication"
python mcp.py find "login handler"

# 2. Make changes, checking frequently
python mcp.py review src/ --staged
python mcp.py security src/

# 3. Document and fix
python mcp.py docs src/ --write
python mcp.py fix src/

# 4. Record and commit
mcp record action "Added OAuth support"
git add -A
git commit -m "feat: add OAuth authentication"

# 5. Pre-push quality check
python mcp.py architecture src/
python mcp.py summarize
git push
```

## Tool Quick Reference

| Need | Command |
|------|---------|
| Find related code | `python mcp.py find "query"` |
| Get context | `python mcp.py context "task"` |
| Check quality | `python mcp.py review src/` |
| Audit security | `python mcp.py security src/` |
| Add docs | `python mcp.py docs src/ --write` |
| Auto-fix | `python mcp.py fix src/` |
| Check complexity | `python mcp.py profile src/` |
| Check architecture | `python mcp.py architecture src/` |
| Check doc coverage | `python mcp.py coverage src/` |
| Analyze errors | `python mcp.py errors src/` |
| Check migration | `python mcp.py migrate src/` |
| Gen API docs | `python mcp.py apidocs src/` |
| Find unused | `python mcp.py deadcode src/` |
| Analyze deps | `python mcp.py deps src/` |
| Gen summary | `python mcp.py summarize src/` |
| Suggest refactor | `python mcp.py refactor src/` |
| Gen tests | `python mcp.py test src/` |
| Gen changelog | `python mcp.py changelog` |
