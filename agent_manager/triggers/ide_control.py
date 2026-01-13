from typing import Dict, Any
import json
import logging
import sys
import threading

logger = logging.getLogger("FireflyIDEControl")

class IDEControlService:
    """
    Service that listens to stdin for JSON commands from the VS Code main process.
    Enables bidirectional communication with the IDE UI.
    """
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.running = False
        self.thread = None

    def start(self):
        """Start the stdin listener thread."""
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, name="IDEControlListener")
        self.thread.daemon = True
        self.thread.start()
        logger.info("IDE Control Service started (listening on stdin).")

    def _listen_loop(self):
        """Continuously read lines from stdin and process as JSON commands."""
        while self.running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    command = json.loads(line)
                    self._process_command(command)
                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON command from IDE: {line}")
            except Exception as e:
                if self.running:
                    logger.error(f"Error in IDE control loop: {e}")
                break

    def _process_command(self, command: Dict[str, Any]):
        """Route the command to the event bus."""
        cmd_type = command.get("type")
        if not cmd_type:
            return

        logger.debug(f"Received command from IDE: {cmd_type}")

        # Publish to the event bus
        # The orchestrator should listen for these
        self.event_bus.publish(f"ide_{cmd_type}", command)

    def stop(self):
        """Stop the service."""
        self.running = False
        # stdin.readline is blocking, but setting running to false will
        # prevent further processing if it ever returns.
        logger.info("IDE Control Service stopped.")
