import logging
import os
import urllib.parse
import urllib.request
import json
from typing import Dict, Any, Optional

logger = logging.getLogger("FireflySMSService")

class SMSService:
    """
    Service to handle SMS (Twilio/Generic Webhook) interactions.
    Processes incoming SMS via WebhookService events and sends responses.
    """
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        self.twilio_number = os.environ.get("TWILIO_NUMBER")
        
        # Subscribe to generic webhook events
        self.event_bus.subscribe("webhook_event", self.handle_incoming_webhook)
        # Subscribe to outgoing SMS requests
        self.event_bus.subscribe("sms_output", self.handle_outgoing_message)

    def handle_incoming_webhook(self, event_type: str, payload: Dict[str, Any]):
        """
        Check if a webhook payload is an SMS (e.g., from Twilio).
        Twilio sends form-encoded data, which our WebhookService might decode as a dict if it's JSON,
        or we might need to handle raw form data.
        """
        # Simple heuristic: Twilio payloads usually have 'From', 'To', and 'Body'
        if "Body" in payload and "From" in payload:
            text = payload.get("Body")
            from_number = payload.get("From")
            
            logger.info(f"Received SMS from {from_number}: {text}")
            
            sms_payload = {
                "type": "sms",
                "from": from_number,
                "text": text
            }
            # Publish as a dedicated sms_input for the Orchestrator
            self.event_bus.publish("sms_input", sms_payload)

    def handle_outgoing_message(self, event_type: str, payload: Dict[str, Any]):
        """Handle 'sms_output' events -> Send SMS via Twilio."""
        to_number = payload.get("to")
        text = payload.get("text")

        if to_number and text:
            self.send_sms(to_number, text)

    def send_sms(self, to_number: str, text: str):
        """Send an SMS using Twilio API (zero-dependency approach)."""
        if not self.twilio_sid or not self.twilio_auth_token or not self.twilio_number:
            logger.warning("Twilio credentials not set. SMS cannot be sent.")
            return

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"
        
        data = urllib.parse.urlencode({
            "To": to_number,
            "From": self.twilio_number,
            "Body": text
        }).encode("utf-8")
        
        # Basic Auth
        import base64
        auth_str = f"{self.twilio_sid}:{self.twilio_auth_token}"
        encoded_auth = base64.b64encode(auth_str.encode("ascii")).decode("ascii")
        
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Basic {encoded_auth}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                logger.info(f"SMS sent successfully: {result.get('sid')}")
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")

    def start(self):
        """Service startup logic."""
        logger.info("SMSService initialized and listening for webhook events.")

    def stop(self):
        """Service shutdown logic."""
        pass
