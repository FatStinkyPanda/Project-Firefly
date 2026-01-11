import unittest
import json
import os
import shutil
import time
from pathlib import Path
from agent_manager.core.event_bus import EventBusService
from agent_manager.core.peer_discovery import PeerDiscoveryService
from agent_manager.orchestrator import OrchestratorManager
from unittest.mock import MagicMock, patch

class TestMultiAgentCoordination(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/tmp_nsync")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        self.bus = EventBusService()
        self.model_client = MagicMock()
        # Pass test directory to PeerDiscovery
        self.peer_discovery = PeerDiscoveryService(event_bus=self.bus, nsync_path=str(self.test_dir))
        
        self.orchestrator = OrchestratorManager(
            event_bus=self.bus,
            model_client=self.model_client,
            peer_discovery=self.peer_discovery
        )
        self.orchestrator.start()
        self.peer_discovery.start()

    def tearDown(self):
        self.peer_discovery.stop()
        self.orchestrator.stop()
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_peer_discovery_and_delegation(self):
        """Verify that a peer is discovered and a task is delegated to it."""
        # 1. Simulate a peer heartbeat
        peer_identity = "WizardPanda"
        peer_file = self.test_dir / ".nsync_agents" / "remote_host.json"
        peer_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(peer_file, "w") as f:
            json.dump({
                "hostname": "remote_host",
                "identity": peer_identity,
                "timestamp": time.time(),
                "status": "active"
            }, f)

        # Synchronously refresh discovery
        self.peer_discovery.refresh()
        
        self.assertIn(peer_identity, self.peer_discovery.peers)

        # 2. Mock AI response to delegate a task
        mock_response = MagicMock()
        mock_response.text = f'<delegate recipient="{peer_identity}">Scan the network for vulnerabilities.</delegate>'
        self.model_client.generate.return_value = mock_response

        # 3. Trigger orchestrator
        self.bus.publish("telegram_input", {"text": "help me scan", "chat_id": 1, "user": "tester"})

        # 4. Verify message exists in recipient's mailbox
        mailbox = self.test_dir / ".nsync_agents" / "messages"
        messages = list(mailbox.glob(f"{peer_identity}_*.json"))
        self.assertTrue(len(messages) > 0, "No message found in mailbox for peer.")
        
        with open(messages[0], "r") as f:
            msg = json.load(f)
            self.assertEqual(msg["to"], peer_identity)
            self.assertEqual(msg["type"], "task")
            self.assertEqual(msg["content"]["text"], "Scan the network for vulnerabilities.")

if __name__ == "__main__":
    unittest.main()
