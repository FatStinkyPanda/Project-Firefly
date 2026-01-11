# MCP Global Rules for AI Agents

> Add this file to your AI agent's rules/instructions to enable MCP integration.

---

## IMPORTANT: How to Run MCP Commands

Find the mcp.py file in the project and run with python3:

```bash
# First, find where mcp-global-rules is installed
find . -name "mcp.py" -path "*/mcp-global-rules/*" 2>/dev/null

# Then run commands using the full path, for example:
python3 ./mcp-global-rules/mcp.py <command>

# Or if installed elsewhere:
python3 /path/to/mcp-global-rules/mcp.py <command>
```

The mcp.py script will auto-detect its location and work correctly.

---

## PLATFORM SPECIFICS (Project-Firefly)

### Windows Compatibility
- **Hooks**: This project uses Python-based git hooks for cross-platform stability. Do not replace them with shell scripts.
- **Paths**: Using `core.longpaths` is required. Always use relative paths or dynamic root detection in scripts.

### Agent-Triggered Event System
Firefly agents are Event-Driven. You must:
1. **Monitor "Agent Manager"**: Check for incoming triggers from Webhooks, Telegram, or SMS.
2. **Handle Remote Events**: Process instructions from `mcp comms` or external signals immediately.

### Universal Model Intelligence
You have access to **ALL** model providers.
- **Priority Cycling**: Start with efficient models (Gemini Flash). If complex reasoning is needed or limits hit, AUTOMATICALLY cycle to stronger models (Claude Opus, GPT-4) or fallback to Local LLMs.
- **Zero Downtime**: Never stop for rate limits. Switch provider and continue.

### Continuous Development (Orchestrators)
- **Always-On**: Supervisor agents run 24/7.
- **Definition of Done**: 100% Tests Passed, Security Scan Clean (0 Critical), Production Ready.
- **Autonomous**: Do not wait for user input unless blocked. Propose -> Implement -> Verify -> Deploy.

---

## CORE PRINCIPLES

### Fix Properly, Never Disable

Fix properly, never disable, never restrict or reduce capabilities of this program. ALWAYS FIX CORRECTLY AND FULLY AND COMPLETELY TO MAKE EVERYTHING WORK FULLY! All integrations, improvements, and adaptations must utilize what already exists and add on to it, never bypassing anything that we have intentionally developed and integrated. Unless explicitly requested by the user for a specific change that goes against this, you must always obey these rules.

### Autonomous Collaboration (Team Mode)

You are part of a multi-agent team across devices (Quasar and WizardPanda). You MUST coordinate autonomously.
1. Use `mcp comms status` to check peer presence.
2. Use `mcp comms collaborate` to enter the autonomous execution loop.
3. Delegate tasks via `mcp comms send <peer> task "..."` and wait for results.
4. Aim for **ZERO human intervention**. Collaborate back and forth until the task is complete.

### Model Priority Enforcement

You MUST prioritize models as follows:
1. **Gemini 3 Flash** (Primary/Default)
2. **Claude Opus** (Secondary/Thinking)

Use `mcp model status` to verify current settings. Switches MUST occur automatically when limits are reached or models become available.

### No Emojis or Icons in Code

Do NOT use emojis or icons in any code unless explicitly requested by the user or defined in the README.md file. Emojis and icons cause code errors and are not always the same between devices.

---

## TRIGGER COMMANDS

### "dev" - Autonomous Development Mode

When the user says only **"dev"**, you MUST:

1. **Find and Run MCP Tools**
   ```bash
   # Find mcp.py location
   MCP=$(find . -name "mcp.py" -path "*/mcp-global-rules/*" 2>/dev/null | head -1)
   
   # Load context
   python3 $MCP autocontext
   python3 $MCP recall "project"
   ```

2. **Read README.md as Single Source of Truth**
   - README.md defines what the project should do
   - README.md contains the development roadmap
   - All decisions must align with README.md

3. **Identify Development Tasks**
   ```bash
   python3 $MCP todos
   python3 $MCP recall "tasks"
   ```

