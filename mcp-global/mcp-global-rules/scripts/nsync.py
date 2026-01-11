#!/usr/bin/env python3
"""
MCP NSync Module
Provides real-time cross-device synchronization and remote execution.
"""

from pathlib import Path
from typing import List, Optional
import os
import subprocess
import sys
import time

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    Observer = None
    FileSystemEventHandler = object

# NSync Configuration
WINDOWS_NSYNC = Path("C:/Users/dbiss/Desktop/Projects/_BLANK_/NSync")
LINUX_NSYNC = Path("/home/p4nd4pr0t0c01/Projects/NSync")

def get_remote_peer():
    import socket
    host = socket.gethostname()
    if host.lower() == "wizardpanda":
        return "quasar"
    return "wizardpanda"

REMOTE_USER = "p4nd4pr0t0c01"

class NSyncHandler(FileSystemEventHandler):
    """Handles file system events and triggers git sync."""
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.last_sync = 0
        self.debounce = 2 # Seconds

    def on_any_event(self, event):
        if event.is_directory or ".git" in event.src_path:
            return

        now = time.time()
        if now - self.last_sync > self.debounce:
            self.sync()
            self.last_sync = now

    def sync(self):
        """Perform a git sync cycle."""
        print(f"[NSYNC] Change detected. Syncing...")

        # [NEW] Ensure rules links exist in all projects before sync
        self.ensure_rules_links()

        try:
            os.chdir(self.repo_path)
            # Add and commit
            subprocess.run(["git", "add", "-A"], capture_output=True)
            subprocess.run(["git", "commit", "-m", "nsync: auto-sync"], capture_output=True)

            # Pull with rebase to handle conflicts cleanly
            subprocess.run(["git", "pull", "--rebase", get_remote_peer(), "master"], capture_output=True)

            # Push to peer
            subprocess.run(["git", "push", get_remote_peer(), "master"], capture_output=True)
            print(f"[NSYNC] Sync complete.")
        except Exception as e:
            print(f"[FAIL] Sync failed: {e}")

    def ensure_rules_links(self):
        """Iterate through all projects and ensure mcp-global-rules is linked."""
        mcp_source = Path("C:/Users/dbiss/Desktop/Projects/_BLANK_/mcp-global-rules") if os.name == 'nt' else Path("/home/p4nd4pr0t0c01/Projects/mcp-global-rules")

        for item in self.repo_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                target = item / "mcp-global-rules"

                # If it's a real directory (not a link), remove it to make way for the link
                if target.exists() and not target.is_symlink():
                    if os.name != 'nt': # Extra check for Linux directory sync issue
                         # Only remove if it's not a junction/symlink
                         import shutil
                         try:
                             if target.is_dir() and not target.is_symlink():
                                 shutil.rmtree(target)
                         except:
                             pass

                if not target.exists():
                    print(f"[NSYNC] Creating rules link for {item.name}...")
                    try:
                        if os.name == 'nt':
                            subprocess.run(["cmd", "/c", "mklink", "/J", str(target), str(mcp_source)], check=True, capture_output=True)
                        else:
                            os.symlink(mcp_source, target)
                    except:
                        pass

def get_nsync_path() -> Path:
    """Determine the local NSync path based on OS."""
    if os.name == 'nt':
        return WINDOWS_NSYNC
    return LINUX_NSYNC

def show_help():
    print("MCP NSync: Real-time synchronization and remote execution")
    print("Usage: mcp nsync <command> [args]")
    print("\nCommands:")
    print("  watch               Start the real-time sync service")
    print("  status              Check sync status and peer connectivity")
    print("  run <file>          Sync and execute a file on wizardpanda")
    print("  sync                Perform a manual sync cycle")
    print("  setup               Install Git hooks for sync automation")
    print("  init-project <name> Initialize a new project folder with MCP links")

