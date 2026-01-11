import logging
import re
import subprocess

from agent_manager.core.tag_parser import TagParserService

logger = logging.getLogger("FireflyOrchestrator")

class OrchestratorManager:
    """
    Manages the lifecycle and execution of agents based on triggers.
    Robustly handles AI responses using the Firefly Tagging System (FTS).
    """
    def __init__(self, event_bus, model_client, config_service=None, peer_discovery=None, session_manager=None):
        self.event_bus = event_bus
        self.model_client = model_client
        self.config_service = config_service
        self.peer_discovery = peer_discovery
        self.session_manager = session_manager
        self.tag_parser = TagParserService()
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

    def stop(self):
        self.is_running = False
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
        elif event_type == "system_event":
            self.handle_system_event(payload)
        elif event_type == "peer_message":
            session_id = f"peer_{payload.get('from')}"
            self.handle_peer_message(payload, session_id=session_id)

    def process_request(self, prompt: str, source: str, context: dict = None, session_id: str = "default"):
        """
        Unified processing logic using AI + Tag Parsing + Session Memory.
        """
        if not self.model_client:
            logger.warning("No Model Client available.")
            return

        # 1. Manage History
        history_context = ""
        if self.session_manager:
            self.session_manager.add_message(session_id, "user", prompt)
            history_context = self.session_manager.format_for_ai(session_id)

        system_prompt = (
            "You are the Firefly Lead Orchestrator. "
            "Use <thought> tags for your reasoning. "
            "Use <command> tags to execute shell commands. "
            "Use <message> tags to communicate back to the user. "
            "Use <delegate recipient=\"agent_name\">task_description</delegate> to assign work to a peer. "
            "Be precise and autonomous.\n"
            f"{history_context}"
        )

        try:
            response = self.model_client.generate(prompt, system_prompt=system_prompt)
            parsed = self.tag_parser.parse(response.text)

            # Record assistant response in history
            if self.session_manager:
                self.session_manager.add_message(session_id, "assistant", response.text)

            # 2. Log thoughts
            for thought in parsed.thoughts:
                logger.info(f"CORE THOUGHT: {thought}")

            # 2. Execute commands (with safety)
            for cmd in parsed.commands:
                self.execute_command(cmd)

            # 3. Handle delegations
            self._handle_delegations(response.text)

            # 4. Route messages
            for msg in parsed.messages:
                if source == "telegram" and context:
                    self.event_bus.publish("telegram_output", {
                        "chat_id": context.get("chat_id"),
                        "text": msg
                    })
                else:
                    logger.info(f"AI MESSAGE: {msg}")

        except Exception as e:
            logger.error(f"Failed to process request: {e}")

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
            return True
        except Exception as e:
            logger.error(f"Execution Error: {e}")
            return False

    def handle_system_event(self, payload: dict):
        """Logic for file changes and other system events."""
        ev_type = payload.get("type")
        path = payload.get("path")
        if ev_type == "file_change" and path.endswith(".py"):
             self.process_request(f"Analyze change in file: {path}", source="system")

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
