#!/usr/bin/env python3
"""
MCP Agent Collaboration Layer (ACL)
Enables secure, bidirectional communication and presence tracking between AI agents.
"""

from pathlib import Path
import json
import os
import socket
import subprocess
import sys
import time

# Configuration - Shared with NSync
WINDOWS_NSYNC = Path("C:/Users/dbiss/Desktop/Projects/_BLANK_/NSync")
LINUX_NSYNC = Path("/home/p4nd4pr0t0c01/Projects/NSync")

def get_nsync_path() -> Path:
    return WINDOWS_NSYNC if os.name == 'nt' else LINUX_NSYNC

def get_comms_dir() -> Path:
    comms_dir = get_nsync_path() / ".nsync_agents"
    if not comms_dir.exists():
        comms_dir.mkdir(parents=True, exist_ok=True)
    return comms_dir

def get_mailbox_dir() -> Path:
    mailbox = get_comms_dir() / "messages"
    if not mailbox.exists():
        mailbox.mkdir(parents=True, exist_ok=True)
    return mailbox

def get_telegram_inbox_dir() -> Path:
    inbox = get_comms_dir() / "telegram_inbox"
    if not inbox.exists():
        inbox.mkdir(parents=True, exist_ok=True)
    return inbox

def get_hostname():
    # Allow override for specifically identifying the IDE agent session
    identity = os.environ.get("AGENT_IDENTITY")
    if identity:
        return identity
    return socket.gethostname()

class AgentPresence:
    """Manages local agent presence and heartbeats."""
    @staticmethod
    def update(status="active", task="monitoring"):
        presence_file = get_comms_dir() / f"{get_hostname()}.json"
        data = {
            "hostname": get_hostname(),
            "timestamp": time.time(),
            "status": status,
            "current_task": task,
            "last_seen": time.ctime()
        }
        with open(presence_file, "w") as f:
            json.dump(data, f, indent=2)

        # Trigger NSync to propagate the heartbeat
        try:
            mcp_py = Path(__file__).parents[1] / "mcp.py"
            subprocess.run([sys.executable, str(mcp_py), "nsync", "sync"], capture_output=True)
        except:
            pass
        return data

    @staticmethod
    def get_remote_status():
        comms_dir = get_comms_dir()
        remote_status = {}
        for f in comms_dir.glob("*.json"):
            if f.stem != get_hostname():
                try:
                    with open(f, "r") as pf:
                        remote_status[f.stem] = json.load(pf)
                except:
                    pass
        return remote_status

