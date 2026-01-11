from pathlib import Path
import os
import shutil
import subprocess
import time
import unittest

from agent_manager.core.event_bus import EventBusService
from agent_manager.core.git_service import GitMonitoringService

class TestGitMonitoring(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path("tmp_test_git")
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir)
        self.tmp_dir.mkdir()

        # Initialize git repo in tmp_dir
        subprocess.run(['git', 'init'], cwd=self.tmp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.tmp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.tmp_dir, check=True, capture_output=True)

        self.bus = EventBusService()
        self.events = []
        def log_event(t, d):
            print(f"EVENT: {d['type']} - {d.get('data')}")
            self.events.append(d)
        self.bus.subscribe("git_event", log_event)

        from agent_manager.core import git_service
        git_service.HAS_WATCHDOG = False # Force polling for test stability

        self.monitor = GitMonitoringService(self.bus, root_path=str(self.tmp_dir))
        self.monitor.start()

    def tearDown(self):
        self.monitor.stop()
        shutil.rmtree(self.tmp_dir)

    def test_detection(self):
        try:
            print("--- Branch Checkout ---")
            subprocess.run(['git', 'checkout', '-b', 'test-branch'], cwd=self.tmp_dir, check=True, capture_output=True)
            time.sleep(2)

            checkout_branches = [e['data']['branch'] for e in self.events if e['type'] == 'branch_checkout']
            print(f"Detected branches: {checkout_branches}")
            self.assertIn('test-branch', checkout_branches)

            print("--- Git Commit ---")
            with open(self.tmp_dir / "test.txt", "w") as f:
                f.write("test content")
            subprocess.run(['git', 'add', 'test.txt'], cwd=self.tmp_dir, check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'test commit'], cwd=self.tmp_dir, check=True, capture_output=True)
            time.sleep(2)

            commit_events = [e for e in self.events if e['type'] == 'commit_detected']
            print(f"Detected commits: {[e['data']['branch'] for e in commit_events]}")
            self.assertTrue(len(commit_events) > 0)
        except Exception as e:
            print(f"TEST ERROR: {e}")
            raise e

if __name__ == "__main__":
    unittest.main()