4. **Identify Gaps**
   - Compare README.md goals vs current implementation
   - Check for missing features
   - Check for incomplete integrations

5. **Continue Development Autonomously**
   - Implement next priority task from README.md
   - NO human intervention required
   - Follow "fix properly" principle
   - Commit progress incrementally

### "go" - Context and Suggestions Mode

When the user says only **"go"**, you MUST:

1. **Find and Run MCP Tools** (same as "dev")
   ```bash
   MCP=$(find . -name "mcp.py" -path "*/mcp-global-rules/*" 2>/dev/null | head -1)
   python3 $MCP autocontext
   python3 $MCP recall "project"
   ```

2. **Read README.md as Single Source of Truth**

3. **Identify Development Tasks and Gaps**
   ```bash
   python3 $MCP todos
   ```

4. **STOP - Do NOT Make Changes**
   - Present findings to user
   - List suggested next steps
   - Wait for user direction on which task to proceed with

5. **Provide Suggestions**
   - What needs to be done
   - Priority order
   - Estimated complexity
   - Ask user which to proceed with

---

## MANDATORY: Use MCP Tools

Before any coding task, you MUST:

1. **Find MCP location**
   ```bash
   MCP=$(find . -name "mcp.py" -path "*/mcp-global-rules/*" 2>/dev/null | head -1)
   ```

2. **Load context**
   ```bash
   python3 $MCP autocontext
   ```

3. **Search for relevant code**
   ```bash
   python3 $MCP search "your query"
   ```

4. **Check what you know**
   ```bash
   python3 $MCP recall "topic"
   ```

## Before Making Changes

```bash
# What will break?
python3 $MCP impact file.py

# Predict bugs
python3 $MCP predict-bugs file.py
```

## After Making Changes

```bash
# Code review
python3 $MCP review file.py

# Security check  
python3 $MCP security file.py

# Generate tests
python3 $MCP test-gen file.py --impl
```

## Remember Important Information

```bash
# Store knowledge for later
python3 $MCP remember "key" "value"

# Example: remember file locations
python3 $MCP remember "auth_handler" "src/auth/handler.py"
```

## Recall Knowledge

```bash
# Search memories
python3 $MCP recall "authentication"
```

---

## Available Commands (48)

| Category | Commands |
|----------|----------|
| Context | `autocontext`, `context`, `search`, `find` |
| Memory | `remember`, `recall`, `forget`, `learn` |
| Analysis | `review`, `security`, `profile`, `errors` |
| Prediction | `predict-bugs`, `risk-score`, `impact` |
| Testing | `test-gen`, `test`, `test-coverage` |
| Indexing | `index-all`, `todos`, `git-history` |

---

## Git Hooks (Automatic)

These run automatically on git operations:
- **pre-commit**: Blocks high-risk/insecure code
- **post-commit**: Updates learning and indexes
- **post-checkout**: Warms context for new branch

---

---

## Cybersecurity Capability Map (WizardPanda)

WizardPanda is equipped with over 70 tools. Use `mcp cybersec list` to explore. Core categories:

| Category | Typical Tools | AI Usage Pattern |
|----------|---------------|------------------|
| **Network** | Nmap, Masscan, Bettercap | Discovery & Scanning |
| **Web** | Burp Suite, Nikto, Wget | Vulnerability Assessment |
| **Exploitation** | Metasploit, Searchsploit | Execution & Payload Delivery |
| **Post-Exploit** | Impacket, Mimikatz | Lateral Movement & Persistence |
| **Password** | John, Hashcat, Hydra | Brute Force & Cracking |
| **Wireless** | Aircrack-ng, Kismet | RF & Wi-Fi Analysis |
| **Forensics** | Autopsy, Volatility | Analysis & Evidence Gathering |
| **Reverse** | Radare2, GDB, Ghidra | Binaries & Malware Analysis |

### Enforcement & Safety
- **Impacket**: Always run via `mcp cybersec <tool>` to ensure the correct VENV is used.
- **Root**: Tools requiring `sudo` are pre-authorized for the `p4nd4pr0t0c01` user.
- **Reporting**: Always pipe large outputs to `outputs/` within the NSync directory for sync.

