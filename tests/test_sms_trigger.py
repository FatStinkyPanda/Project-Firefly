from unittest.mock import MagicMock, patch
import unittest

from agent_manager.core.event_bus import EventBusService
from agent_manager.triggers.sms import SMSService

class TestSMSService(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBusService()
        with patch.dict('os.environ', {
            'TWILIO_ACCOUNT_SID': 'AC_test',
            'TWILIO_AUTH_TOKEN': 'token_test',
            'TWILIO_NUMBER': '+1234567890'
        }):
            self.service = SMSService(self.event_bus)

    def test_handle_incoming_webhook_as_sms(self):
        # Mock payload as if it came from Twilio form data (parsed as dict)
        payload = {
            "From": "+1987654321",
            "To": "+1234567890",
            "Body": "Status check"
        }

        mock_handler = MagicMock()
        self.event_bus.subscribe("sms_input", mock_handler)

        self.event_bus.publish("webhook_event", payload)

        mock_handler.assert_called_once()
        processed = mock_handler.call_args[0][1]
        self.assertEqual(processed["text"], "Status check")
        self.assertEqual(processed["from"], "+1987654321")

    @patch('urllib.request.urlopen')
    def test_send_sms_calls_api(self, mock_urlopen):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"sid": "SM_test"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        self.service.send_sms("+1987654321", "Agent response")

        # Verify it attempted to call Twilio
        args, kwargs = mock_urlopen.call_args
        req = args[0]
        self.assertIn("api.twilio.com", req.full_url)
        self.assertEqual(req.get_method(), "POST")

if __name__ == "__main__":
    unittest.main()
