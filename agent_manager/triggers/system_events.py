from pathlib import Path
from threading import Thread
from typing import Set
import logging
import os
import time

logger = logging.getLogger("WorkspaceMonitor")

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

class WorkspaceMonitoringService:
    """
    Monitors the project workspace for file changes and system events.
    Fires 'system_event' on the EventBus.
    """
    def __init__(self, event_bus, root_path: str = "."):
        self.event_bus = event_bus
        self.root_path = Path(root_path).resolve()
        self.is_running = False
        self.ignored_dirs = {'.git', '.mcp', '__pycache__', 'node_modules', 'vscode'}
        self.relevant_extensions = {'.py', '.js', '.ts', '.md', '.json', '.txt'}
        self._thread = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True

        if HAS_WATCHDOG:
            self._start_watchdog()
        else:
            self._start_polling()

        logger.info(f"Workspace Monitoring started at {self.root_path} ({'watchdog' if HAS_WATCHDOG else 'polling'} mode)")

    def stop(self):
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=1)
        logger.info("Workspace Monitoring stopped.")

    def _start_watchdog(self):
        class Handler(FileSystemEventHandler):
            def __init__(self, service):
                self.service = service

            def on_modified(self, event):
                if not event.is_directory:
                    self.service._handle_change(event.src_path)

            def on_created(self, event):
                if not event.is_directory:
                    self.service._handle_change(event.src_path)

        self.observer = Observer()
        self.observer.schedule(Handler(self), str(self.root_path), recursive=True)
        self.observer.start()

    def _start_polling(self):
        def poll_loop():
            file_states = {} # path -> mtime
            while self.is_running:
                try:
                    for path in self.root_path.rglob('*'):
                        if any(part in self.ignored_dirs for part in path.parts):
                            continue
                        if path.suffix not in self.relevant_extensions:
                            continue

                        mtime = path.stat().st_mtime
                        if str(path) not in file_states:
                            file_states[str(path)] = mtime
                        elif file_states[str(path)] != mtime:
                            file_states[str(path)] = mtime
                            self._handle_change(str(path))
                except Exception as e:
                    logger.error(f"Polling error: {e}")

                time.sleep(2) # Poll every 2 seconds

        self._thread = Thread(target=poll_loop, daemon=True)
        self._thread.start()

    def _handle_change(self, path: str):
        rel_path = os.path.relpath(path, self.root_path)
        if any(part in self.ignored_dirs for part in Path(rel_path).parts):
            return

        logger.info(f"File change detected: {rel_path}")
        self.event_bus.publish("system_event", {
            "type": "file_change",
            "path": rel_path,
            "timestamp": time.time()
        })
