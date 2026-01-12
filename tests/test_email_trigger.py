import unittest
from unittest.mock import MagicMock, patch
from agent_manager.triggers.email import EmailService
from agent_manager.core.event_bus import EventBusService

class TestEmailService(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBusService()
        with patch.dict('os.environ', {'EMAIL_USER': 'test@firefly.io', 'EMAIL_PASS': 'pass'}):
            self.service = EmailService(self.event_bus)

    def test_handle_outgoing_message_triggers_send(self):
        self.service.send_email = MagicMock()
        
        payload = {
            "to": "developer@firefly.io",
            "subject": "Firefly Test",
            "text": "Hello from agent!"
        }
        self.event_bus.publish("email_output", payload)
        
        self.service.send_email.assert_called_once_with(
            "developer@firefly.io", "Firefly Test", "Hello from agent!"
        )

    @patch('imaplib.IMAP4_SSL')
    def test_check_emails_matches_firefly_subject(self, mock_imap):
        # Mock IMAP connection and results
        instance = mock_imap.return_value
        instance.login.return_value = ('OK', [b'Logged in'])
        instance.select.return_value = ('OK', [b'1'])
        instance.search.return_value = ('OK', [b'1'])
        
        # Mock a raw email message
        raw_email = b"Subject: FIREFLY: Help me\nFrom: user@test.com\n\nWhat is your purpose?"
        instance.fetch.return_value = ('OK', [[None, raw_email]])
        
        # Subscribe to event to verify capture
        mock_handler = MagicMock()
        self.event_bus.subscribe("email_input", mock_handler)
        
        self.service._check_emails()
        
        mock_handler.assert_called_once()
        payload = mock_handler.call_args[0][1]
        self.assertEqual(payload["from"], "user@test.com")
        self.assertEqual(payload["subject"], "FIREFLY: Help me")
        self.assertEqual(payload["text"], "What is your purpose?")

if __name__ == "__main__":
    unittest.main()
