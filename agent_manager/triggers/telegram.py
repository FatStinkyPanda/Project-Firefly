import os
import time
import json
import logging
import threading
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional, Dict, Any

logger = logging.getLogger("FireflyTelegramService")

class TelegramService:
    """
    Service to handle Telegram Bot API interactions.
    Polls for updates and sends messages.
    """
    BASE_URL = "https://api.telegram.org/bot"

    def __init__(self, event_bus, token: Optional[str] = None):
        self.event_bus = event_bus
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.is_running = False
        self.last_update_id = 0
        self.polling_thread = None
        
        # Subscribe to outgoing messages to send them back to Telegram
        self.event_bus.subscribe("telegram_output", self.handle_outgoing_message)

    def start(self):
        """Start the polling loop in a background thread."""
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not set. TelegramService will not run.")
            return

        self.is_running = True
        self.polling_thread = threading.Thread(target(self._poll_loop), daemon=True)
        self.polling_thread.start()
        logger.info("TelegramService started polling.")

    def stop(self):
        """Stop the polling loop."""
        self.is_running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=1.0)
        logger.info("TelegramService stopped.")

    def _poll_loop(self):
        """Internal loop to check for updates."""
        while self.is_running:
            try:
                self._check_updates()
            except Exception as e:
                logger.error(f"Error in Telegram polling loop: {e}")
                time.sleep(5) # Backoff on error
            
            time.sleep(1) # Poll interval

    def _check_updates(self):
        """Call getUpdates API."""
        url = f"{self.BASE_URL}{self.token}/getUpdates?offset={self.last_update_id + 1}&timeout=30"
        
        try:
            with urllib.request.urlopen(url) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if not result.get("ok"):
                    logger.error(f"Telegram API Error: {result}")
                    return

                updates = result.get("result", [])
                for update in updates:
                    self.last_update_id = update["update_id"]
                    self._process_update(update)

        except urllib.error.URLError as e:
            # Network issue or timeout (normal for long polling)
            pass

    def _process_update(self, update: Dict[str, Any]):
        """Process a single update and publish event."""
        message = update.get("message")
        if not message:
            return

        chat_id = message.get("chat", {}).get("id")
        text = message.get("text")
        username = message.get("from", {}).get("username")

        if text:
            logger.info(f"Received Telegram message from {username}: {text}")
            payload = {
                "type": "message",
                "chat_id": chat_id,
                "text": text,
                "user": username
            }
            # Publish to Event Bus
            self.event_bus.publish("telegram_input", payload)

    def handle_outgoing_message(self, payload: Dict[str, Any]):
        """Handle 'telegram_output' events -> Send message to Telegram."""
        chat_id = payload.get("chat_id")
        text = payload.get("text")
        
        if chat_id and text:
            self.send_message(chat_id, text)

    def send_message(self, chat_id: int, text: str):
        """Send a text message to a chat."""
        if not self.token:
            return

        url = f"{self.BASE_URL}{self.token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text
        }
        
        headers = {'Content-Type': 'application/json'}
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)

        try:
            with urllib.request.urlopen(req) as response:
                pass # Success
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
