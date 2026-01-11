import json
import logging
import os
import socket
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("FireflyPeerDiscovery")

class PeerDiscoveryService:
    """
    Enables detection and communication with other Firefly/MCP agents.
    Uses the NSync shared directory for presence and messaging.
    """
    def __init__(self, event_bus, nsync_path: Optional[str] = None):
        self.event_bus = event_bus
        # Default NSync path for Windows
        self.nsync_path = Path(nsync_path or os.environ.get("NSYNC_PATH", "C:/Users/dbiss/Desktop/Projects/_BLANK_/NSync"))
        self.comms_dir = self.nsync_path / ".nsync_agents"
        self.mailbox_dir = self.comms_dir / "messages"
        
        self.hostname = socket.gethostname()
        self.identity = os.environ.get("AGENT_IDENTITY", self.hostname)
        
        self.peers = {} # hostname -> presence_data
        self.running = False
        self._poll_thread = None

        self._ensure_directories()

    def _ensure_directories(self):
        try:
            self.comms_dir.mkdir(parents=True, exist_ok=True)
            self.mailbox_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create comms directories: {e}")

    def start(self):
        if self.running: return
        self.running = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        logger.info(f"PeerDiscoveryService started. Identity: {self.identity}")

    def stop(self):
        self.running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=2)
        logger.info("PeerDiscoveryService stopped.")

    def _poll_loop(self):
        while self.running:
            self.refresh()
            # Sleep in small increments to be responsive to stop()
            for _ in range(100):
                if not self.running: break
                time.sleep(0.1)

    def refresh(self):
        """Synchronously refresh presence, peers, and mailbox."""
        self._update_presence()
        self._discover_peers()
        self._check_mailbox()

    def _update_presence(self, status="active", task="monitoring"):
        presence_file = self.comms_dir / f"{self.hostname}.json"
        data = {
            "hostname": self.hostname,
            "identity": self.identity,
            "timestamp": time.time(),
            "status": status,
            "current_task": task,
            "last_seen": time.ctime()
        }
        try:
            with open(presence_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to update presence: {e}")

    def _discover_peers(self):
        current_time = time.time()
        found_peers = []
        
        try:
            for f in self.comms_dir.glob("*.json"):
                if f.stem == self.hostname: continue
                
                try:
                    with open(f, "r") as pf:
                        data = json.load(pf)
                        peer_id = data.get("identity", f.stem)
                        
                        # Check pulse (stale if > 120s)
                        if current_time - data.get("timestamp", 0) < 120:
                            if peer_id not in self.peers:
                                logger.info(f"New peer discovered: {peer_id}")
                                self.event_bus.publish("peer_joined", data)
                            self.peers[peer_id] = data
                            found_peers.append(peer_id)
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Error discovering peers: {e}")

        # Detect left peers
        to_remove = []
        for peer_id in self.peers:
            if peer_id not in found_peers:
                logger.info(f"Peer left or stale: {peer_id}")
                self.event_bus.publish("peer_left", {"identity": peer_id})
                to_remove.append(peer_id)
        
        for p in to_remove:
            del self.peers[p]

    def _check_mailbox(self):
        messages = []
        try:
            # Files match: {recipient}_{sender}_{id}.json
            search_pattern = f"{self.identity}_*.json"
            for f in self.mailbox_dir.glob(search_pattern):
                try:
                    with open(f, "r") as mf:
                        msg = json.load(mf)
                        messages.append(msg)
                    f.unlink() # Mark as read
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Error checking mailbox: {e}")

        for msg in messages:
            logger.info(f"Received message from {msg.get('from')}: {msg.get('type')}")
            self.event_bus.publish("peer_message", msg)

    def send_message(self, recipient: str, msg_type: str, content: dict):
        msg_id = int(time.time() * 1000)
        msg_file = self.mailbox_dir / f"{recipient}_{self.identity}_{msg_id}.json"
        
        payload = {
            "id": msg_id,
            "from": self.identity,
            "to": recipient,
            "type": msg_type,
            "content": content,
            "timestamp": time.time()
        }
        
        try:
            with open(msg_file, "w") as f:
                json.dump(payload, f, indent=2)
            logger.info(f"Message sent to {recipient}: {msg_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {recipient}: {e}")
            return False
