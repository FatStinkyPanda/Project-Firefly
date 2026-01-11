"""
Auto-Learning Integration
=========================
Automatic recording of tool outcomes for continuous improvement.

Usage:
    Import and wrap tool functions for auto-learning.
"""

from pathlib import Path
from typing import Any, Callable, Optional
import functools
import sys
import traceback

# Import learning system
try:
    from .learning import get_store, record_feedback, record_error as _record_error
except ImportError:
    # Fallback if not running as module
    def record_feedback(*args, **kwargs): pass
    def _record_error(*args, **kwargs): pass


def auto_learn(tool_name: str):
    """Decorator to auto-record tool outcomes."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                result = func(*args, **kwargs)

                # Record success
                context = f"args={args[:2]}" if args else ""
                record_feedback(tool_name, 'success', context)

                return result
            except Exception as e:
                # Record failure
                tb = traceback.format_exc()
                record_error(
                    error_type=type(e).__name__,
                    pattern=str(e)[:100],
                    fix="",
                    context=f"Tool: {tool_name}"
                )
                record_feedback(tool_name, 'failure', str(e)[:100])
                raise

        return wrapper
    return decorator


def record_error(
    error_type: str,
    pattern: str,
    fix: str = "",
    context: str = ""
):
    """Record an error for learning."""
    try:
        from .learning import get_store
        store = get_store()
        store.record_error(error_type, pattern, fix, context)
    except Exception:
        pass  # Silent fail for learning


def record_correction(before: str, after: str, context: str = ""):
    """Record a user correction for learning."""
    try:
        from .learning import get_store
        store = get_store()
        store.record_feedback(
            action='correction',
            outcome='applied',
            context=f"Before: {before[:50]}... After: {after[:50]}...",
            details={'before': before, 'after': after}
        )
    except Exception:
        pass


def suggest_from_history(error_type: str, pattern: str) -> Optional[str]:
    """Get fix suggestion from learning history."""
    try:
        from .learning import get_store
        store = get_store()
        return store.suggest_fix(error_type, pattern)
    except Exception:
        return None


def get_success_rate(tool_name: str) -> float:
    """Get success rate for a tool."""
    try:
        from .learning import get_store
        store = get_store()
        return store.get_action_success_rate(tool_name)
    except Exception:
        return 0.5  # Unknown


def main():
    """CLI entry point."""
    from .utils import Console
    Console.header("Auto-Learning Status")

    try:
        from .learning import get_store
        store = get_store()

        analysis = store.analyze_patterns()

        print(f"\nTotal feedback: {analysis['total_feedback']}")
        print(f"Error patterns: {analysis['total_errors']}")

        print("\n## Tool Success Rates")
        for action, data in analysis.get('action_outcomes', {}).items():
            rate = data['success_rate'] * 100
            status = "✓" if rate > 80 else "!" if rate > 50 else "✗"
            print(f"  {status} {action}: {rate:.0f}% ({data['count']} uses)")

        print("\n## Common Errors")
        for err in analysis.get('common_errors', [])[:5]:
            print(f"  - [{err['type']}] {err['pattern'][:40]}...")
            if err.get('fix'):
                print(f"    Fix: {err['fix'][:40]}...")

    except Exception as e:
        print(f"Error loading learning data: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
