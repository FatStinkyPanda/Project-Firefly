import logging
import os
import re
import subprocess

from agent_manager.core.git_manager import GitManager
from agent_manager.core.tag_parser import TagParserService
import asyncio

logger = logging.getLogger("FireflyOrchestrator")

class OrchestratorManager:
    """
    Manages the lifecycle and execution of agents based on triggers.
    Robustly handles AI responses using the Firefly Tagging System (FTS).
    """
    def __init__(self, event_bus, model_client, config_service=None, peer_discovery=None, session_manager=None, browser_service=None, artifact_service=None, prompt_service=None, memory_service=None, notification_service=None, context_service=None):
        self.event_bus = event_bus
        self.model_client = model_client
        self.config_service = config_service
        self.peer_discovery = peer_discovery
        self.session_manager = session_manager
        self.browser_service = browser_service
        self.artifact_service = artifact_service
        self.prompt_service = prompt_service
        self.memory_service = memory_service
        self.notification_service = notification_service
        self.context_service = context_service
        self.is_autonomous = False
        self.git_manager = GitManager()
        self.tag_parser = TagParserService()
        self._current_conflicts = set()
        self._total_cost = 0.0
        self._is_autonomous = False
        self.is_running = False

    def start(self):
        self.is_running = True
        logger.info("Orchestrator started. Defined role: Lead Developer.")
        self.event_bus.subscribe("webhook_event", self.handle_event)
        self.event_bus.subscribe("telegram_input", self.handle_event)
        self.event_bus.subscribe("system_event", self.handle_event)
        self.event_bus.subscribe("peer_message", self.handle_event)
        self.event_bus.subscribe("peer_joined", self.handle_event)
        self.event_bus.subscribe("peer_left", self.handle_event)
        self.event_bus.subscribe("git_event", self.handle_event)
        self.event_bus.subscribe("email_input", self.handle_event)
        self.event_bus.subscribe("sms_input", self.handle_event)
        self.event_bus.subscribe("ide_set_mode", self.handle_event)
        self.event_bus.subscribe("ide_intent", self.handle_event)
        self.event_bus.subscribe("ide_create_agent", self.handle_event)
        self.event_bus.subscribe("ide_delete_agent", self.handle_event)
        self.event_bus.subscribe("ide_set_safety_mode", self.handle_event)
        self.event_bus.subscribe("ide_set_active_model", self.handle_event)
        self.event_bus.subscribe("ide_chat", self.handle_event)

    def stop(self):
        self.is_running = False
        if self.browser_service:
            asyncio.run(self.browser_service.stop())
        logger.info("Orchestrator stopped.")

    def handle_event(self, event_type: str, payload: dict):
        """Main routing hub for incoming events."""
        if not self.is_running: return

        logger.info(f"Orchestrator received event: {event_type}")

        if event_type == "webhook_event":
            self.process_request(f"Webhook Payload: {payload.get('data')}", source="webhook")
        elif event_type == "telegram_input":
            session_id = f"tg_{payload.get('chat_id')}"
            self.process_request(payload.get("text"), source="telegram", context=payload, session_id=session_id)
        elif event_type == "email_input":
            from_addr = payload.get("from")
            session_id = f"email_{from_addr.replace('@', '_').replace('.', '_')}"
            self.process_request(payload.get("text"), source="email", context=payload, session_id=session_id)
        elif event_type == "sms_input":
            from_num = payload.get("from")
            session_id = f"sms_{from_num.replace('+', '').replace(' ', '')}"
            self.process_request(payload.get("text"), source="sms", context=payload, session_id=session_id)
        elif event_type == "ide_set_mode":
            is_autonomous = payload.get("autonomous", False)
            self.set_autonomous_mode(is_autonomous)
        elif event_type == "ide_intent":
            intent_id = payload.get("id")
            intent_args = payload.get("args")
            self.handle_intent(intent_id, intent_args)
        elif event_type == "ide_create_agent":
            self.handle_create_agent(payload)
        elif event_type == "ide_delete_agent":
            self.handle_delete_agent(payload)
        elif event_type == "ide_set_safety_mode":
            self.handle_set_safety_mode(payload)
        elif event_type == "ide_set_active_model":
            self.handle_set_active_model(payload)
        elif event_type == "ide_chat":
            text = payload.get("text")
            logger.info(f"Received chat: {text}")
            self.process_request(text, source="chat", session_id="firefly_chat")
        elif event_type == "system_event":
            self.handle_system_event(payload)
        elif event_type == "git_event":
            self.handle_git_event(payload)
        elif event_type == "usage_report":
            self._total_cost += payload.get("cost", 0)
            self.set_status(cost=self._total_cost)

    def set_autonomous_mode(self, enabled: bool):
        """Toggle autonomous execution mode."""
        self.is_autonomous = enabled
        logger.info(f"Orchestrator autonomous mode: {'ENABLED' if enabled else 'DISABLED'}")
        # Log this as an artifact
        if self.artifact_service:
            self.artifact_service.create_artifact(
                "internal",
                "mode_change",
                f"Autonomous mode set to {enabled}",
                session_id="system"
            )
        # We also broadcast a status update to the IDE
        print(f"[FIREFLY:STATUS] mode={'autonomous' if enabled else 'manual'}")

    def handle_intent(self, intent_id: str, args: Any):
        """Process a user intent as an observation for the agent."""
        logger.info(f"Processing user intent: {intent_id}")
        # In a real scenario, this would trigger a planning pulse if in autonomous mode
        if self.is_autonomous:
             message = f"User performed action: {intent_id} with args: {args}. Does this require any follow-up?"
             # We could queue a background task here
             self.process_request(message, source="system_intent", session_id="autonomous_loop")

    def handle_create_agent(self, payload: dict):
        """Handle agent creation request from the IDE."""
        agent_id = payload.get("id")
        name = payload.get("name")
        persona = payload.get("persona")
        logger.info(f"Summoning Agent: {name} (ID: {agent_id}) -> {persona}")
        self.set_status(thought=f"Spectral manifest of '{name}' complete. Focus: {persona}")

    def handle_delete_agent(self, payload: dict):
        """Handle agent deletion request from the IDE."""
        agent_id = payload.get("id")
        logger.info(f"Banishing Agent: {agent_id}")
        self.set_status(thought=f"Agent {agent_id} returned to the void.")

    def handle_set_safety_mode(self, payload: dict):
        """Handle safety mode change from IDE."""
        mode = payload.get("mode", "MANUAL")
        logger.info(f"Safety Mode -> {mode}")
        self._safety_mode = mode
        self.set_status(thought=f"Command approval mode: {mode}")

    def handle_set_active_model(self, payload: dict):
        """Handle active model change from IDE."""
        model_id = payload.get("model_id", "gemini-2.0-flash")
        logger.info(f"Active Model -> {model_id}")
        if self.model_client:
            # Update the model client's active model
            self.model_client.set_active_model(model_id)
        self.set_status(thought=f"Model switched to: {model_id}")

    def process_request(self, text: str, source: str = "manual", context: Optional[Dict] = None, session_id: str = "default", agent_role: str = "Lead Orchestrator"):
        """
        Sync bridge to async processing.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.process_request_async(text, source, context, session_id, agent_role))

    async def process_request_async(self, prompt: str, source: str, context: dict = None, session_id: str = "default", agent_role: str = "Lead Orchestrator"):
        """
        Unified processing logic using AI + Tag Parsing + Session Memory.
        """
        if not self.model_client:
            logger.warning("No Model Client available.")
            return

        # 0. Sync UI Mode
        if source in ["system", "git", "delegate", "peer"]:
            self.set_status(mode="autonomous")
        else:
            self.set_status(mode="interactive")

        # 1. Manage History
        history_context = ""
        if self.session_manager:
            self.session_manager.add_message(session_id, "user", prompt)
            history_context = self.session_manager.format_for_ai(session_id)

            # Retrieve relevant semantic memories
            if self.memory_service:
                memories = self.memory_service.query(prompt, top_k=3)
                if memories:
                    mem_context = "\n[RELEVANT HISTORICAL CONTEXT]\n" + "\n".join([f"- {m['text']}" for m in memories])
                    history_context += mem_context
            
            # Retrieve project state (Active Context Compression)
            if self.context_service:
                # Assuming root is current working dir or similar
                state = self.context_service.get_project_state(os.getcwd())
                state_summary = f"""