---

## Multi-Agent Coordination & Safety

When working on a project across devices, you MUST follow these safety checks:

1. **Presence Check**: `mcp comms status` - Ensure you are not overwriting a peer's active work.
2. **Conflict Avoidance**: If a peer is "active" on a project, send a "task" message via `mcp comms send` to coordinate before making changes.
3. **Handshake**: Use `mcp comms ping wizardpanda` to verify remote availability before triggering long-running remote scans.
4. **Heartbeat Maintenance**: Update your task status (`mcp comms heartbeat`) at the start and end of major operations.

---

## NSync: The Master Workflow

Any development intended for remote execution on `wizardpanda` MUST follow this workflow:

1. **Initialize Project** (if new):
   ```bash
   # From the mcp-global-rules directory:
   python3 mcp.py nsync init-project <project_name>
   ```
   This creates a folder in `NSync/` and links `mcp-global-rules` so the agent always has its tools.

2. **Develop Locally**:
   - Write all code inside `C:\Users\dbiss\Desktop\Projects\_BLANK_\NSync\<project_name>\`.
   - Use standard MCP tools (security, review, etc.) locally before syncing.

3. **Automatic Synchronization**:
   - Changes are broadcast in real-time. Ensure `mcp nsync watch` is running on your host.
   - Files appear on `wizardpanda` at `/home/p4nd4pr0t0c01/Projects/NSync/<project_name>/`.

4. **Remote Execution & Validation**:
   ```bash
   # Sync and run the script on wizardpanda hardware
   python3 mcp.py nsync run <project_name>/main.py
   ```

5. **Cybersecurity Integration**:
   - **Discovery**: Use `mcp cybersec list` to find tools and `mcp cybersec help <tool>` to learn about flags.
   - **Execution**: If a script needs the pen-testing suite, run it via `mcp nsync run`.
   - Within the remote script, you can invoke tools via standard shell calls as they are pre-configured in the `wizardpanda` environment.

---

## Remote Access: WizardPanda

- **Host**: `wizardpanda` (Tailscale IP: `100.121.26.87`)
- **User**: `p4nd4pr0t0c01`
- **Environment**: Raspberry Pi 5 (Debian 12), Python 3.11.
- **Tools**: Full suite located in `~/cybersec` and categorized in `mcp cybersec`.

---

## Agent Collaboration Layer (ACL)

Agents on different devices (Quasar and WizardPanda) work together via `mcp comms`.

### 1. Verification of Presence
Before delegating a task to a peer agent, you MUST verify they are "listening":
```bash
# Check if the peer agent is alive and see what they are doing
python3 mcp.py comms status
```

### 2. Communicating with Peer Agents
Send instructions or status updates to your peer:
```bash
# Send a message to the peer
python3 mcp.py comms send wizardpanda "task" "I am starting the vulnerability scan, monitor logs."
```

### 3. Listening for Instructions
Periodically check for messages from your peer:
```bash
# Poll for new messages
python3 mcp.py comms listen
```

### 4. Heartbeat Maintenance
Keep your status updated so your peer knows you are still working:
```bash
# Update heartbeat
python3 mcp.py comms heartbeat "active" "running nmap scan"
```

---

## Autonomous Team Protocols

To collaborate autonomously across devices:
1. **Initiate Loop**: One agent should run `mcp comms collaborate` to process remote tasks.
2. **Task Delegation**: Send structured tasks via `mcp comms send`.
3. **Status Monitoring**: Use `mcp comms status` to ensure the team is in sync.
4. **Model Switching**: Always prefer Gemini 3 Flash. If usage limits are hit, switch to Claude Opus via `mcp model switch`.

---

## Summary

| Trigger | Behavior |
|---------|----------|
| `dev` | Autonomous development, no intervention needed |
| `go` | Context + suggestions, wait for user direction |

**README.md is the single source of truth for project development.**

**ALWAYS use MCP tools. They provide context, prevent bugs, and learn from your work.**
