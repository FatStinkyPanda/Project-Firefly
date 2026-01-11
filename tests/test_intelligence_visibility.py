from unittest.mock import MagicMock
import time
import unittest

from agent_manager.core.dashboard_service import DashboardService
from agent_manager.core.event_bus import EventBusService
from agent_manager.core.session_manager import SessionManager

class TestIntelligenceVisibility(unittest.TestCase):
    def setUp(self):
        self.bus = EventBusService()
        self.sessions = SessionManager(max_history=5)
        self.dashboard = DashboardService(event_bus=self.bus)

    def test_session_history(self):
        """Verify that SessionManager tracks and formats history correctly."""
        sid = "test_user"
        self.sessions.add_message(sid, "user", "Hello")
        self.sessions.add_message(sid, "assistant", "Hi there!")

        history = self.sessions.get_history(sid)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")

        formatted = self.sessions.format_for_ai(sid)
        self.assertIn("USER: Hello", formatted)
        self.assertIn("ASSISTANT: Hi there!", formatted)

    def test_session_sliding_window(self):
        """Verify max history limits."""
        sid = "limit_test"
        for i in range(10):
            self.sessions.add_message(sid, "user", f"Msg {i}")

        history = self.sessions.get_history(sid)
        self.assertEqual(len(history), 5) # Max history is 5
        self.assertEqual(history[0]["content"], "Msg 5")

    def test_dashboard_aggregation(self):
        """Verify that DashboardService correctly catches events."""
        self.dashboard.start()

        # 1. Test Usage
        self.bus.publish("usage_report", {"total_tokens": 100, "cost_usd": 0.05})
        self.assertEqual(self.dashboard.usage["tokens"], 100)
        self.assertEqual(self.dashboard.usage["cost"], 0.05)

        # 2. Test Peers
        self.bus.publish("peer_joined", {"identity": "Panda", "hostname": "local", "status": "idle"})
        self.assertIn("Panda", self.dashboard.peers)

        self.bus.publish("peer_left", {"identity": "Panda"})
        self.assertNotIn("Panda", self.dashboard.peers)

        # 3. Test Activity Log
        self.bus.publish("system_event", {"type": "test"})
        self.assertTrue(any("system_event" in ev for ev in self.dashboard.last_events))

        self.dashboard.stop()

if __name__ == "__main__":
    unittest.main()
