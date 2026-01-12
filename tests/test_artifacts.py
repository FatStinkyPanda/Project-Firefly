from pathlib import Path
import json
import os
import shutil
import unittest

from agent_manager.core.artifact_service import ArtifactService

class TestArtifactService(unittest.TestCase):
    def setUp(self):
        self.test_root = Path("test_workspace")
        self.test_root.mkdir(exist_ok=True)
        self.service = ArtifactService(root_path=str(self.test_root))

    def tearDown(self):
        if self.test_root.exists():
            shutil.rmtree(self.test_root)

    def test_create_artifact(self):
        session_id = "test_session"
        artifact_type = "test_type"
        content = {"key": "value"}

        path = self.service.create_artifact(session_id, artifact_type, content)
        self.assertIsNotNone(path)
        self.assertTrue(os.path.exists(path))

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.assertEqual(data["session_id"], session_id)
            self.assertEqual(data["type"], artifact_type)
            self.assertEqual(data["content"], content)

    def test_export_session_log(self):
        session_id = "test_session_log"
        self.service.create_artifact(session_id, "thought", "I am thinking.")
        self.service.create_artifact(session_id, "command", {"cmd": "ls", "success": True})

        log_path = self.service.export_session_log(session_id)
        self.assertIsNotNone(log_path)
        self.assertTrue(os.path.exists(log_path))

        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("# Session Log: test_session_log", content)
            self.assertIn("THOUGHT", content)
            self.assertIn("I am thinking.", content)
            self.assertIn("COMMAND", content)

if __name__ == "__main__":
    unittest.main()
