#!/usr/bin/env python3
"""
MCP Agent Collaboration Layer (ACL)
Enables secure, bidirectional communication and presence tracking between AI agents.
"""

from pathlib import Path
import json
import os
import socket
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

def get_hostname():
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

def show_status():
    """Displays local and remote agent status."""
    local = AgentPresence.update()
    print("--- Local Agent Priority ---")
    print(f"Host:   {local['hostname']}")
    print(f"Status: {local['status']}")
    print(f"Task:   {local['current_task']}")
    print(f"Sync:   {local['last_seen']}")

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
                print(f"Content: {m['content']}")

                # If it's a task, execute it and report back
                if m['type'] == "task" or m['type'] == "instruction":
                    task_text = m['content'].get('text', '')
                    print(f"[EXEC] Starting task: {task_text}")
                    # In a real scenario, the agent would use the LLM to process this.
                    # For now, we simulate acknowledgment.
                    send_message(m['from'], "ack", {"text": f"Task received and processing: {task_text}"})

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
