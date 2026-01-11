#!/usr/bin/env python3
"""
Antigravity Autonomous Agent Launcher
Ensures the mcp comms collaborate loop stays running in the background.
Auto-restarts on failure.
"""

from pathlib import Path
import os
import subprocess
import sys
import time

import signal

PID_FILE = Path("/tmp/agent_launcher.pid") if os.name != 'nt' else Path(os.environ.get('TEMP', 'C:/Temp')) / "agent_launcher.pid"

def is_already_running():
    if PID_FILE.exists():
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            # Check if process exists
            if os.name != 'nt':
                os.kill(pid, 0)
            else:
                # Windows check
                subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, check=True)
            return True
        except:
            PID_FILE.unlink(missing_ok=True)
    return False

def write_pid():
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

def get_mcp_py():
    script_dir = Path(__file__).resolve().parent
    mcp_py = script_dir.parent / "mcp.py"
    return str(mcp_py)

def run_collaboration():
    mcp_py = get_mcp_py()
    script_dir = Path(__file__).resolve().parent
    telegram_bridge_py = script_dir / "telegram_bridge.py"
    telegram_config = script_dir / "telegram_config.json"

    print(f"[LAUNCHER] Starting autonomous collaboration loop...")

    t_process = None

    while True:
        try:
            # Check/Start Telegram Bridge if configured
            if telegram_config.exists():
                if t_process is None or t_process.poll() is not None:
                    action = "Starting" if t_process is None else "Restarting"
                    print(f"[LAUNCHER] Telegram configuration found. {action} Bridge...")
                    t_process = subprocess.Popen([sys.executable, str(telegram_bridge_py)], shell=False)

            # Run mcp comms collaborate
            process = subprocess.Popen([sys.executable, mcp_py, "comms", "collaborate"], shell=False)

            # Monitoring loop
            while process.poll() is None:
                # Dynamically check for Telegram bridge if config exists
                if telegram_config.exists():
                    if t_process is None or t_process.poll() is not None:
                        print("[LAUNCHER] Telegram Bridge starting/restarting...")
                        t_process = subprocess.Popen([sys.executable, str(telegram_bridge_py)], shell=False)
                elif t_process and t_process.poll() is None:
                    # If config removed, kill the bridge
                    print("[LAUNCHER] Telegram config removed. Stopping Bridge...")
                    t_process.terminate()
                    t_process = None

                time.sleep(5)

            print(f"[LAUNCHER] Collaboration loop exited with code {process.returncode}. Restarting in 5s...")
        except Exception as e:
            print(f"[LAUNCHER] Error in loop: {e}. Restarting in 10s...")
            time.sleep(10)

        time.sleep(5)

if __name__ == "__main__":
    if is_already_running():
        print("[LAUNCHER] Already running. Exiting.")
        sys.exit(0)

    write_pid()
    try:
        run_collaboration()
    finally:
        PID_FILE.unlink(missing_ok=True)