def init_project(name: str):
    """Initialize a sub-project within NSync with MCP links."""
    nsync_path = get_nsync_path()
    project_path = nsync_path / name

    if project_path.exists():
        print(f"[FAIL] Project {name} already exists at {project_path}")
        return 1

    project_path.mkdir(parents=True)
    print(f"[OK] Created project directory: {project_path}")

    # Create link to mcp-global-rules
    mcp_source = Path("C:/Users/dbiss/Desktop/Projects/_BLANK_/mcp-global-rules") if os.name == 'nt' else Path("/home/p4nd4pr0t0c01/Projects/mcp-global-rules")
    mcp_target = project_path / "mcp-global-rules"

    try:
        if os.name == 'nt':
            # Use Junction for Windows directory link
            subprocess.run(["cmd", "/c", "mklink", "/J", str(mcp_target), str(mcp_source)], check=True)
        else:
            os.symlink(mcp_source, mcp_target)
        print(f"[OK] Linked mcp-global-rules to {mcp_target}")
    except Exception as e:
        print(f"[WARN] Could not create link: {e}")

    # Run setup to ensure rules links etc. refreshed
    try:
        mcp_py = Path(__file__).parents[1] / "mcp.py"
        subprocess.run([sys.executable, str(mcp_py), "nsync", "setup"], capture_output=True)
    except:
        pass

    # Create a README.md if it doesn't exist
    with open(project_path / "README.md", "w") as f:
        f.write(f"# {name}\n\nThis project is part of the NSync ecosystem. Use `mcp nsync run` for execution on wizardpanda.\n")

    # [NEW] Create .cursorrules for AI Agent Onboarding
    with open(project_path / ".cursorrules", "w") as f:
        f.write("# MASTER AI INSTRUCTIONS\n\n")
        f.write("You are working in an NSync project. You MUST FOLLOW the global rules defined here:\n")
        f.write("- [Global Rules](mcp-global-rules/global_rules.md)\n\n")
        f.write("KEY CONTEXT:\n")
        f.write("- This project is BI-DIRECTIONALLY SYNCED with WizardPanda (Raspberry Pi 5).\n")
        f.write("- Use `mcp nsync run <file>` to execute work on remote hardware.\n")
        f.write("- Use `mcp comms status` to collaborate with other AI agents.\n")
        f.write("- Full cybersecurity toolset is available on WizardPanda via `mcp cybersec`.\n")

    # [NEW] Create AI_CONTEXT.md for deep-dive information
    with open(project_path / "AI_CONTEXT.md", "w") as f:
        f.write(f"# AI Onboarding: {name}\n\n")
        f.write("## 1. Environment\n")
        f.write("- **Host**: Quasar (Local Windows)\n")
        f.write("- **Peer**: WizardPanda (Remote Pi 5 via Tailscale)\n")
        f.write("- **Sync**: Real-time via NSync (Git-backed)\n\n")
        f.write("## 2. Capabilities\n")
        f.write("- Access to 70+ Cybersecurity tools (Nmap, Metasploit, etc.) on WizardPanda.\n")
        f.write("- Secure agent-to-agent communication via `mcp comms`.\n")
        f.write("- Automated Git-backed recovery and version control.\n\n")
        f.write("## 3. Mandatory Rules\n")
        f.write("- Always perform security checks using `mcp security` before syncing.\n")
        f.write("- Coordinate with peer agents via `mcp comms` to avoid conflicts.\n")

    # Trigger a sync to create it on the other side
    handler = NSyncHandler(nsync_path)
    handler.sync()
    return 0

