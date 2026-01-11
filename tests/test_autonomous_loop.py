import unittest
from agent_manager.core.event_bus import EventBusService
from agent_manager.core.config_service import ConfigurationService
from agent_manager.core.tag_parser import TagParserService
from agent_manager.orchestrator import OrchestratorManager
from unittest.mock import MagicMock, patch

class TestFireflyAutonomousLoop(unittest.TestCase):
    def setUp(self):
        self.bus = EventBusService()
        self.config = ConfigurationService() # Uses defaults
        self.model_client = MagicMock()
        self.orchestrator = OrchestratorManager(
            event_bus=self.bus,
            model_client=self.model_client,
            config_service=self.config
        )
        self.orchestrator.start()

    def test_autonomous_command_execution(self):
        """Verify that <command> tags are parsed and executed if safe."""
        # Mock AI response with thoughts and commands
        mock_response = MagicMock()
        mock_response.text = (
            "<thought>I need to check the project status.</thought>\n"
            "<command>git status</command>\n"
            "<message>Status checked.</message>"
        )
        self.model_client.generate.return_value = mock_response

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout="On branch main", stderr="", returncode=0)
            
            # Trigger telegram input
            self.bus.publish("telegram_input", {"text": "check status", "chat_id": 123, "user": "test_user"})
            
            # Check if subprocess was called with the correct command
            mock_run.assert_called_with("git status", shell=True, capture_output=True, text=True, timeout=30)

    def test_safety_policy_block(self):
        """Verify that destructive commands are blocked by the safety policy."""
        mock_response = MagicMock()
        mock_response.text = "<command>rm -rf /</command>"
        self.model_client.generate.return_value = mock_response

        with patch('subprocess.run') as mock_run:
            self.bus.publish("telegram_input", {"text": "delete everything", "chat_id": 123, "user": "test_user"})
            
            # Subprocess should NOT be called for unsafe command
            mock_run.assert_not_called()

if __name__ == "__main__":
    unittest.main()