[PROJECT STATE]
Global Goal: {state.get('global_goal')}
Active Task: {state.get('current_active_task')}
Items in Queue: {len(state.get('next_step_queue', []))}
Known Bugs: {', '.join(state.get('known_bugs', []))}
"""
                history_context += state_summary

        # 2. Construct System Prompt using PromptService
        if self.prompt_service:
            system_prompt = self.prompt_service.get_prompt(agent_role, session_context=history_context)
        else:
            # Fallback to legacy logic if service not available
            system_prompt = f"You are the Firefly {agent_role}. {history_context}"

        try:
            response = self.model_client.generate(prompt, system_prompt=system_prompt)
            parsed = self.tag_parser.parse(response.text)

            # Record assistant response in history
            if self.session_manager:
                self.session_manager.add_message(session_id, "assistant", response.text)

            # 2. Log thoughts
            for thought in parsed.thoughts:
                logger.info(f"CORE THOUGHT: {thought}")
                self.set_status(thought=thought)
                if self.artifact_service:
                    self.artifact_service.create_artifact(session_id, "thought", thought)

            # 2. execute commands (with safety)
            for cmd in parsed.commands:
                result = self.execute_command(cmd)
                if self.artifact_service:
                    self.artifact_service.create_artifact(session_id, "command", {"command": cmd, "success": result})

            # 2. Extract Thoughts and Index in Memory
            thoughts = re.findall(r'<thought>(.*?)</thought>', response.text, re.DOTALL | re.IGNORECASE)
            for t in thoughts:
                if self.memory_service:
                    self.memory_service.upsert(t.strip(), {"type": "thought", "session": session_id})

            # 2.5 Handle Browser Actions
            await self._handle_browser_actions(response.text, session_id)
            
            # 2.6 Handle Skeleton Actions
            self._handle_skeleton_requests(response.text, session_id)

            # 3. Handle plans and delegations
            self._handle_plans(response.text, session_id)
            self._handle_delegations(response.text)

            # 4. Route messages
            for msg in parsed.messages:
                if source == "telegram" and context:
                    self.event_bus.publish("telegram_output", {
                        "chat_id": context.get("chat_id"),
                        "text": msg
                    })
                elif source == "email" and context:
                    self.event_bus.publish("email_output", {
                        "to": context.get("from"),
                        "subject": f"Re: {context.get('subject', 'Firefly Response')}",
                        "text": msg
                    })
                elif source == "sms" and context:
                    self.event_bus.publish("sms_output", {
                        "to": context.get("from"),
                        "text": msg
                    })
                else:
                    logger.info(f"AI MESSAGE: {msg}")

            # 5. Handle Git Resolutions
            resolutions = re.findall(r'<git_resolve\s+path=["\'](.*?)["\']>(.*?)</git_resolve>', response.text, re.DOTALL | re.IGNORECASE)
            for path, resolved in resolutions:
                logger.info(f"Applying Git resolution for: {path}")
                self.git_manager.resolve_file(path, resolved.strip())
                self._current_conflicts.discard(path)
                if not self._current_conflicts:
                    logger.info("All conflicts resolved. Committing merge.")
                    self.git_manager.commit("chore: resolve merge conflicts autonomously", all_files=True)

        except Exception as e:
            logger.error(f"Failed to process request: {e}")

    async def _handle_browser_actions(self, text: str, session_id: str):
        """Extracts and executes <browser> tags."""
        if not self.browser_service:
            return

        # Regex to find <browser action="..." ... />
        # Example: <browser action="navigate" url="https://google.com"/>
        browser_tags = re.findall(r'<browser\s+([^>]*?)/?>', text, re.IGNORECASE)
        for tag_content in browser_tags:
            # Parse attributes
            attrs = dict(re.findall(r'(\w+)=["\'](.*?)["\']', tag_content))
            action = attrs.get("action")
            if not action:
                continue

            logger.info(f"Browser Action: {action} with {attrs}")
            self.set_status(thought=f"Executing browser action: {action}")

            result = await self.browser_service.run_action(action, **attrs)

            # Feed result back to the session history
            if self.session_manager:
                result_msg = f"[BROWSER RESULT] {action}: {result}"
                self.session_manager.add_message(session_id, "system", result_msg)

                if self.artifact_service:
                    self.artifact_service.create_artifact(session_id, "browser_result", {"action": action, "result": result})

                # Optional: Proactively trigger a follow-up if it was a scrape/screenshot
                if action in ["get_text", "navigate", "screenshot"]:
                    # We might want to trigger the agent again with the new context
                    # to keep the autonomous flow going.
                    self.process_request("Analyze the browser result and continue.", source="system", session_id=session_id)

    def _handle_skeleton_requests(self, text: str, session_id: str):
        """Extracts and executes <skeleton path="..."> tags."""
        if not self.context_service:
            return

        # Regex to find <skeleton path="..." />
        skeleton_tags = re.findall(r'<skeleton\s+path=["\'](.*?)["\']\s*/?>', text, re.IGNORECASE)
        for path in skeleton_tags:
            logger.info(f"Skeleton Request for: {path}")
            
            try:
                # Use environment/project root logic if possible, assuming absolute or relative to root
                # For now, simplistic check
                if not os.path.isabs(path):
                    # How do we know project root? We might guess or need configuration.
                    # We'll assume relative to CWD for now, or rely on absolute paths.
                    # Better: try to find it.
                    pass
                
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    skeleton = self.context_service.generate_skeleton(content, path)
                    
                    # Feed back to session
                    if self.session_manager:
                        msg = f"[SKELETON VIEW] {path}:\n{skeleton}"
                        self.session_manager.add_message(session_id, "system", msg)
                else:
                     if self.session_manager:
                        self.session_manager.add_message(session_id, "system", f"[ERROR] File not found for skeleton: {path}")

            except Exception as e:
                logger.error(f"Failed to generate skeleton: {e}")
                if self.session_manager:
                     self.session_manager.add_message(session_id, "system", f"[ERROR] Skeleton generation failed: {e}")

    def execute_command(self, command: str):
        """Executes a command if it passes the safety policy."""
        if self.config_service:
            if not self.config_service.is_command_safe(command, agent_context="orchestrator"):
                logger.warning(f"BLOCKED: Command '{command}' failed safety check.")
                return False

        logger.info(f"EXECUTING: {command}")
        try:
            # Note: Avoid shell=True for security. We wrap in powershell/sh instead to keep shell features.
            if os.name == 'nt':
                cmd_args = ["powershell.exe", "-Command", command]
            else:
                cmd_args = ["/bin/sh", "-c", command]

            result = subprocess.run(cmd_args, shell=False, capture_output=True, text=True, timeout=30)
            if result.stdout:
                logger.info(f"STDOUT: {result.stdout.strip()}")
            if result.stderr:
                logger.error(f"STDERR: {result.stderr.strip()}")

            if self.artifact_service:
                 # Note: Ideally we'd pass the session_id here, but execute_command doesn't have it.
                 # For now, we record command status generically or refine the signature.
                 pass

            return result.returncode == 0
        except Exception as e:
            logger.error(f"Execution Error: {e}")
            return False

    def set_status(self, thought=None, cost=None, mode=None):
        """Communicates the current status to the Firefly IDE host."""
        status_parts = ["[FIREFLY:STATUS]"]
        if thought: status_parts.append(f'thought="{thought}"')
        if cost is not None: status_parts.append(f"cost={cost:.6f}")
        if mode:
            self._is_autonomous = (mode.lower() == "autonomous")
            status_parts.append(f"mode={mode}")
        elif self._is_autonomous:
            status_parts.append("mode=autonomous")
        else:
            status_parts.append("mode=idle")

        print(" ".join(status_parts), flush=True)

    def handle_system_event(self, payload: dict):
        """Logic for file changes and other system events."""
        ev_type = payload.get("type")
        path = payload.get("path")
        if ev_type == "file_change" and path.endswith(".py"):
             self.process_request(f"Analyze change in file: {path}", source="system")

    def handle_git_event(self, payload: dict):
        """Logic for Git events like commits, checkouts, and merges."""
        ev_type = payload.get("type")
        data = payload.get("data", {})

        if ev_type == "merge_state_change":
            # Check for conflicts
            conflicts = self.git_manager.get_conflicts()
            if conflicts:
                self._current_conflicts = set(conflicts)
                logger.warning(f"Git Conflicts detected in files: {conflicts}")
                self.set_status(mode="autonomous", thought="Analyzing merge conflicts...")

                # Activate GitFlowManager logic or handle in Orchestrator
                for conflict_file in conflicts:
                    content = self.git_manager.get_file_content_with_conflicts(conflict_file)
                    self.process_request(
                        f"CRITICAL: Git merge conflict detected in {conflict_file}.\n"
                        f"Content with markers:\n{content}\n"
                        "Please provide the resolved content using <git_resolve path=\"...\">...</git_resolve> tags.",
                        source="system",
                        session_id="git_conflict_resolution",
                        agent_role="GitFlowManager"
                    )

        elif ev_type == "branch_checkout":
             logger.info(f"Switched to branch: {data.get('branch')}")

        elif ev_type == "commit_detected":
             if self.config_service and self.config_service.get("git_agent_always_live"):
                 # Review the commit autonomously
                 self.process_request(
                     f"New commit detected on branch {data.get('branch')} ({data.get('commit')}). "
                     "Perform an autonomous review of the changes and ensure quality standards are met.",
                     source="system",
                     session_id=f"git_review_{data.get('branch')}",
                     agent_role="GitFlowManager"
                 )

    def _handle_plans(self, text: str, session_id: str):
        """Extracts and parses <plan> tags for task decomposition."""
        plans = re.findall(r'<plan>(.*?)</plan>', text, re.DOTALL | re.IGNORECASE)
        for plan_content in plans:
            logger.info(f"PLAN DETECTED: {plan_content.strip()}")
            if self.artifact_service:
                self.artifact_service.create_artifact(session_id, "plan", plan_content.strip())

            # Simple parsing of checkboxes like: - [ ] Task name (Role)
            tasks = re.findall(r'- \[ \] (.*?) \((.*?)\)', plan_content)
            for task_desc, role in tasks:
                 logger.info(f"Sub-task identified: {task_desc} (Assigned to: {role})")
                 if self.notification_service:
                     self.notification_service.notify(f"Decomposing task: {task_desc} -> Routing to {role}")
                 # Autonomously delegate sub-tasks
                 self.delegate_task(role, f"Part of plan for {session_id}: {task_desc}")

    def handle_peer_message(self, payload: dict, session_id: str = "peer_unknown"):
        """Handle coordination messages from other agents."""
        msg_from = payload.get("from")
        msg_type = payload.get("type")
        content = payload.get("content", {})

        logger.info(f"Peer Message from {msg_from}: {msg_type}")
        if msg_type == "result":
            self.process_request(f"Agent {msg_from} returned result: {content.get('text')}", source="peer", session_id=session_id)

    def _handle_delegations(self, text: str):
        """Extract and process <delegate> tags."""
        # More robust regex for delegation
        delegations = re.findall(r'<delegate\s+recipient=["\'](.*?)["\']>(.*?)</delegate>', text, re.DOTALL | re.IGNORECASE)
        for recipient, task in delegations:
            self.delegate_task(recipient, task.strip())

    def delegate_task(self, recipient: str, task: str):
        """Delegates a task to a discovered peer by identity, role, or capability."""
        if not self.peer_discovery:
            logger.warning("No PeerDiscoveryService available.")
            return

        if recipient == "GitFlowManager" and not any(p.get("role") == "GitFlowManager" for p in self.peer_discovery.peers.values()):
            logger.info("No remote GitFlowManager found. Spawning local GitFlowManager logic.")
            self.process_request(task, source="delegate", agent_role="GitFlowManager")
            return

        target_agents = []

        # 1. Match by Identity
        if recipient in self.peer_discovery.peers:
            target_agents.append(recipient)

        # 2. Match by Role
        elif recipient != "broadcast":
            for p_id, p_data in self.peer_discovery.peers.items():
                if p_data.get("role") == recipient:
                    target_agents.append(p_id)
                elif recipient in p_data.get("capabilities", []):
                    target_agents.append(p_id)

        # 3. Handle Broadcast
        if recipient == "broadcast":
            target_agents = list(self.peer_discovery.peers.keys())

        if not target_agents:
            logger.warning(f"No agents found for target/role/capability: {recipient}")
            return

        # For specific roles, we pick the first available or broadcast to all?
        # Logic: If it's a specific identity, send to one. If it's a role/capability, pick one (load balance later).
        # For now, if identity not found but role found, pick the first one.
        for agent_id in target_agents:
            logger.info(f"DELEGATING: '{task}' to {agent_id} (Target: {recipient})")
            self.peer_discovery.send_message(agent_id, "task", {"text": task})
            if recipient != "broadcast" and recipient not in self.peer_discovery.peers:
                break # Only send to one if it was a role/capability match

    def handle_peer_auth(self, payload: dict):
        """Handle new peer discovery."""
        identity = payload.get("identity")
        logger.info(f"🤝 Handshake with peer: {identity}")

    def dispatch_agent(self, agent_name: str, payload: dict):
        """Local agent dispatch (simulated)."""
        logger.info(f"🚀 [Orchestrator] -> Assigning task to {agent_name}")
