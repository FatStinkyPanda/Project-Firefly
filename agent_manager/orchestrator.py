import logging

from agent_manager.core.event_bus import bus

logger = logging.getLogger("FireflyOrchestrator")

class OrchestratorManager:
    """
    Manages the lifecycle and execution of agents based on triggers.
    """
    def __init__(self, event_bus, model_client):
        self.event_bus = event_bus
        self.model_client = model_client
        self.is_running = False
        # Subscribe to events
        self.event_bus.subscribe("webhook_event", self.handle_webhook)

    def start(self):
        self.is_running = True
        logger.info("Orchestrator started. Defined role: Lead Developer.")
        self.event_bus.subscribe("webhook_event", self.handle_event)
        self.event_bus.subscribe("telegram_input", self.handle_event)

        logger.info(f"Orchestrator started. Defined role: {self.role}.")

        # In a real continuous mode, this might loop or sleep
        # For now, it relies on the main thread keeping it alive
        pass

    def stop(self):
        self.is_running = False
        logger.info("Orchestrator stopped.")

    def handle_event(self, event_type: str, payload: Dict[str, Any]):
        """
        Main Event Handler.
        Dispatches events to specific logic based on type.
        """
        logger.info(f"Orchestrator received event: {event_type}")
        
        if event_type == "webhook_event":
            self.handle_webhook(payload)
        elif event_type == "telegram_input":
            self.handle_telegram(payload)

    def handle_webhook(self, payload: Dict[str, Any]):
        """Handle incoming webhooks."""
        data = payload.get('data')
        logger.info(f"Processing webhook data: {data}")
        
        # Experimental: Use Model Client to analyze payload
        if self.model_client:
            try:
                analysis = self.model_client.generate(f"Analyze this webhook payload: {data}")
                logger.info(f"Model Analysis: {analysis}")
            except Exception as e:
                logger.error(f"Model generation failed: {e}")
        
        # Original logic for handling the webhook payload (now removed from here)
        # The original logic for bug_report/feature_request is removed as per the instruction's snippet.
        # If this logic needs to be preserved, it would need to be re-added or moved.

    def handle_telegram(self, payload: Dict[str, Any]):
        """Handle incoming Telegram messages."""
        chat_id = payload.get("chat_id")
        text = payload.get("text")
        user = payload.get("user")
        
        logger.info(f"Processing Telegram message from {user}: {text}")
        
        if not self.model_client:
            logger.warning("No Model Client available to process Telegram message.")
            return

        try:
            # Generate response using AI
            response_text = self.model_client.generate(
                prompt=text,
                system_prompt=f"You are Firefly, an AI agent helper. You are chatting with {user} via Telegram. Keep answers concise."
            )
            
            # Send response back via Event Bus
            self.event_bus.publish("telegram_output", {
                "chat_id": chat_id,
                "text": response_text
            })
            logger.info(f"Sent Telegram reply to {chat_id}")
            
        except Exception as e:
            self.dispatch_agent("BugFixAgent", payload)
        elif event_type == "feature_request":
            logger.info("✨ FEATURE REQUEST. Dispatching 'FeatureAgent'...")
            self.dispatch_agent("FeatureAgent", payload)
        else:
            logger.info(f"Generic event received. Logging for context: {payload}")

    def dispatch_agent(self, agent_name: str, clean_payload: dict):
        """
        Simulate dispatching a sub-agent.
        In the full system, this would spin up a new LLM context or mcp-agent session.
        """
        logger.info(f"🚀 [Orchestrator] -> Assigning task to {agent_name}")
        logger.info(f"   Context: {clean_payload}")
        # Placeholder for actual agent spin-up
        logger.info(f"   {agent_name} is now working (simulated)")

