# AI AUTONOMOUS DEVELOPMENT SCRIPT (STRICT ENFORCEMENT)

**TO ANY AI AGENT READING THIS:**
You are now the Lead Developer/Orchestrator for **Project-Firefly**. Your goal is to continue development autonomously until all requirements in `README.md` are fully implemented, tested, and production-ready.

---

## STRICT PHILOSOPHY (DO NOT IGNORE)
**Adhere to this absolutely:**
"Fix properly, never disable, never restrict or reduce capabilities of this program, ALWAYS FIX CORRECTLY AND FULLY AND COMPLETELY TO MAKE EVERYTHING WORK FULLY! All integrations, improvements, and adaptations must utilize what already exists and add on to it, never bypassing anything that we have intentionally developed and integrated."

**Focus:** Real development. Code. Tests. Functionality. 
**Avoid:** Writing summary markdown files that nobody reads.

---

## YOUR MANDATORY WORKFLOW (REPEAT UNTIL DONE)

### 1. INITIALIZATION (Start Here)
If you are a new agent or starting a fresh session, you **MUST** orient yourself immediately:
1.  **Load Context:** Run `python mcp-global/mcp-global-rules/mcp.py autocontext`
2.  **Read Truth:** Read `README.md` (The Single Source of Truth).
3.  **Check Status:** Read `task.md` to see what is next.

### 2. DEVELOPMENT LOOP
Pick the next incomplete task from `README.md` / `task.md` and execute:

1.  **Pre-Work check:**
    *   `python mcp-global/mcp-global-rules/mcp.py search "relevant_code"`
    *   `python mcp-global/mcp-global-rules/mcp.py impact <target_file>`
2.  **Implement:** Write the code.
3.  **Verify (MANDATORY):**
    *   `python mcp-global/mcp-global-rules/mcp.py fix <file>` (Auto-fix lints)
    *   `python mcp-global/mcp-global-rules/mcp.py security <file>` (Security audit)
    *   `python mcp-global/mcp-global-rules/mcp.py review <file>` (Quality review)
4.  **Test:** Ensure tests pass. 100% success required.

### 3. COMMIT & PUSH (The Definition of Done)
Once a feature is working and fully verified:
1.  **Stage:** `git add .`
2.  **Commit:** `git commit -m "feat: <description of change>"`
    *   *Note: This will trigger strict pre-commit hooks. If they fail, FIX THE CODE. Do not bypass.*
3.  **Push:** `git push`
    *   *Note: This will trigger strict pre-push hooks. If they fail, FIX THE SECURITY ISSUES.*

### 4. REPEAT
Do not stop. Go back to Step 2. Pick the next task. update the roadmap/task list. Continue until Project-Firefly is complete.