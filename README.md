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
- **Proactive Monitoring:** Real-time file system monitoring (`WorkspaceMonitoringService`) triggers agents on-save for instant review and context updates.
- **Universal Inputs:** Agents can be triggered by:
    - **Webhooks:** (e.g., A bug report submission on your company website auto-triggers a "Bug Fix" agent).
    - **Remote Comms:** Send instructions via **Telegram, SMS, or Email** to your agent.
- **Persistent Conversations:** Agent sessions persist even when you are away. You can start a task, leave, checks its status via SMS, and return to find the work completed.
- **Multi-modal Web Interaction:** Agents can now browse the live web, navigate to URLs, click elements, capture screenshots, and scrape content for real-time analysis.

### 3. 🧠 Universal Model Connectivity & Intelligent Cycling
Firefly breaks the vendor lock-in. It is agnostic to the AI model provider, giving developers true freedom.
- **Universal Support:** Connects to **ANY** AI source:
    - Google (Gemini 1.5 Pro/Flash)
    - OpenAI (GPT-4o/mini)
    - Anthropic (Claude 3.5 Sonnet/Opus)
    - OpenRouter (Access to 100+ Models)
    - Local Models (Ollama, LM Studio)
- **Smart Orchestration:**
    - **Priority Cycling:** Define a hierarchy of models in `options.json` (e.g., *Try Gemini Flash First -> Failover to Claude -> Fallback to Local Llama*).
    - **Usage Management:** Real-time token tracking and cost estimation ($USD) across all providers. If a rate limit is hit, Firefly instantly and transparently switches to the next available model.
    - **Semantic Memory:** Integrated FAISS-driven vector search for long-term project retrieval.

### 4. 🔒 Advanced Safety & Configuration
Firefly provides granular control over autonomous actions through its **Command Approval System**.
- **Adjustable Safety Modes:**
    - **AUTO:** Maximum speed. Most commands are auto-approved.
    - **ORCHESTRATOR_ONLY:** High speed. Commands from the Lead Developer agent are auto-approved.
    - **MANUAL:** Maximum safety. Every system command requires developer intervention.
- **Preconfigured Safe-Defaults:** Firefly includes lists of "Always Safe" (read-only) and "Ask Always" (destructive) commands to protect your device while enabling 100% autonomous development.

### 5. 🗜️ Active Context Compression
Firefly introduces an optional **Active Context Compression** mode designed to enable small local models to work effectively on massive codebases.
- **Why it matters:** Standard 16k context windows cannot hold millions of lines of code. This mode treats the context window as a temporary "workbench" rather than a storage drive.
- **How it works:**
    - **Skeleton View:** Agents work with compressed "skeleton" files (signatures only) to navigate the architecture without reading full implementation details.
    - **Graph RAG:** A knowledge graph maps function calls, allowing agents to find dependencies logically rather than just semantically.
    - **State Management:** Decouples "Project Status" from "Agent Memory," ensuring long-term goals persist even as context is cleared.
- **Configuration:** This mode is **disabled by default**. It is an advanced feature that can be enabled per-agent or per-model in `options.json`.
  > See [active_context_compression.md](active_context_compression.md) for full architectural details.

---

## 🏗️ Architecture

1.  **Base:** [Microsoft VS Code](https://github.com/microsoft/vscode) (Detached Fork).
2.  **Automation Layer:** `mcp-global` (Python-based automated toolchain).
3.  **Intelligence Layer:** Firefly Agent Manager (Python/urllib-based zero-dependency service layer).
4.  **Environment:** Enforced **Python 3.11.x** in an isolated virtual environment (`.venv`).

---

## 🛠️ Recent Technical Decisions & Milestones

### 🛡️ Spectre Mitigation Strategy
During the build of native Node.js modules (like `@vscode/spdlog` and `@vscode/sqlite3`), we encountered `MSB8040` errors requiring Spectre-mitigated libraries. 
- **Decision:** Rather than disabling security mitigations, we opted to install the mandatory `Microsoft.VisualStudio.Component.VC.Runtimes.x86.x64.Spectre` component for Visual Studio 2026.
- **Why:** This ensures the IDE remains secure and production-ready, adhering to our "Fix Properly" philosophy.

### 🧠 Backend Stability (PYTHONPATH & Syntax)
The Agent Backend initially failed due to `ModuleNotFoundError` and `SyntaxError`.
- **Decision:** Injected explicit `PYTHONPATH` in `fireflyMainService.ts` and corrected `from __future__ import annotations` placement across all Python model files.
- **Result:** The backend now reliably spawns and maintains communication with the frontend.

### 🏗️ Service Registration Logic
Restored missing registrations in `workbench.common.main.ts` for `FireflyWorkbenchService`.
- **Why:** This resolved "blank window" launch issues by ensuring core services are available at startup.

### 🌐 Phase 3: Browser Automation Integration
Successfully implemented the `BrowserAdapter` using Playwright.
- **Decision:** Integrated a headless Chromium instance into the `Agent Manager` lifecycle to allow multi-modal web reasoning.
- **Result:** Agents can now perform live web research, verify UI deployments, and interact with external web tools autonomously.

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.11.x** (Strictly enforced)
- **Visual Studio 2026 Build Tools** with Spectre-mitigated libraries.
- **Node.js 22.x**

### Installation & Launch
1.  **Clone the Repo:**
    ```bash
    git clone https://github.com/FatStinkyPanda/Project-Firefly.git
    cd Project-Firefly
    ```
2.  **Rebuild Native Modules:**
    Firefly requires native C++ bindings for its core functions.
    ```powershell
    # Rebuilds all 14 native modules using VS 2026
    .\vscode\scripts\rebuild_all_native.bat
    ```
3.  **Compile & Run:**
    ```bash
    cd vscode
    npm run compile
    .\scripts\code.bat
    ```

---

## 🤝 Contributing
Firefly follows the **MCP-Global** protocol. All contributions must pass the automated security and quality gates.
- Always run `python mcp.py context` before starting work.
- **Never disable a hook.** Fix the underlying root cause.

---

*Project-Firefly: Illuminating the path to autonomous software engineering.*
