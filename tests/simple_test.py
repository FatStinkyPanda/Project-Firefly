from pathlib import Path
import os
import shutil
import time

from agent_manager.core.event_bus import EventBusService
from agent_manager.core.git_service import GitMonitoringService

# Setup
tmp_dir = Path("simple_git_test")
if tmp_dir.exists():
    shutil.rmtree(tmp_dir)
tmp_dir.mkdir()

print(f"Initializing git in {tmp_dir}...")
os.system(f'cd {tmp_dir} && git init && git config user.email "test@example.com" && git config user.name "Test User"')

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
os.system(f'cd {tmp_dir} && git checkout -b feature/ai-git')
time.sleep(2)

print("--- Creating commit ---")
with open(tmp_dir / "firefly.txt", "w") as f:
    f.write("Firefly is watching.")
os.system(f'cd {tmp_dir} && git add firefly.txt && git commit -m "feat: firefly observation"')
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
