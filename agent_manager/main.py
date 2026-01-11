import logging
import os # Added for os.environ.get
import time

from agent_manager.core.event_bus import EventBus
from agent_manager.models.gemini import GeminiService # Added
from agent_manager.models.manager import ModelClientManager
from agent_manager.models.openai import OpenAIService # Added
from agent_manager.orchestrator import OrchestratorManager
from agent_manager.triggers.telegram import TelegramService # Added
from agent_manager.triggers.webhook import WebhookTrigger

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FireflyAgentManager")

def main():
    logger.info("Initializing Firefly Agent Manager...")

    # 1. Initialize Event Bus
    bus = EventBusService()

    # 2. Initialize Model Client Manager
    # Load keys from environment
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    providers = []
    if gemini_key:
        providers.append(GeminiService(api_key=gemini_key))
    if openai_key:
        providers.append(OpenAIService(api_key=openai_key))

    if not providers:
        logger.warning("No AI providers configured (missing API keys). Model features will be disabled.")

    model_client = ModelClientManager(providers)

    # 3. Initialize Orchestrator
    orchestrator = OrchestratorManager(event_bus=bus, model_client=model_client)

    # 4. Initialize Triggers
    webhook_trigger = WebhookService(event_bus=bus, port=5000)
    telegram_service = TelegramService(event_bus=bus)

    # 5. Start Services
    webhook_trigger.start()
    telegram_service.start()

    # 6. Keep Alive Loop
    try:
        while True:
            logger.info("   - Status: Waiting for events...")
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Exiting...")
    finally:
        webhook_trigger.stop()
        telegram_service.stop()
        orchestrator.stop()

if __name__ == "__main__":
    main()