def start_watch():
    if not Observer:
        print("[FAIL] 'watchdog' package not found. Install with: pip install watchdog")
        return 1

    path = get_nsync_path()
    if not path.exists():
        print(f"[FAIL] NSync directory not found at {path}")
        return 1

    # [NEW] PID-based singleton protection
    import tempfile
    pid_file = Path(tempfile.gettempdir()) / "nsync_watch.pid"
    if pid_file.exists():
        try:
            with open(pid_file, "r") as f:
                old_pid = int(f.read().strip())
                if os.name == 'nt':
                    # Windows PID check
                    subprocess.run(["tasklist", "/FI", f"PID eq {old_pid}"], check=True, capture_output=True)
                else:
                    # Linux PID check
                    os.kill(old_pid, 0)
                print(f"[NSYNC] Watch service already running (PID {old_pid}). Exiting.")
                return 0
        except:
            pid_file.unlink()

    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    handler = NSyncHandler(path)
    observer = Observer()
    observer.schedule(handler, str(path), recursive=True)
    observer.start()

    # Background polling for bidirectional sync (Pi -> Windows)
    # Only needed on Windows because Pi can't SSH back
    import threading
    def poll_remote():
        while True:
            time.sleep(30) # Poll every 30 seconds
            print("[NSYNC] Periodic check for remote changes...")
            handler.sync()

    if os.name == 'nt':
        poll_thread = threading.Thread(target=poll_remote, daemon=True)
        poll_thread.start()
        print("[NSYNC] Started background polling thread.")

    print(f"[NSYNC] Monitoring {path} for changes...")
    print("Press Ctrl+C to stop.")

    # [NEW] Start the autonomous collaboration launcher in the background
    launcher_py = Path(__file__).parent / "agent_launcher.py"
    try:
        # Check if launcher already running (agent_launcher has its own PID protection)
        subprocess.Popen([sys.executable, str(launcher_py)], start_new_session=True)
        print("[NSYNC] Autonomous collaboration launcher started.")
    except Exception as e:
        print(f"[WARN] Failed to start collaboration launcher: {e}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    finally:
        if pid_file.exists():
            pid_file.unlink()
    observer.join()
    return 0

def remote_run(filename: str):
    """Sync and run a script on wizardpanda."""
    local_path = get_nsync_path() / filename
    if not local_path.exists():
        print(f"[FAIL] File {filename} not found in NSync directory.")
        return 1

    print(f"[NSYNC] Syncing {filename} to {get_remote_peer()}...")
    # Manual sync before execution
    handler = NSyncHandler(get_nsync_path())
    handler.sync()

    remote_cmd = f"cd ~/Projects/NSync && python3 {filename}"
    ssh_cmd = ["ssh", f"{REMOTE_USER}@{get_remote_peer()}", remote_cmd]

    print(f"[EXEC] Executing on {get_remote_peer()}...\n" + "-"*40)
    subprocess.run(ssh_cmd)
    print("-"*40 + "\n[NSYNC] Remote execution complete.")
    return 0

def check_status():
    """Verify connectivity and repo states."""
    path = get_nsync_path()
    print(f"Local Path: {path}")
    if path.exists():
        print("[OK] Local directory exists.")
        os.chdir(path)
        res = subprocess.run(["git", "status"], capture_output=True, text=True)
        if res.returncode == 0:
            print("[OK] Git repository initialized.")
        else:
            print("[WARN] Git not initialized in NSync directory.")
    else:
        print("[FAIL] Local directory missing.")

    print(f"Peer: {get_remote_peer()}")
    res = subprocess.run(["ssh", f"{REMOTE_USER}@{get_remote_peer()}", "date"], capture_output=True)
    if res.returncode == 0:
        print("[OK] Peer reachable via SSH.")
    else:
        print("[FAIL] Peer unreachable or SSH failed.")

def setup_hooks():
    """Install Git hooks for sync automation."""
    path = get_nsync_path()
    hooks_dir = path / ".git" / "hooks"
    if not hooks_dir.exists():
        print(f"[FAIL] Git hooks directory missing at {hooks_dir}")
        return 1

    # Post-commit hook: Trigger sync immediately
    post_commit_path = hooks_dir / ("post-commit" if os.name != 'nt' else "post-commit")
    # Note: On Windows Git Bash uses the same name

    sync_cmd = "mcp nsync sync"
    if os.name == 'nt':
        # Create a shell script for Git to run
        with open(post_commit_path, "w") as f:
            f.write(f"#!/bin/sh\n{sync_cmd}\n")
    else:
        with open(post_commit_path, "w") as f:
            f.write(f"#!/bin/bash\npython3 /home/p4nd4pr0t0c01/Projects/mcp-global-rules/mcp.py nsync sync\n")

    os.chmod(post_commit_path, 0o755)
    print(f"[OK] Installed post-commit hook at {post_commit_path}")

    # Post-merge hook: Re-index context
    post_merge_path = hooks_dir / "post-merge"
    index_cmd = "mcp index-all"
    if os.name == 'nt':
        with open(post_merge_path, "w") as f:
            f.write(f"#!/bin/sh\n{index_cmd}\n")
    else:
        with open(post_merge_path, "w") as f:
            f.write(f"#!/bin/bash\npython3 /home/p4nd4pr0t0c01/Projects/mcp-global-rules/mcp.py index-all\n")

    os.chmod(post_merge_path, 0o755)
    print(f"[OK] Installed post-merge hook at {post_merge_path}")
    return 0

def main():
    if len(sys.argv) < 2:
        show_help()
        return 0

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "watch":
        return start_watch()
    elif cmd == "run" and args:
        return remote_run(args[0])
    elif cmd == "status":
        return check_status()
    elif cmd == "sync":
        handler = NSyncHandler(get_nsync_path())
        handler.sync()
        return 0
    elif cmd == "setup":
        return setup_hooks()
    elif cmd == "init-project" and args:
        return init_project(args[0])
    else:
        show_help()
    return 0

if __name__ == "__main__":
    sys.exit(main())
