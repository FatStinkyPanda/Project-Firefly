from pathlib import Path
from threading import Thread
import logging
import os
import time

logger = logging.getLogger("GitMonitor")

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

class GitMonitoringService:
    """
    Monitors the .git directory for state changes (branches, commits, merges).
    Fires 'git_event' on the EventBus.
    """
    def __init__(self, event_bus, root_path: str = "."):
        self.event_bus = event_bus
        self.root_path = Path(root_path).resolve()
        self.git_path = self.root_path / ".git"
        self.is_running = False
        self._thread = None
        self._observer = None

    def start(self):
        if not self.git_path.exists():
            logger.warning(f"No .git directory found at {self.root_path}. Git monitoring disabled.")
            return

        if self.is_running:
            return
        self.is_running = True

        if HAS_WATCHDOG:
            self._start_watchdog()
        else:
            self._start_polling()

        logger.info(f"Git Monitoring started at {self.git_path}")

    def stop(self):
        self.is_running = False
        if self._observer:
            self._observer.stop()
            self._observer.join()
        if self._thread:
            self._thread.join(timeout=1)
        logger.info("Git Monitoring stopped.")

    def _start_watchdog(self):
        class GitHandler(FileSystemEventHandler):
            def __init__(self, service):
                self.service = service

            def on_modified(self, event):
                self.service._process_event(event.src_path)

            def on_created(self, event):
                self.service._process_event(event.src_path)

            def on_deleted(self, event):
                self.service._process_event(event.src_path)

        self._observer = Observer()
        # Monitor HEAD and refs
        self._observer.schedule(GitHandler(self), str(self.git_path / "HEAD"), recursive=False)
        self._observer.schedule(GitHandler(self), str(self.git_path / "refs"), recursive=True)
        if (self.git_path / "index").exists():
             self._observer.schedule(GitHandler(self), str(self.git_path / "index"), recursive=False)

        self._observer.start()

    def _start_polling(self):
        def poll_loop():
            last_states = {} # path -> mtime
            paths_to_watch = [
                self.git_path / "HEAD",
                self.git_path / "refs"
            ]
            while self.is_running:
                try:
                    for root_p in paths_to_watch:
                        if not root_p.exists(): continue

                        if root_p.is_file():
                            mtime = root_p.stat().st_mtime
                            if str(root_p) not in last_states or last_states[str(root_p)] != mtime:
                                last_states[str(root_p)] = mtime
                                self._process_event(str(root_p))
                        else:
                            for p in root_p.rglob('*'):
                                if p.is_file():
                                    mtime = p.stat().st_mtime
                                    if str(p) not in last_states or last_states[str(p)] != mtime:
                                        last_states[str(p)] = mtime
                                        self._process_event(str(p))
                except Exception as e:
                    logger.error(f"Git polling error: {e}")
                time.sleep(1)

        self._thread = Thread(target=poll_loop, daemon=True)
        self._thread.start()

    def _process_event(self, path: str):
        path = Path(path)
        rel_path = path.relative_to(self.git_path)

        event_type = "unknown"
        data = {"path": str(rel_path)}

        if rel_path.name == "HEAD":
            event_type = "branch_checkout"
            # Read current branch
            try:
                content = path.read_text().strip()
                if content.startswith("ref: refs/heads/"):
                    data["branch"] = content.replace("ref: refs/heads/", "")
                else:
                    data["branch"] = "DETACHED"
                    data["commit"] = content
            except: pass
        elif "refs/heads/" in str(rel_path):
            event_type = "commit_detected"
            data["branch"] = rel_path.name
            try:
                data["commit"] = path.read_text().strip()
            except: pass
        elif "refs/remotes/" in str(rel_path):
            event_type = "remote_update"
            data["remote_path"] = str(rel_path)
        elif rel_path.name == "index":
            event_type = "index_change"
        elif rel_path.name == "MERGE_HEAD":
            event_type = "merge_state_change"

        logger.info(f"Git event detected: {event_type} - {data}")
        self.event_bus.publish("git_event", {
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        })