def send_message(recipient: str, msg_type: str, content: dict):
    """Sends an encrypted-in-transit message via NSync mailbox."""
    mailbox = get_mailbox_dir()
    msg_id = int(time.time() * 1000)
    msg_file = mailbox / f"{recipient}_{get_hostname()}_{msg_id}.json"

    payload = {
        "id": msg_id,
        "from": get_hostname(),
        "to": recipient,
        "type": msg_type,
        "content": content,
        "timestamp": time.time()
    }

    with open(msg_file, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[COMMS] Message sent to {recipient}: {msg_type}")

    # Trigger NSync to propagate the message
    try:
        mcp_py = Path(__file__).parents[1] / "mcp.py"
        subprocess.run([sys.executable, str(mcp_py), "nsync", "sync"], capture_output=True)
    except:
        pass
    return msg_file

def listen_for_messages():
    """Polls for messages addressed to this host."""
    mailbox = get_mailbox_dir()
    hostname = get_hostname()

    messages = []
    for f in mailbox.glob(f"{hostname}_*.json"):
        try:
            with open(f, "r") as mf:
                msg = json.load(mf)
                messages.append(msg)
            # Mark as read/processed by deleting
            f.unlink()
        except Exception as e:
            print(f"[WARN] Failed to read message {f}: {e}")

    return messages

def listen_for_telegram_messages():
    """Polls for Telegram messages. Background agents wait for Antigravity priority."""
    inbox = get_telegram_inbox_dir()
    hostname = get_hostname()
    agent_identity = os.getenv("AGENT_IDENTITY", hostname)  # Use AGENT_IDENTITY if set, else hostname

    messages = []

    # Priority 1: Messages directly for me (based on AGENT_IDENTITY)
    for f in inbox.glob(f"{agent_identity}_*.json"):
        try:
            with open(f, "r") as mf:
                msg = json.load(mf)
                messages.append(msg)
            f.unlink()
        except: pass

    # Skip fallback logic if I AM Antigravity (I already checked)
    if agent_identity.lower() == "antigravity":
        return messages

    # Priority 2: Fallback for Antigravity (Background Agents only)
    # Background agents (Quasar/wizardpanda) only take Antigravity messages if stale
    for f in inbox.glob("Antigravity_*.json"):
        try:
            # Check how old the message is
            stats = f.stat()
            age = time.time() - stats.st_mtime

            # If the IDE brain hasn't taken it in 60s, a background agent can help
            if age > 60:
                # But only the PRIMARY should handle the fallback to avoid double-response
                is_primary = False
                if hostname.lower() == "quasar":
                    is_primary = True
                else:
                    # If I'm on wizardpanda, I only take it if Quasar is offline
                    remotes = AgentPresence.get_remote_status()
                    quasar_active = False
                    for h, d in remotes.items():
                         if h.lower() == "quasar" and time.time() - d.get('timestamp', 0) < 120:
                             quasar_active = True
                    if not quasar_active:
                        is_primary = True

                if is_primary:
                    with open(f, "r") as mf:
                        msg = json.load(mf)
                        messages.append(msg)
                    f.unlink()
                    print(f"[COMMS] Handled Antigravity fallback message (Age: {int(age)}s)")
        except: pass

    return messages

def notify_user_telegram(text: str):
    """Sends a notification back to the user via the Telegram Bridge."""
    # The bridge will watch this directory for outgoing alerts
    outbox = get_comms_dir() / "telegram_outbox"
    if not outbox.exists():
        outbox.mkdir(parents=True, exist_ok=True)

    msg_id = int(time.time() * 1000)
    msg_file = outbox / f"out_{msg_id}.json"

    with open(msg_file, "w") as f:
        json.dump({"text": text, "from": get_hostname(), "timestamp": time.time()}, f, indent=2)
    print(f"[COMMS] Notification queued for Telegram: {text[:50]}...")

def show_status():
    """Displays local and remote agent status."""
    hostname = get_hostname()
    presence_file = get_comms_dir() / f"{hostname}.json"
    local = {}
    if presence_file.exists():
        with open(presence_file, "r") as f:
            local = json.load(f)
    else:
        local = AgentPresence.update() # Create if missing

    print("--- Local Agent Priority ---")
    print(f"Host:   {local.get('hostname', hostname)}")
    print(f"Status: {local.get('status', 'unknown')}")
    print(f"Task:   {local.get('current_task', 'unknown')}")
    print(f"Sync:   {local.get('last_seen', 'unknown')}")

    print("\n--- Remote Agents ---")
    remotes = AgentPresence.get_remote_status()
    if not remotes:
        print("No remote agents detected yet.")
    for host, data in remotes.items():
        age = time.time() - data['timestamp']
        active_str = "[ACTIVE]" if age < 60 else "[OFFLINE/STALE]"
        print(f"Host:   {host} {active_str}")
        print(f"Status: {data['status']}")
        print(f"Task:   {data['current_task']}")
        print(f"Last heartbeat: {int(age)}s ago")
        print("-" * 20)

def show_help():
    print("MCP Agent Collaboration Layer (ACL)")
    print("Usage: mcp comms <command> [args]")
    print("\nCommands:")
    print("  status                Check local and remote agent presence")
    print("  send <host> <type> <msg> Send a message to a specific agent")
    print("  listen                Poll and display unread messages")
    print("  ping <host>           Quick verification of remote agent life")
    print("  heartbeat <status> <task> Update local presence info")
    print("  collaborate           Enter autonomous agent-to-agent team mode")

def handle_telegram_instruction(text):
    """Parses telegram text and tries to execute as an MCP command or route to Antigravity."""
    print(f"[EXEC] Parsing Telegram Task: {text}")

    # Check if this is the "Antigravity" agent (IDE session)
    # If so, send to Antigravity automation instead of running MCP commands
    hostname = get_hostname().lower()
    agent_identity = os.getenv("AGENT_IDENTITY", "").lower()

    # Route to Antigravity IDE automation if AGENT_IDENTITY is set to "Antigravity"
    if agent_identity == "antigravity":
        try:
            # Import antigravity automation module
            antigravity_path = Path(__file__).resolve().parent / "antigravity_automation.py"
            if antigravity_path.exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location("antigravity_automation", antigravity_path)
                ag_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(ag_module)

                # Send message to Antigravity IDE
                print("[INFO] Routing message to Antigravity IDE automation")
                response = ag_module.handle_antigravity_message(text)
                return response if response else "[ERROR] No response from Antigravity"
            else:
                print(f"[WARNING] antigravity_automation.py not found at {antigravity_path}")
                return "Antigravity automation module not found. Install with: python antigravity_automation.py install"
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[ERROR] Antigravity automation failed: {e}\n{error_details}")
            return f"Error routing to Antigravity: {e}"

    # Otherwise, handle as regular MCP command
    mcp_py = Path(__file__).parents[1] / "mcp.py"

    # Simple mapping or direct attempt
    cmd_parts = text.split()
    if not cmd_parts: return "Empty command"

    # If the user says "status", run "mcp comms status"
    # If they say "scan", we might need more logic, but for now let's try direct mapping
    try:
        if text.lower() == "status":
            res = subprocess.run([sys.executable, str(mcp_py), "comms", "status"], capture_output=True, text=True)
            return res.stdout
        elif text.lower().startswith("run "):
            # e.g. "run script.py" -> "mcp nsync run script.py"
            script = text[4:].strip()
            res = subprocess.run([sys.executable, str(mcp_py), "nsync", "run", script], capture_output=True, text=True)
            return res.stdout
        else:
            # Try running it as a generic mcp command if it looks like one
            # Otherwise, just acknowledge.
            return f"Received: {text}. (Smart execution for this command pending development)"
    except Exception as e:
        return f"Error executing task: {e}"

def autonomous_loop():
    """Autonomous execution loop for AI agents."""
    hostname = get_hostname()
    print(f"[AUTONOMOUS] Agent {hostname} entered collaboration mode.")
    AgentPresence.update("active", "autonomous collaboration")

    try:
        while True:
            msgs = listen_for_messages()
            for m in msgs:
                print(f"\n[RECEIVED] From: {m['from']} | Type: {m['type']}")
                if m['type'] == "task" or m['type'] == "instruction":
                    task_text = m['content'].get('text', '')
                    result = handle_telegram_instruction(task_text)
                    send_message(m['from'], "result", {"text": result})

            # Check for Telegram instructions
            t_msgs = listen_for_telegram_messages()
            for tm in t_msgs:
                print(f"\n[TELEGRAM] Instruction received: {tm['text']}")
                result = handle_telegram_instruction(tm['text'])
                notify_user_telegram(f"Result for '{tm['text']}':\n{result}")

            time.sleep(5)
            # Periodic heartbeat
            AgentPresence.update("active", "listening for team tasks")
    except KeyboardInterrupt:
        print("\n[AUTONOMOUS] Collaboration mode stopped.")

def main():
    if len(sys.argv) < 2:
        show_help()
        return 0

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "status":
        show_status()
    elif cmd == "send" and len(args) >= 3:
        send_message(args[0], args[1], {"text": " ".join(args[2:])})
    elif cmd == "listen":
        msgs = listen_for_messages()
        if not msgs:
            print("No new messages.")
        for m in msgs:
            print(f"\n[FROM: {m['from']}] [TYPE: {m['type']}]")
            print(f"Content: {m['content']}")
    elif cmd == "ping" and args:
        remotes = AgentPresence.get_remote_status()
        if args[0] in remotes:
            age = time.time() - remotes[args[0]]['timestamp']
            if age < 60:
                print(f"[OK] {args[0]} is ALIVE (Age: {int(age)}s)")
                return 0
        print(f"[FAIL] {args[0]} is UNREACHABLE or STALE")
        return 1
    elif cmd == "heartbeat" and len(args) >= 2:
        AgentPresence.update(args[0], args[1])
        print("[OK] Heartbeat updated.")
    elif cmd == "collaborate":
        autonomous_loop()
    else:
        show_help()
    return 0

if __name__ == "__main__":
    sys.exit(main())
