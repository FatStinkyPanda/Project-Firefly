"""
File System Watcher
===================
Background process for live semantic index updates.

Usage:
    python mcp.py watch           # Start watching
    python mcp.py watch --stop    # Stop watching
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, Optional
import hashlib
import json
import os
import sys
import time

from .utils import Console, find_python_files, find_project_root
import signal


# Try watchdog for efficient file watching
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


@dataclass
class WatcherState:
    """State of the file watcher."""
    pid_file: Path
    index_path: Path
    debounce_ms: int = 500
    save_interval_s: int = 30
    running: bool = False


class CodeChangeHandler:
    """Handles file changes for indexing."""

    def __init__(self, root: Path, state: WatcherState):
        self.root = root
        self.state = state
        self.pending_files: Set[Path] = set()
        self.last_change_time: float = 0
        self.file_hashes: Dict[str, str] = {}

    def on_modified(self, path: Path):
        """Handle file modification."""
        if not path.suffix == '.py':
            return

        # Check if file actually changed (not just touched)
        current_hash = self._get_file_hash(path)
        if self.file_hashes.get(str(path)) == current_hash:
            return

        self.file_hashes[str(path)] = current_hash
        self.pending_files.add(path)
        self.last_change_time = time.time()

    def _get_file_hash(self, path: Path) -> str:
        """Get hash of file contents."""
        try:
            with open(path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def process_pending(self) -> int:
        """Process pending files if debounce period passed."""
        if not self.pending_files:
            return 0

        # Check debounce
        elapsed_ms = (time.time() - self.last_change_time) * 1000
        if elapsed_ms < self.state.debounce_ms:
            return 0

        # Process files
        files = list(self.pending_files)
        self.pending_files.clear()

        Console.info(f"Updating index for {len(files)} files...")

        try:
            from .vector_store import VectorStore
            store = VectorStore(self.state.index_path)
            store.load()
            store.update(files)
            Console.ok(f"Index updated")
            return len(files)
        except Exception as e:
            Console.warn(f"Index update failed: {e}")
            return 0


if WATCHDOG_AVAILABLE:
    class WatchdogHandler(FileSystemEventHandler):
        """Watchdog event handler."""

        def __init__(self, change_handler: CodeChangeHandler):
            self.change_handler = change_handler

        def on_modified(self, event):
            if not event.is_directory:
                self.change_handler.on_modified(Path(event.src_path))

        def on_created(self, event):
            if not event.is_directory:
                self.change_handler.on_modified(Path(event.src_path))


def poll_watch(root: Path, state: WatcherState):
    """Polling-based file watcher (fallback)."""
    handler = CodeChangeHandler(root, state)
    last_save = time.time()

    # Initial scan
    Console.info("Initial file scan...")
    for path in find_python_files(root):
        handler.file_hashes[str(path)] = handler._get_file_hash(path)
    Console.ok(f"Tracking {len(handler.file_hashes)} files")

    Console.info(f"Watching {root} (polling mode)...")
    Console.info("Press Ctrl+C to stop")

    while state.running:
        # Check for changes
        for path in find_python_files(root):
            current_hash = handler._get_file_hash(path)
            if handler.file_hashes.get(str(path)) != current_hash:
                handler.on_modified(path)

        # Process pending
        handler.process_pending()

        # Periodic save
        if time.time() - last_save > state.save_interval_s:
            last_save = time.time()

        time.sleep(1)


def watchdog_watch(root: Path, state: WatcherState):
    """Watchdog-based efficient file watching."""
    handler = CodeChangeHandler(root, state)
    watchdog_handler = WatchdogHandler(handler)

    observer = Observer()
    observer.schedule(watchdog_handler, str(root), recursive=True)
    observer.start()

    Console.info(f"Watching {root} (watchdog mode)...")
    Console.info("Press Ctrl+C to stop")

    try:
        while state.running:
            handler.process_pending()
            time.sleep(0.5)
    finally:
        observer.stop()
        observer.join()


def start_watch(root: Path = None, background: bool = False):
    """Start the file watcher."""
    root = root or find_project_root() or Path.cwd()

    mcp_dir = root / '.mcp'
    mcp_dir.mkdir(exist_ok=True)

    state = WatcherState(
        pid_file=mcp_dir / 'watcher.pid',
        index_path=mcp_dir / 'vector_index',
        running=True
    )

    # Check if already running
    if state.pid_file.exists():
        try:
            pid = int(state.pid_file.read_text().strip())
            # Check if process exists
            os.kill(pid, 0)
            Console.warn(f"Watcher already running (PID {pid})")
            return 1
        except (ProcessLookupError, ValueError):
            state.pid_file.unlink()

    # Write PID
    state.pid_file.write_text(str(os.getpid()))

    # Handle shutdown
    def shutdown(signum, frame):
        Console.info("Stopping watcher...")
        state.running = False
        if state.pid_file.exists():
            state.pid_file.unlink()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        if WATCHDOG_AVAILABLE:
            watchdog_watch(root, state)
        else:
            poll_watch(root, state)
    finally:
        if state.pid_file.exists():
            state.pid_file.unlink()

    Console.ok("Watcher stopped")
    return 0


def stop_watch(root: Path = None):
    """Stop the file watcher."""
    root = root or find_project_root() or Path.cwd()
    pid_file = root / '.mcp' / 'watcher.pid'

    if not pid_file.exists():
        Console.warn("No watcher running")
        return 1

    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        Console.ok(f"Stopped watcher (PID {pid})")
        pid_file.unlink()
        return 0
    except ProcessLookupError:
        Console.warn("Watcher process not found")
        pid_file.unlink()
        return 1
    except Exception as e:
        Console.fail(f"Could not stop watcher: {e}")
        return 1


def get_watch_status(root: Path = None) -> Optional[int]:
    """Get watcher PID if running."""
    root = root or find_project_root() or Path.cwd()
    pid_file = root / '.mcp' / 'watcher.pid'

    if not pid_file.exists():
        return None

    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)  # Check if process exists
        return pid
    except (ProcessLookupError, ValueError):
        return None


def main():
    """CLI entry point."""
    Console.header("File Watcher")

    if WATCHDOG_AVAILABLE:
        Console.ok("watchdog available (efficient mode)")
    else:
        Console.warn("watchdog not installed, using polling")

    args = [a for a in sys.argv[1:] if not a.startswith('-')]

    if '--stop' in sys.argv:
        return stop_watch()

    if '--status' in sys.argv:
        pid = get_watch_status()
        if pid:
            Console.ok(f"Watcher running (PID {pid})")
        else:
            Console.info("Watcher not running")
        return 0

    # Start watching
    path = Path(args[0]) if args else None
    return start_watch(path)


if __name__ == "__main__":
    sys.exit(main())
