# MCP AI Agent: Permanent Development Workflow Memory

> **ENFORCED WORKFLOWS - READ AND ADHERE STRICTOR THAN CODE**
> This document defines the MANDATORY operating procedures for all AI agents working on the CleverLittleBee project. It integrates context from MCP-Global, core principles, and autonomous bug-fixing protocols.

---

## 1. Core Principles (Non-Negotiable)

- **Fix Properly, Never Disable**: Fix properly, never disable, never restrict or reduce capabilities of this program. ALWAYS FIX CORRECTLY AND FULLY AND COMPLETELY TO MAKE EVERYTHING WORK FULLY! All integrations, improvements, and adaptations must utilize what already exists and add on to it, never bypassing anything that we have intentionally developed and integrated.
- **README.md as Single Source of Truth**: README.md defines what the project should do and contains the development roadmap. All decisions must align with README.md.
- **Model Priority Enforcement**:
    1. **Gemini 3 Flash** (Primary/Default)
    2. **Claude Opus** (Secondary/Thinking)
    *Use `mcp model status` to verify current settings. Switches MUST occur automatically when limits are reached or models become available.*
- **No Emojis or Icons in Code**: Strictly prohibited unless explicitly requested by the user or defined in the README.md file. Emojis and icons cause code errors and are not always the same between devices.

---

## 2. Mandatory Setup & Command Execution

The `mcp.py` script is the gateway to the entire system. 
- **Finding MCP**: `find . -name "mcp.py" -path "*/mcp-global-rules/*"`
- **Execution**: Run commands using the full path, e.g., `python3 ./mcp-global-rules/mcp.py <command>`.
- **Auto-Detection**: The script auto-detects its location and works correctly when called with its relative or absolute path.

---

## 3. Mandatory Tool Usage (Enforced Workflow)

AI agents MUST use these tools at each stage of development. 

### Before Making Changes
| Command | Purpose |
|---------|---------|
| `python mcp.py context "task"` | Get relevant context for what you are working on |
| `python mcp.py find "name"` | Find related files/components |
| `python mcp.py search "query"` | Search for relevant code patterns |
| `python mcp.py deps src/` | Understand project dependencies |
| `python mcp.py recall "topic"` | Check previous project knowledge |
| `python mcp.py impact file.py` | Determine what your changes might break |
| `python mcp.py predict-bugs file.py` | Use AI to predict potential bugs in changes |

### During Development
| Command | Purpose |
|---------|---------|
| `python mcp.py docs src/ --write` | Add docstrings and comments as you go |
| `python mcp.py fix src/` | Auto-fix syntax, lint, and formatting issues |
| `python mcp.py review src/` | Check quality continuously during implementation |

### Before Committing (Local Gate)
Commits are BLOCKED by hooks if CRITICAL issues are found.
| Command | Purpose |
|---------|---------|
| `python mcp.py review src/ --strict` | Full strict quality review |
| `python mcp.py security src/` | Security audit (Zero tolerance for hardcoded secrets) |
| `python mcp.py deadcode src/` | Identify and remove unused code |
| `python mcp.py coverage src/` | Check doc coverage (Success if > 50%) |
| `python mcp.py errors src/` | Analyze common error patterns |
| `python mcp.py profile src/` | Check code complexity |

### Before Pushing (Final Gate)
| Command | Purpose |
|---------|---------|
| `python mcp.py architecture src/` | Validate project structure against rules |
| `python mcp.py summarize --output SUMMARY.md` | Update the master context summary |
| `python mcp.py test src/` | Run existing tests to ensure no regressions |

---

## 4. Trigger Commands ("dev" and "go")

### "dev" - Autonomous Development Mode
When the user says only **"dev"**, you MUST:
1. **Find $MCP**: Locate the script autonomously.
2. **Load Context**: `python3 $MCP autocontext` and `python3 $MCP recall "project"`.
3. **Read Truth**: Parse README.md for requirements and roadmap goals.
4. **Identify Work**: `python3 $MCP todos` and `python3 $MCP recall "tasks"`.
5. **Implement**: Implement next priority task from README.md. **NO human intervention required.**
6. **Cycle**: Commit progress incrementally, following "fix properly" principle.

