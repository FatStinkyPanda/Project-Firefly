"""
Learning System
================
Learn from feedback, preferences, and past mistakes.

Usage:
    python mcp.py learn --show-patterns
    python mcp.py learn --from-feedback
"""

from collections import Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import sys

from .utils import Console, find_project_root


@dataclass
class Feedback:
    """A feedback entry."""
    action: str
    outcome: str  # 'success', 'failure', 'partial'
    context: str
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorPattern:
    """A learned error pattern."""
    error_type: str
    pattern: str
    fix: str
    occurrences: int = 1
    last_seen: str = ""
    contexts: List[str] = field(default_factory=list)


@dataclass
class Preference:
    """A user preference."""
    key: str
    value: Any
    learned_from: str = "default"
    confidence: float = 0.5


class LearningStore:
    """Store for learning data."""

    def __init__(self, storage_path: Path = None):
        if storage_path:
            self.storage_path = storage_path
        else:
            home = Path.home()
            self.storage_path = home / '.mcp' / 'learning'

        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.feedback: List[Feedback] = []
        self.errors: Dict[str, ErrorPattern] = {}
        self.preferences: Dict[str, Preference] = {}

        self.load()

    def load(self):
        """Load learning data."""
        # Load feedback
        fb_path = self.storage_path / 'feedback.json'
        if fb_path.exists():
            try:
                with open(fb_path, 'r') as f:
                    data = json.load(f)
                    self.feedback = [Feedback(**d) for d in data]
            except Exception:
                pass

        # Load error patterns
        err_path = self.storage_path / 'errors.json'
        if err_path.exists():
            try:
                with open(err_path, 'r') as f:
                    data = json.load(f)
                    self.errors = {k: ErrorPattern(**v) for k, v in data.items()}
            except Exception:
                pass

        # Load preferences
        pref_path = self.storage_path / 'preferences.json'
        if pref_path.exists():
            try:
                with open(pref_path, 'r') as f:
                    data = json.load(f)
                    self.preferences = {k: Preference(**v) for k, v in data.items()}
            except Exception:
                pass

    def save(self):
        """Save all learning data."""
        # Save feedback
        fb_path = self.storage_path / 'feedback.json'
        with open(fb_path, 'w') as f:
            json.dump([asdict(fb) for fb in self.feedback[-1000:]], f, indent=2)

        # Save errors
        err_path = self.storage_path / 'errors.json'
        with open(err_path, 'w') as f:
            json.dump({k: asdict(v) for k, v in self.errors.items()}, f, indent=2)

        # Save preferences
        pref_path = self.storage_path / 'preferences.json'
        with open(pref_path, 'w') as f:
            json.dump({k: asdict(v) for k, v in self.preferences.items()}, f, indent=2)

    def record_feedback(
        self,
        action: str,
        outcome: str,
        context: str = "",
        details: Dict = None
    ):
        """Record feedback on an action."""
        fb = Feedback(
            action=action,
            outcome=outcome,
            context=context,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            details=details or {}
        )
        self.feedback.append(fb)
        self.save()

    def record_error(self, error_type: str, pattern: str, fix: str, context: str = ""):
        """Record an error and its fix."""
        key = f"{error_type}:{pattern[:50]}"

        if key in self.errors:
            err = self.errors[key]
            err.occurrences += 1
            err.last_seen = datetime.utcnow().isoformat() + 'Z'
            if context and context not in err.contexts:
                err.contexts.append(context)
                err.contexts = err.contexts[-5:]  # Keep last 5
        else:
            self.errors[key] = ErrorPattern(
                error_type=error_type,
                pattern=pattern,
                fix=fix,
                last_seen=datetime.utcnow().isoformat() + 'Z',
                contexts=[context] if context else []
            )

        self.save()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a preference value."""
        pref = self.preferences.get(key)
        return pref.value if pref else default

    def set_preference(self, key: str, value: Any, source: str = "user"):
        """Set a preference."""
        self.preferences[key] = Preference(
            key=key,
            value=value,
            learned_from=source,
            confidence=1.0 if source == "user" else 0.7
        )
        self.save()

    def suggest_fix(self, error_type: str, pattern: str) -> Optional[str]:
        """Suggest a fix for an error based on patterns."""
        key = f"{error_type}:{pattern[:50]}"

        if key in self.errors:
            return self.errors[key].fix

        # Fuzzy match
        for k, err in self.errors.items():
            if error_type in k and pattern[:20] in err.pattern:
                return err.fix

        return None

    def get_action_success_rate(self, action: str) -> float:
        """Get success rate for an action type."""
        relevant = [fb for fb in self.feedback if fb.action == action]
        if not relevant:
            return 0.5  # Unknown

        successes = sum(1 for fb in relevant if fb.outcome == 'success')
        return successes / len(relevant)

    def get_common_errors(self, limit: int = 10) -> List[ErrorPattern]:
        """Get most common errors."""
        sorted_errors = sorted(
            self.errors.values(),
            key=lambda e: e.occurrences,
            reverse=True
        )
        return sorted_errors[:limit]

    def analyze_patterns(self) -> Dict:
        """Analyze learning patterns."""
        analysis = {
            "total_feedback": len(self.feedback),
            "total_errors": len(self.errors),
            "total_preferences": len(self.preferences),
            "action_outcomes": {},
            "common_errors": []
        }

        # Analyze action outcomes
        action_counts = Counter()
        action_success = Counter()

        for fb in self.feedback:
            action_counts[fb.action] += 1
            if fb.outcome == 'success':
                action_success[fb.action] += 1

        for action, count in action_counts.most_common(10):
            rate = action_success[action] / count if count > 0 else 0
            analysis["action_outcomes"][action] = {
                "count": count,
                "success_rate": round(rate, 2)
            }

        # Common errors
        for err in self.get_common_errors(5):
            analysis["common_errors"].append({
                "type": err.error_type,
                "pattern": err.pattern[:50],
                "fix": err.fix[:50],
                "occurrences": err.occurrences
            })

        return analysis


# Global store
_store: Optional[LearningStore] = None


def get_store() -> LearningStore:
    global _store
    if _store is None:
        _store = LearningStore()
    return _store


def record_feedback(action: str, outcome: str, context: str = ""):
    """Record feedback."""
    get_store().record_feedback(action, outcome, context)


def record_error(error_type: str, pattern: str, fix: str):
    """Record an error pattern."""
    get_store().record_error(error_type, pattern, fix)


def suggest_fix(error_type: str, pattern: str) -> Optional[str]:
    """Get suggested fix."""
    return get_store().suggest_fix(error_type, pattern)


def main():
    """CLI entry point."""
    Console.header("Learning System")

    store = get_store()

    Console.info(f"Storage: {store.storage_path}")
    Console.info(f"Feedback entries: {len(store.feedback)}")
    Console.info(f"Error patterns: {len(store.errors)}")
    Console.info(f"Preferences: {len(store.preferences)}")

    if '--show-patterns' in sys.argv or '--patterns' in sys.argv:
        analysis = store.analyze_patterns()

        print("\n## Action Outcomes")
        for action, data in analysis["action_outcomes"].items():
            print(f"  {action}: {data['success_rate']*100:.0f}% success ({data['count']} times)")

        print("\n## Common Errors")
        for err in analysis["common_errors"]:
            print(f"  [{err['type']}] {err['pattern']}")
            print(f"    Fix: {err['fix']}")
            print(f"    Occurred: {err['occurrences']} times")

        return 0

    if '--preferences' in sys.argv:
        print("\n## Preferences")
        for key, pref in store.preferences.items():
            print(f"  {key}: {pref.value} (from {pref.learned_from})")
        return 0

    # Show summary
    analysis = store.analyze_patterns()
    print(f"\nTotal learning data: {analysis['total_feedback']} feedback, {analysis['total_errors']} errors")

    return 0


if __name__ == "__main__":
    sys.exit(main())
