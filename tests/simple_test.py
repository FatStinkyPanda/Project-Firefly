from pathlib import Path
import shutil
import subprocess
import time

from agent_manager.core.event_bus import EventBusService
from agent_manager.core.git_service import GitMonitoringService

# Setup
tmp_dir = Path("simple_git_test")
if tmp_dir.exists():
    shutil.rmtree(tmp_dir)
tmp_dir.mkdir()

print(f"Initializing git in {tmp_dir}...")
subprocess.run(['git', 'init'], cwd=tmp_dir, check=True, capture_output=True)
subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=tmp_dir, check=True, capture_output=True)
subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=tmp_dir, check=True, capture_output=True)

bus = EventBusService()
def log_event(t, d):
    print(f"EVENT DETECTED: {d['type']} - {d['data']}")
bus.subscribe("git_event", log_event)

from agent_manager.core import git_service
git_service.HAS_WATCHDOG = False

monitor = GitMonitoringService(bus, root_path=str(tmp_dir))
monitor.start()

time.sleep(1)

print("--- Creating branch ---")
subprocess.run(['git', 'checkout', '-b', 'feature/ai-git'], cwd=tmp_dir, check=True, capture_output=True)
time.sleep(2)

print("--- Creating commit ---")
with open(tmp_dir / "firefly.txt", "w") as f:
    f.write("Firefly is watching.")
subprocess.run(['git', 'add', 'firefly.txt'], cwd=tmp_dir, check=True, capture_output=True)
subprocess.run(['git', 'commit', '-m', 'feat: firefly observation'], cwd=tmp_dir, check=True, capture_output=True)
time.sleep(2)

monitor.stop()
print("Cleanup...")
# Wait a bit for file handles to release
time.sleep(1)
try:
    shutil.rmtree(tmp_dir)
    print("Cleanup successful.")
except Exception as e:
    print(f"Cleanup failed (expected on Windows sometimes): {e}")