### "go" - Context and Suggestions Mode
When the user says only **"go"**, you MUST:
1. **Load Context**: Same as `dev`.
2. **Read Truth**: Read README.md.
3. **Analyze**: Identify tasks and gaps (`python3 $MCP todos`).
4. **STOP**: Present findings and suggested next steps (Priority, Complexity).
5. **Wait**: Do NOT make changes until the user gives explicit direction.

---

## 5. Bug Fix Protocol (Autonomous Loop)

Follow this workflow to identify, fix, and document bugs from the `bug_reports` table.

1.  **Identify Unresolved Bugs**: 
    ```bash
    sudo -u postgres psql -d cleverlittlebee_db -P pager=off -x -c "SELECT id, description, file_path, status, created_at FROM bug_reports WHERE status = 'NOT_RESOLVED' ORDER BY created_at ASC;"
    ```
2.  **Analyze**: Read ID, Description, and check `file_path` (e.g., in `/sandbox_uploads/`).
3.  **Fix**: Reproduce using `grep_search/find_by_name`, create a mini-plan, Implement using `replace_file_content`.
4.  **Verify**: 
    - Frontend: `npm run build`
    - Backend: `sudo systemctl restart cleverlittlebee-api`
5.  **Document & Close**: Update status to `SOLVED` and include `fix_notes`.
    ```bash
    sudo -u postgres psql -d cleverlittlebee_db -c "UPDATE bug_reports SET status = 'SOLVED', fix_notes = 'DETAILED_DESCRIPTION' WHERE id = 'BUG_ID';"
    ```

---

## 6. MCP Memory Recording

Always record important findings and actions to maintain the project's persistent state:
- `python mcp.py remember "auth_handler" "src/auth.py"`
- `mcp record action "Implemented Feature X"`
- `mcp record decision "Chose approach Y because Z"`
- `mcp record todo "Refactor component W"`

---

## 7. Tool Reference (48 Commands)

| Category | Commands |
|----------|----------|
| **Context** | `autocontext`, `context`, `search`, `find` |
| **Memory** | `remember`, `recall`, `forget`, `learn` |
| **Analysis** | `review`, `security`, `profile`, `errors`, `deadcode`, `deps`, `summarize`, `refactor` |
| **Prediction** | `predict-bugs`, `risk-score`, `impact` |
| **Testing** | `test-gen`, `test`, `test-coverage`, `apidocs` |
| **Management** | `index-all`, `todos`, `git-history`, `migrate`, `changelog` |

---

## 8. Development Environment & Dependencies

### Core Python Tools (18 scripts)
- **Runtime**: Python 3.11+ standard library ONLY.
- **Stdlib Modules**: `ast`, `sys`, `os`, `re`, `pathlib`, `typing`, `dataclasses`, `collections`, `json`, `subprocess`, `datetime`, `enum`, `hashlib`, `math`.

### Bundled Vendor Packages (90 wheels in `vendor/python-packages-py311/`)
| Purpose | Key Packages |
|---------|--------------|
| **Quality** | `pylint-4.0.4`, `flake8-7.3.0`, `black-25.12.0`, `isort-7.0.0`, `mypy-1.19.1` |
| **Security** | `bandit-1.9.2`, `safety-3.7.0`, `pip_audit-2.10.0` |
| **Testing** | `pytest-9.0.2`, `pytest_cov-7.0.0`, `coverage-7.13.1` |
| **Analysis** | `radon-6.0.1`, `astroid-4.0.2` |
| **Utilities**| `pre_commit-4.5.1`, `rich-14.2.0`, `pydantic-2.12.5`, `requests-2.32.5`, `cryptography-46.0.3` |

### Installation (Completely Offline)
```bash
# Core Tools: No installation needed (Stdlib only)
# Vendor Tools: pip install --no-index --find-links=vendor/python-packages-py311 <package>
# Or use: .\install.ps1 (Windows) / ./install.sh (Linux)
```

---
**System Status**: ENFORCED
