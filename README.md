# Project-Firefly (Firefly) 🦉🔥

> **The AI-Native Integrated Development Environment.**  
> *Forked from VS Code. Powered by MCP-Global. Driven by Autonomous Intelligence.*

## 📖 Overview

**Project-Firefly** (or simply **Firefly**) is a next-generation fork of [Visual Studio Code](https://github.com/microsoft/vscode), designed to be the ultimate environment for AI-assisted and autonomous software development. 

While inspired by advanced platforms like Google's "Antigravity", Firefly distinguishes itself through **enforced automation**, **universal AI compatibility**, and a radically new **Event-Driven Agent Trigger System**. It is built not just to help developers write code, but to actively manage, monitor, and complete entire software lifecycles through continuous autonomous operation.

---

## 🚀 Core Pillars

### 1. 🛡️ Strict MCP-Global Integration
Firefly comes pre-integrated with the **`mcp-global`** toolset, providing a rigid yet powerful framework for quality and security.
- **Enforced Workflows:** Development is governed by mandatory git hooks (pre-commit, pre-push) that run security scans, code reviews, and architectural checks.
- **Automated Context & Memory:** The IDE automatically maintains context maps and project memory, ensuring AI agents always know the "what", "why", and "how" of the codebase.
- **"Fix Properly" Philosophy:** The system adheres to a strict "fix properly, never disable" rule, ensuring technical debt is addressed, not bypassed.

### 2. ⚡ Event-Driven Agent Trigger System
Firefly transforms the IDE from a passive editor into an active event processor. Developers can configure **Agent Triggers** that react to events inside and outside the IDE.
- **"Agent Manager" Hub:** A central conversation interface where developers configure and monitor all automated triggers.
- **Universal Inputs:** Agents can be triggered by:
    - **Webhooks:** (e.g., A bug report submission on your company website auto-triggers a "Bug Fix" agent).
    - **Remote Comms:** Send instructions via **Telegram, SMS, or Email** to your agent.
    - **System Events:** Build failures, deployment alerts, or time-based schedules.
- **Persistent Conversations:** Agent sessions persist even when you are away. You can start a task, leave, checks its status via SMS, and return to find the work completed.

### 3. 🧠 Universal Model Connectivity & Intelligent Cycling
Firefly breaks the vendor lock-in. It is agnostic to the AI model provider, giving developers true freedom.
- **Universal Support:** Connects to **ANY** AI source:
    - Google (Gemini)
    - OpenAI (GPT-4)
    - Anthropic (Claude)
    - OpenRouter
    - Local Models (Ollama, LM Studio)
    - Custom URLs / Enterprise Endpoints
- **Smart Orchestration:**
    - **Priority Cycling:** Define a hierarchy of models (e.g., *Try Gemini Flash First -> Failover to Claude Opus -> Fallback to Local Llama*).
    - **Usage Management:** If a rate limit is hit, Firefly instantly and transparently switches to the next available model in your priority list, ensuring zero downtime.

### 4. 🔄 Continuous Development Mode
Firefly introduces the concept of **"Always-On" Development**.
- **AI Orchestrators:** Specialized supervisor agents that manage the project lifecycle from start to finish.
- **Autonomous Management:** These orchestrators assign tasks to sub-agents, monitor progress, and verify results.
- **Production Guarantee:** The system ensures that all requirements are met, 100% of tests pass, and the artifact is fully ready for deployment before marking a task as complete. 
- **Set & Forget:** Define the project goal, and the Orchestrator runs continuous loops until the software is production-ready.

---

## 🏗️ Architecture

1.  **Base:** [Microsoft VS Code](https://github.com/microsoft/vscode) (Detached Fork).
2.  **Automation Layer:** `mcp-global` (Python-based automated toolchain).
3.  **Intelligence Layer:** Firefly Agent Manager (Rust/Python/WASM hybrid for high-performance agent orchestration).

## 🛠️ Getting Started

### Prerequisites
- Python 3.10+
- Node.js (for VS Code development)
- Git

### Installation
1.  **Clone the Repo:**
    ```bash
    git clone https://github.com/FatStinkyPanda/Project-Firefly.git
    cd Project-Firefly
    ```
2.  **Bootstrap MCP-Global:**
    ```bash
    # Installs hooks and automation tools
    python mcp-global/mcp-global-rules/mcp.py setup --all
    ```
3.  **Build Firefly:**
    *Follow standard VS Code build instructions provided in the `vscode/` directory.*

---

## 🤝 Contributing
Firefly follows the **MCP-Global** protocol. All contributions must pass the automated security and quality gates.
- Always run `mcp.py context` before starting work.
- Use `mcp.py fix` to auto-resolve linting issues.
- **Never disable a hook.** Fix the underlying root cause.

---

*Project-Firefly: Illuminating the path to autonomous software engineering.*
