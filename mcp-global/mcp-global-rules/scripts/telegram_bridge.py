#!/usr/bin/env python3
"""
Telegram C2 Bridge
Polls Telegram for user instructions and dispatches them to active agents.
"""

from pathlib import Path
import json
import os
import sys
import time

import requests

# MCP Path Resolution
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.append(str(SCRIPTS_DIR))

try:
    import agent_comms
except ImportError:
    pass

CONFIG_FILE = Path(__file__).resolve().parent / "telegram_config.json"

def get_config():
    if not CONFIG_FILE.exists():
        return None
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def poll_telegram(config):
    # Only the primary host should poll for updates to avoid 409 Conflict
    # We'll designate Quasar (Windows) as primary, WizardPanda as fallback.
    hostname = agent_comms.get_hostname().lower()
    is_windows = os.name == 'nt'

    # Simple logic: If we are on Linux and a Windows agent was seen recently, don't poll.
    if not is_windows:
        remotes = agent_comms.AgentPresence.get_remote_status()
        for host, data in remotes.items():
            if data.get('hostname', '').lower() == 'quasar' or 'window' in host.lower():
                age = time.time() - data.get('timestamp', 0)
                if age < 120: # Quasar was seen in the last 2 minutes
                    return

    token = config.get("bot_token")
    chat_id = config.get("chat_id")
    last_update = config.get("last_update_id", 0)

    url = f"https://api.telegram.org/bot{token}/getUpdates?offset={last_update + 1}&timeout=10"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            updates = r.json().get("result", [])
            for update in updates:
                last_update = update["update_id"]
                msg = update.get("message", {})
                text = msg.get("text", "")
                from_id = msg.get("from", {}).get("id")

                if str(from_id) == str(chat_id):
                    handle_instruction(text)

            # Save progress
            config["last_update_id"] = last_update
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
        elif r.status_code != 409: # Ignore expected conflicts during handovers
            print(f"[BRIDGE] Telegram API Error: {r.status_code}")
    except Exception as e:
        pass # Silently retry on network humps

def handle_instruction(text):
    print(f"[BRIDGE] Received instruction: {text}")
    target_host = agent_comms.get_hostname().lower()

    if text.lower().startswith("to "):
        parts = text.split(":", 1)
        if len(parts) == 2:
            target_host = parts[0].replace("to ", "").strip().lower()
            text = parts[1].strip()

    inbox = agent_comms.get_telegram_inbox_dir()
    msg_id = int(time.time() * 1000)

    # If the user says "to antigravity", "to assistant", or just "to me"
    if text.lower().startswith("to antigravity") or text.lower().startswith("to assistant"):
         target_host = "Antigravity"
         if ":" in text:
             text = text.split(":", 1)[1].strip()

    msg_file = inbox / f"{target_host}_{msg_id}.json"

    with open(msg_file, "w") as f:
        json.dump({"text": text, "timestamp": time.time()}, f, indent=2)

def check_outbox(config):
    token = config.get("bot_token")
    chat_id = config.get("chat_id")
    outbox = agent_comms.get_comms_dir() / "telegram_outbox"

    if not outbox.exists():
        return

    # Use a temp directory outside of the NSync synced tree for processing
    import tempfile
    buffer_dir = Path(tempfile.gettempdir()) / "mcp_telegram_buffer"
    if not buffer_dir.exists():
        buffer_dir.mkdir(parents=True, exist_ok=True)

    for f in outbox.glob("*.json"):
        if f.is_dir() or f.name.startswith("."): continue
        try:
            # Move to local temp buffer first (breaks sync lock)
            target = buffer_dir / f.name
            try:
                # Force replace if target exists (stale)
                if target.exists(): os.remove(target)
                os.rename(str(f), str(target))
            except OSError:
                continue # Still locked by NSync or Git

            with open(target, "r") as mf:
                data = json.load(mf)
                from_agent = data.get('from', 'Unknown')
                content = data.get('text', '')
                # Ensure we don't have empty content
                if not content: content = "[Empty Message]"

                text = f"📢 *{from_agent}*:\n{content}"

                url = f"https://api.telegram.org/bot{token}/sendMessage"
                try:
                    r = requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=15)
                    if r.status_code == 200:
                        os.remove(target)
                    else:
                        print(f"[BRIDGE] API Error {r.status_code}: {r.text}")
                        # Fallback for Markdown failure
                        if r.status_code == 400:
                            print("[BRIDGE] Retrying without Markdown...")
                            requests.post(url, json={"chat_id": chat_id, "text": text.replace("*", "")}, timeout=10)
                            os.remove(target)
                except Exception as e:
                    print(f"[BRIDGE] Request failed: {e}")
        except Exception as e:
            print(f"[BRIDGE] Loop error: {e}")

def main():
    print("--- Telegram C2 Bridge ---")

    # [NEW] PID-based singleton protection
    import tempfile
    pid_file = Path(tempfile.gettempdir()) / "telegram_bridge.pid"
    if pid_file.exists():
        try:
            with open(pid_file, "r") as f:
                old_pid = int(f.read().strip())
                if os.name == 'nt':
                    subprocess.run(["tasklist", "/FI", f"PID eq {old_pid}"], check=True, capture_output=True)
                else:
                    os.kill(old_pid, 0)
                print(f"[BRIDGE] Service already running (PID {old_pid}). Exiting.")
                return 0
        except:
            pid_file.unlink()

    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    try:
        config = get_config()
        if not config:
            print("[FAIL] telegram_config.json missing. Please create it with bot_token and chat_id.")
            return 1

        print(f"[BRIDGE] Configuration loaded. Chat ID: {config.get('chat_id')}")

        while True:
            poll_telegram(config)
            check_outbox(config)
            time.sleep(2)
    except Exception as e:
        print(f"[CRITICAL] Bridge encountered an unhandled error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if pid_file.exists():
            pid_file.unlink()

if __name__ == "__main__":
    main()
