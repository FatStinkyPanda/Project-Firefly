# MCP Global Rules - AI Agent Instructions

## Available Commands (48 total)

Run with: `${PYTHON3_CMD} mcp-global-rules/mcp.py <command>`

### Before Coding
```bash
mcp autocontext              # Load relevant context
mcp recall "topic"           # Search memory
mcp search "query"           # Semantic code search
```

### While Coding
```bash
mcp predict-bugs file.py     # Check for bugs
mcp impact file.py           # What breaks?
mcp context "query"          # Get context
```

### After Coding
```bash
mcp review file.py           # Code review
mcp security file.py         # Security check
mcp test-gen file.py --impl  # Generate tests
```

### Remember & Learn
```bash
mcp remember "key" "value"   # Store knowledge
mcp recall "query"           # Search knowledge
mcp learn --patterns         # View learned patterns
```

## Hooks (Automatic)

All hooks are installed and will run automatically:
- **pre-commit**: Auto-fix, risk check, security scan, review
- **post-commit**: Learning, index update
- **post-checkout**: Warm indexes

## Key Directories

- `mcp-global-rules/` - MCP package
- `.mcp/` - Index data (auto-generated)

## Quick Reference

| Need | Command |
|------|---------|
| Context | `mcp autocontext` |
| Search | `mcp search "query"` |
| Review | `mcp review .` |
| Bugs | `mcp predict-bugs .` |
| Tests | `mcp test-gen file.py` |
| Memory | `mcp remember/recall` |
