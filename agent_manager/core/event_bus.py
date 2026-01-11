from threading import Lock
from typing import Callable, Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FireflyEventBus")

class EventBusService:
    """
    Central event bus for the agent system.
    Follows a simple Publish-Subscribe pattern.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = Lock()

    def subscribe(self, event_type: str, callback: Callable[[Any], None]):
        """Subscribe a callback function to a specific event type."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
        logger.info(f"Subscribed to event: {event_type}")

    def publish(self, event_type: str, data: Any):
        """Publish an event to all subscribers."""
        with self._lock:
            if event_type not in self._subscribers:
                # No subscribers for this event
                return

            subscribers = self._subscribers[event_type][:] # Copy list to avoid modification issues during iteration

        logger.info(f"Publishing event: {event_type}")
        for callback in subscribers:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in subscriber callback for {event_type}: {e}")
