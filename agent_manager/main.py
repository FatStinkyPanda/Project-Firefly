import logging
import os # Added for os.environ.get
import time

from agent_manager.core.artifact_service import ArtifactService
from agent_manager.core.browser_adapter import BrowserService
from agent_manager.core.config_service import ConfigurationService
from agent_manager.core.dashboard_service import DashboardService
from agent_manager.core.event_bus import EventBusService
from agent_manager.core.git_service import GitMonitoringService
from agent_manager.core.session_manager import SessionManager
from agent_manager.models.manager import ModelClientManager
from agent_manager.orchestrator import OrchestratorManager
from agent_manager.triggers.system_events import WorkspaceMonitoringService
from agent_manager.triggers.telegram import TelegramService
from agent_manager.triggers.webhook import WebhookService

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FireflyAgentManager")

from agent_manager.core.peer_discovery import PeerDiscoveryService

# [Existing imports ...]

def main():
    logger.info("Initializing Firefly Agent Manager...")

    # 1. Initialize Event Bus
    bus = EventBusService()

    # 2. Initialize Configuration
    config = ConfigurationService()

    # 3. Initialize Model Client Manager
    model_client = ModelClientManager(event_bus=bus, config_service=config)

    # 3.5 Initialize Session Management
    session_manager = SessionManager()

    # 3.6 Initialize Browser Adapter
    browser_adapter = BrowserService(event_bus=bus)

    # 3.7 Initialize Artifact Service
    artifact_service = ArtifactService()

    # 4. Initialize Peer Discovery
    peer_discovery = PeerDiscoveryService(event_bus=bus)
    peer_discovery.start()

    # 5. Initialize Orchestrator
    orchestrator = OrchestratorManager(
        event_bus=bus,
        model_client=model_client,
        config_service=config,
        peer_discovery=peer_discovery,
        session_manager=session_manager,
        browser_service=browser_adapter,
        artifact_service=artifact_service
    )
    orchestrator.start()

    # 5. Initialize Triggers
    webhook_service = WebhookService(event_bus=bus, port=5000)
    telegram_service = TelegramService(event_bus=bus)
    workspace_service = WorkspaceMonitoringService(event_bus=bus)
    git_monitor = GitMonitoringService(event_bus=bus)

    # 6. Initialize Dashboard
    dashboard = DashboardService(event_bus=bus)
    dashboard.start()

    # 7. Start Services
    webhook_service.start()
    telegram_service.start()
    workspace_service.start()
    git_monitor.start()

    # 7. Keep Alive Loop
    try:
        while True:
            logger.info("   - Status: Active. Monitoring events...")
            time.sleep(15)
    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Exiting...")
    finally:
        dashboard.stop()
        workspace_service.stop()
        telegram_service.stop()
        webhook_service.stop()
        git_monitor.stop()
        orchestrator.stop()

if __name__ == "__main__":
    main()
