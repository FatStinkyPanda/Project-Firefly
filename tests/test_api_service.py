import unittest
import json
import urllib.request
import time
import shutil
from pathlib import Path
from unittest.mock import MagicMock
from agent_manager.core.api_service import APIService
from agent_manager.core.artifact_service import ArtifactService
from agent_manager.core.event_bus import EventBusService

class TestAPIService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_root = Path("test_api_root")
        if cls.test_root.exists():
            shutil.rmtree(cls.test_root)
        cls.test_root.mkdir()
        
        cls.bus = EventBusService()
        cls.artifacts = ArtifactService(root_path=str(cls.test_root))
        cls.mock_client = MagicMock()
        cls.mock_client.usage_ledger = {"total_cost_usd": 0.05}
        cls.api = APIService(cls.bus, cls.artifacts, model_client=cls.mock_client, port=5051)
        cls.api.start()
        
        # Give it a moment to start
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.api.stop()
        if cls.test_root.exists():
            shutil.rmtree(cls.test_root)

    def test_list_sessions_empty(self):
        with urllib.request.urlopen("http://localhost:5051/api/artifacts") as response:
            data = json.loads(response.read().decode())
            self.assertIsInstance(data, list)

    def test_artifacts_flow(self):
        session_id = "test_session_123"
        self.artifacts.create_artifact(session_id, "thought", "I am thinking")
        
        # 1. List sessions
        with urllib.request.urlopen("http://localhost:5051/api/artifacts") as response:
            sessions = json.loads(response.read().decode())
            self.assertIn(session_id, sessions)
            
        # 2. List artifacts in session
        with urllib.request.urlopen(f"http://localhost:5051/api/artifacts/{session_id}") as response:
            arts = json.loads(response.read().decode())
            self.assertEqual(len(arts), 1)
            self.assertEqual(arts[0]["type"], "thought")
            filename = arts[0]["name"]
            
        # 3. Get specific artifact
        with urllib.request.urlopen(f"http://localhost:5051/api/artifacts/{session_id}/{filename}") as response:
            content = json.loads(response.read().decode())
            self.assertEqual(content["content"], "I am thinking")

    def test_status_endpoint(self):
        with urllib.request.urlopen("http://localhost:5051/api/status") as response:
            data = json.loads(response.read().decode())
            self.assertEqual(data["status"], "online")
            self.assertIn("usage_api", data["capabilities"])

    def test_usage_endpoint(self):
        with urllib.request.urlopen("http://localhost:5051/api/usage") as response:
            data = json.loads(response.read().decode())
            self.assertEqual(data["total_cost_usd"], 0.05)

if __name__ == "__main__":
    unittest.main()
