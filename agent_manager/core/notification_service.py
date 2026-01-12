from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger("FireflyNotificationService")

class NotificationService:
    """
    Unified notification hub for Project-Firefly.
    Routes messages to Telegram, Webhooks, and internal Event Bus.
    """
    def __init__(self, event_bus, config_service=None):
        self.event_bus = event_bus
        self.config_service = config_service

        # Subscribe to internal broadcasts
        self.event_bus.subscribe("broadcast_notification", self.on_broadcast)

    def notify(self, message: str, priority: str = "info", metadata: Optional[Dict[str, Any]] = None):
        """
        Send a notification to all active channels.
        """
        logger.info(f"[{priority.upper()}] Notification: {message}")

        payload = {
            "text": message,
            "priority": priority,
            "metadata": metadata or {}
        }

        # 1. Alert via EventBus (Triggers Telegram, Webhooks etc)
        # We use a broad chat_id for telegram if not specified
        tg_payload = {
            "text": f"[{priority.upper()}] {message}"
        }
        # If we have a default chat ID in env, TelegramService will handle it,
        # but here we can explicitly try to find one.
        self.event_bus.publish("telegram_output", tg_payload)
        self.event_bus.publish("webhook_event", {"type": "notification", "data": payload})

    def on_broadcast(self, event_type: str, payload: Dict[str, Any]):
        """Handler for internal broadcast events."""
        text = payload.get("text")
        prio = payload.get("priority", "info")
        if text:
            self.notify(text, prio, payload.get("metadata"))
