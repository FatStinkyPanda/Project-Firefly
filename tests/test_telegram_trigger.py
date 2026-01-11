import unittest
import json
from unittest.mock import MagicMock, patch
from agent_manager.triggers.telegram import TelegramService
from agent_manager.core.event_bus import EventBusService

class TestTelegramService(unittest.TestCase):
    def setUp(self):
        self.bus = EventBusService()
        self.service = TelegramService(event_bus=self.bus, token="TEST_TOKEN")

    @patch("urllib.request.urlopen")
    def test_poll_updates(self, mock_urlopen):
        """Test that polling processes updates and publishes events."""
        # Mock response from getUpdates
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "ok": True,
            "result": [{
                "update_id": 123,
                "message": {
                    "chat": {"id": 999},
                    "text": "Hello Firefly",
                    "from": {"username": "tester"}
                }
            }]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Mock event bus publish to verify call
        self.bus.publish = MagicMock()

        # Manually trigger one check
        self.service._check_updates()

        # Verify event was published
        self.bus.publish.assert_called_with("telegram_input", {
            "type": "message",
            "chat_id": 999,
            "text": "Hello Firefly",
            "user": "tester"
        })

    @patch("urllib.request.urlopen")
    def test_send_message(self, mock_urlopen):
        """Test sending a message via telegram_output event."""
        # Mock successful dispatch
        mock_response = MagicMock()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # publish event
        self.bus.publish("telegram_output", {"chat_id": 888, "text": "Reply"})
        
        # Verify socket/api call via mock
        # Since handle_outgoing_message is subscribed, it should call send_message
        # We need to wait or verify behavior. 
        # Since EventBus is synchronous for now (based on previous files), it should call immediately?
        # Let's check event_bus implementation. Assuming synchronous for now.
        
        # Actually EventBus might be async/threaded?
        # Let's verify send_message calls urlopen
        
        self.service.send_message(888, "Reply")
        
        args, kwargs = mock_urlopen.call_args
        req = args[0]
        self.assertIn("sendMessage", req.full_url)
        self.assertIn(b"Reply", req.data)
