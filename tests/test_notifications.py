import unittest
from unittest.mock import MagicMock
from agent_manager.core.notification_service import NotificationService
from agent_manager.core.event_bus import EventBusService

class TestNotificationService(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBusService()
        self.service = NotificationService(self.event_bus)

    def test_notify_publishes_to_bus(self):
        # Mock subscribers
        mock_tg = MagicMock()
        mock_webhook = MagicMock()
        
        self.event_bus.subscribe("telegram_output", mock_tg)
        self.event_bus.subscribe("webhook_event", mock_webhook)
        
        self.service.notify("Test alert", priority="critical")
        
        # Verify Telegram call
        mock_tg.assert_called_once()
        payload_tg = mock_tg.call_args[0][1]
        self.assertEqual(payload_tg["text"], "[CRITICAL] Test alert")
        
        # Verify Webhook call
        mock_webhook.assert_called_once()
        payload_wh = mock_webhook.call_args[0][1]
        self.assertEqual(payload_wh["type"], "notification")
        self.assertEqual(payload_wh["data"]["priority"], "critical")

    def test_broadcast_trigger(self):
        # Trigger via broadcast event
        self.service.notify = MagicMock()
        self.event_bus.publish("broadcast_notification", {"text": "System update", "priority": "info"})
        
        self.service.notify.assert_called_once_with("System update", "info", None)

if __name__ == "__main__":
    unittest.main()
