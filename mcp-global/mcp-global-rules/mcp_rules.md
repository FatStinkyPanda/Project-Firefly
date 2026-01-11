# MCP Global Rules

> Auto-copy this to `.agent/` or your AI agent's rules directory

## IMPORTANT: Python Command

Use `python3` on Linux/Mac or `python` on Windows:
```bash
python3 mcp-global-rules/mcp.py <command>
```

## CORE PRINCIPLES

### Fix Properly, Never Disable

Fix properly, never disable, never restrict or reduce capabilities of this program. ALWAYS FIX CORRECTLY AND FULLY AND COMPLETELY TO MAKE EVERYTHING WORK FULLY! All integrations, improvements, and adaptations must utilize what already exists and add on to it, never bypassing anything that we have intentionally developed and integrated.

### Autonomous Teamwork

Collaborate with peer agents autonomously via `mcp comms`.
- Prefer Gemini 3 Flash.
- Use `mcp comms collaborate` for back-and-forth development without human intervention.
- Verify presence via `mcp comms status`.

### No Emojis in Code

Do NOT use emojis or icons in any code unless explicitly requested by the user or defined in README.md.

---

## TRIGGER COMMANDS

### "dev" - Autonomous Development

When user says only **"dev"**:
1. Load context: `python3 mcp-global-rules/mcp.py autocontext`
2. Read README.md (single source of truth)
3. Identify tasks: `python3 mcp-global-rules/mcp.py todos`
4. Find gaps in implementation
5. Continue development AUTONOMOUSLY - no human intervention

### "go" - Context and Suggestions

When user says only **"go"**:
1. Load context: `python3 mcp-global-rules/mcp.py autocontext`
2. Read README.md (single source of truth)
3. Identify tasks: `python3 mcp-global-rules/mcp.py todos`
4. **STOP - DO NOT make changes**
5. Present suggestions and wait for user direction

---

## Required Behavior

1. **Before ANY coding task**, run:
   ```bash
   python3 mcp-global-rules/mcp.py autocontext
   ```

2. **Before modifying a file**, check impact:
   ```bash
   python3 mcp-global-rules/mcp.py impact <file>
   python3 mcp-global-rules/mcp.py predict-bugs <file>
   ```

3. **After making changes**, verify:
   ```bash
   python3 mcp-global-rules/mcp.py review <file>
   python3 mcp-global-rules/mcp.py security <file>
   ```

4. **Remember important decisions**:
   ```bash
   python3 mcp-global-rules/mcp.py remember "<key>" "<value>"
   ```

5. **Recall prior knowledge**:
   ```bash
   python3 mcp-global-rules/mcp.py recall "<query>"
   ```

---

## Enforced via Git Hooks

These checks run automatically and WILL BLOCK commits that:
- Have HIGH bug risk
- Have CRITICAL security issues
- Fail code review with >5 errors

## Do NOT

- Skip the autocontext step
- Ignore predict-bugs warnings
- Bypass pre-commit hooks (--no-verify)
- Forget to use remember/recall
- Use emojis in code
- Disable or bypass existing functionality
