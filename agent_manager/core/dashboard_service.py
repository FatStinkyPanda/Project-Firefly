import logging
import os
import time
import threading
from typing import Dict, Any, List

logger = logging.getLogger("FireflyDashboard")

class DashboardService:
    """
    Real-time CLI dashboard for Project-Firefly.
    Aggregates events, usage, and peer status.
    """
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.peers = {}
        self.usage = {"tokens": 0, "cost": 0.0, "completions": 0}
        self.last_events = []
        self.is_running = False
        self._render_thread = None

    def start(self):
        self.is_running = True
        self.event_bus.subscribe("peer_joined", self._on_peer_joined)
        self.event_bus.subscribe("peer_left", self._on_peer_left)
        self.event_bus.subscribe("usage_report", self._on_usage_report)
        self.event_bus.subscribe("system_event", self._on_event)
        self.event_bus.subscribe("telegram_input", self._on_event)
        self.event_bus.subscribe("webhook_event", self._on_event)
        
        self._render_thread = threading.Thread(target=self._render_loop, daemon=True)
        self._render_thread.start()
        logger.info("DashboardService started.")

    def stop(self):
        self.is_running = False
        if self._render_thread:
            self._render_thread.join(timeout=1)

    def _on_peer_joined(self, event_type, payload):
        self.peers[payload.get("identity")] = payload

    def _on_peer_left(self, event_type, payload):
        identity = payload.get("identity")
        if identity in self.peers:
            del self.peers[identity]

    def _on_usage_report(self, event_type, payload):
        self.usage["tokens"] += payload.get("total_tokens", 0)
        self.usage["cost"] += payload.get("cost_usd", 0.0)
        self.usage["completions"] += 1

    def _on_event(self, event_type, payload):
        timestamp = time.strftime("%H:%M:%S")
        self.last_events.append(f"[{timestamp}] {event_type}")
        if len(self.last_events) > 8:
            self.last_events.pop(0)

    def _render_loop(self):
        while self.is_running:
            self._render()
            time.sleep(5) # Refresh every 5 seconds

    def _render(self):
        # Use terminal escape codes to clear and home on supported terminals, 
        # but for simplicity and compatibility with standard logs, we'll just print a headered block.
        # os.system('cls' if os.name == 'nt' else 'clear') 
        
        output = []
        output.append("\n" + "="*50)
        output.append("🦉 PROJECT-FIREFLY AGENT HUB DASHBOARD")
        output.append("="*50)
        
        # 1. Resource Usage
        output.append(f"\n[RESOURCE USAGE]")
        output.append(f"  - Total Tokens: {self.usage['tokens']}")
        output.append(f"  - Total Cost:   ${self.usage['cost']:.4f}")
        output.append(f"  - Completions:  {self.usage['completions']}")
        
        # 2. Peer Registry
        output.append(f"\n[PEER REGISTRY] ({len(self.peers)} active)")
        for p_id, p_data in self.peers.items():
            output.append(f"  - {p_id} (@{p_data.get('hostname')}) | Status: {p_data.get('status')}")
            
        # 3. Recent Activity
        output.append(f"\n[RECENT ACTIVITY]")
        if not self.last_events:
            output.append("  (Waiting for events...)")
        for ev in reversed(self.last_events):
            output.append(f"  {ev}")
            
        output.append("="*50 + "\n")
        
        # In a real CLI we would sys.stdout.write, but for logs:
        print("\n".join(output))
