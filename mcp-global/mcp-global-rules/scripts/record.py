"""
Context Recorder
================
Record development actions and context snapshots to memory.

Usage:
    python mcp.py record "Action description"
    python mcp.py record --snapshot
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .utils import Console, find_project_root, run_git_command
from .memory import get_store

def get_git_status(root: Path) -> str:
    """Get concise git status."""
    status = run_git_command(['status', '--short'], cwd=root)
    if not status:
        return "No changes"
    return status

def get_git_diff_stat(root: Path) -> str:
    """Get git diff stats."""
    # Staged changes
    staged = run_git_command(['diff', '--cached', '--stat'], cwd=root)
    return staged or "No staged changes"

def analyze_diff(root: Path) -> str:
    """Analyze the staged diff for semantic meaning."""
    diff = run_git_command(['diff', '--cached', '-U0'], cwd=root)
    if not diff:
        return "No staged changes detected."
        
    changes = []
    current_file = ""
    
    for line in diff.split('\n'):
        if line.startswith('diff --git'):
            # diff --git a/file.py b/file.py
            parts = line.split()
            if len(parts) >= 4:
                current_file = parts[-1].lstrip('b/')
        elif line.startswith('@@'):
            # @@ -10,0 +11,5 @@ def new_function():
            # Try to extract context hint
            context = line.split('@@')[-1].strip()
            if context and current_file:
                changes.append(f"- {current_file}: {context}")
            elif current_file:
                 changes.append(f"- {current_file}: (modification)")

    # Deduplicate and summarize
    unique_changes = sorted(list(set(changes)))
    if len(unique_changes) > 10:
        return "\n".join(unique_changes[:10]) + f"\n... ({len(unique_changes) - 10} more changes)"
    return "\n".join(unique_changes)

def record_snapshot(root: Path) -> bool:
    """Record a context snapshot of current state."""
    Console.info("Recording context snapshot...")
    
    status = get_git_status(root)
    semantic_summary = analyze_diff(root)
    
    content = f"# Context Snapshot\n\n## Git Status\n{status}\n\n## Semantic Changes\n{semantic_summary}"
    
    store = get_store()
    timestamp = datetime.now().isoformat()
    
    store.remember(
        key=f"Snapshot {timestamp}",
        value=content,
        tags=['snapshot', 'auto-context', 'pre-commit']
    )
    
    Console.ok("Context snapshot recorded")
    return True

def main():
    """CLI entry point."""
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    root = find_project_root() or Path.cwd()
    
    if '--snapshot' in sys.argv:
        record_snapshot(root)
        return 0
        
    if not args:
        Console.fail("Usage: mcp record 'message' OR mcp record --snapshot")
        return 1
        
    message = " ".join(args)
    store = get_store()
    store.remember(
        key=f"Action {datetime.now().isoformat()}",
        value=message,
        tags=['user-action']
    )
    Console.ok("Action recorded")
    return 0

if __name__ == "__main__":
    sys.exit(main())
