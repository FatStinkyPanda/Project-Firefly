"""
Auto-Dev Loop Trigger
=====================
Triggers the autonomous development loop if enabled by the user.
"""

from pathlib import Path
import sys

from .utils import Console, find_project_root
import config.loop_config as loop_config

def main():
    """Check config and trigger loop if enabled."""
    if not loop_config.ENABLE_AUTO_LOOP:
        Console.info("Auto-Dev Loop: Disabled (User controllable via mcp-global-rules/config/loop_config.py)")
        return 0

    # Locate the prompt file
    root = find_project_root() or Path.cwd()
    # Check standard location first
    prompt_path = root / "mcp-global-rules" / "prompts" / "auto_dev.md"

    if not prompt_path.exists():
        # Fallback to the user's legacy temp file as requested (but preferring permanent)
        fallback = root / "ai-script-to-make-it-continue-development.md"
        if fallback.exists():
            prompt_path = fallback
        else:
            Console.warn("Auto-Dev Loop: Enabled but prompt file not found.")
            return 1

    try:
        content = prompt_path.read_text(encoding='utf-8').strip()
        Console.header("AUTO-DEV LOOP TRIGGERED")
        print("\n" + "="*40)
        print(">>> INJECTION START >>>")
        print(content)
        print("<<< INJECTION END <<<")
        print("="*40 + "\n")
        Console.ok("Prompt sent to agent stream.")
    except Exception as e:
        Console.fail(f"Failed to read prompt: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
