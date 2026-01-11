#!/usr/bin/env python3
"""
MCP Cybersecurity Tool Wrapper
Integrates 70+ security tools from wizardpanda into the MCP CLI.
"""

from pathlib import Path
from typing import List, Dict, Optional
import os
import subprocess
import sys

# Tool Categories
CATEGORIES = {
    "Network": ["nmap", "masscan", "arp-scan", "netdiscover", "fping", "hping3"],
    "Web": ["gobuster", "dirb", "dirbuster", "nikto", "sqlmap", "wfuzz", "commix"],
    "Exploitation": ["msfconsole", "msfvenom", "searchsploit", "beef-xss", "social-engineer-toolkit"],
    "Password": ["hydra", "john", "hashcat", "medusa", "ncrack"],
    "Wireless": ["aircrack-ng", "airmon-ng", "airodump-ng", "aireplay-ng", "reaver", "bully", "wifite"],
    "Forensics": ["autopsy", "binwalk", "foremost", "scalpel", "chkrootkit", "rkhunter"],
    "OSINT": ["theHarvester", "recon-ng", "whois", "dig", "nslookup"],
    "Reverse": ["gdb", "radare2", "ghidra", "cutter", "objdump"],
    "Post-Exploitation": ["impacket", "powersploit", "bloodhound", "mimikatz"]
}

# Special Environment Paths
CYBERSEC_ENV = Path.home() / "cybersec-env"
CYBERSEC_BIN = CYBERSEC_ENV / "bin"

def get_impacket_tools() -> List[str]:
    """List tools available in the Impacket virtualenv."""
    if not CYBERSEC_BIN.exists():
        return []
    return [f.name for f in CYBERSEC_BIN.iterdir() if f.is_file() and f.name.endswith(".py")]

def show_help():
    """Show help for the cybersec command."""
    print("MCP Cybersecurity Tool Wrapper")
    print("Usage: mcp cybersec <category|tool|list> [args]")
    print("\nCommands:")
    print("  list              List all tool categories and available tools")
    print("  help <tool>       Show help for a specific tool")
    print("  <tool> [args]     Execute a specific tool (e.g., mcp cybersec nmap -sV target)")
    print("\nCategories:")
    for cat in CATEGORIES:
        print(f"  {cat}")

def list_tools():
    """List all tools organized by category."""
    print("Available Cybersecurity Tools:")
    for cat, tools in CATEGORIES.items():
        print(f"\n[{cat}]")
        print(", ".join(tools))

    impacket_tools = get_impacket_tools()
    if impacket_tools:
        print("\n[Impacket (Auto-activates VENV)]")
        # Split into manageable chunks for display
        for i in range(0, len(impacket_tools), 5):
            print(", ".join(impacket_tools[i:i+5]))

def run_tool(tool_name: str, args: List[str]):
    """Run a specific tool, handling env activation if needed."""

    # Check if it's an impacket tool
    impacket_tools = get_impacket_tools()
    if tool_name in impacket_tools or tool_name.replace(".py", "") in [t.replace(".py", "") for t in impacket_tools]:
        if not tool_name.endswith(".py"):
            tool_name += ".py"

        python_bin = CYBERSEC_BIN / "python3"
        tool_path = CYBERSEC_BIN / tool_name

        if not python_bin.exists() or not tool_path.exists():
            print(f"[FAIL] Impacket tool {tool_name} not found or venv invalid.")
            return 1

        cmd = [str(python_bin), str(tool_path)] + args
        print(f"[EXEC] Running Impacket tool: {' '.join(cmd)}")
    else:
        # Check if tool is in PATH
        from shutil import which
        if not which(tool_name):
            print(f"[FAIL] Tool '{tool_name}' not found in system PATH.")
            print("Tip: Use 'mcp cybersec list' to see available tools.")
            return 1

        cmd = [tool_name] + args
        print(f"[EXEC] Running tool: {' '.join(cmd)}")

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n[INFO] Tool execution interrupted by user.")
    except Exception as e:
        print(f"[FAIL] Error running tool: {e}")
        return 1
    return 0

def main():
    if len(sys.argv) < 2:
        show_help()
        return 0

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "list":
        list_tools()
    elif cmd == "help" and args:
        run_tool(args[0], ["--help"])
    elif cmd in CATEGORIES:
        print(f"Tools in category '{cmd}':")
        print(", ".join(CATEGORIES[cmd]))
    else:
        return run_tool(cmd, args)

if __name__ == "__main__":
    sys.exit(main())
