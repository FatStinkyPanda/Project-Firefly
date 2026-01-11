"""
ast-grep Wrapper
================
Structural code search and transformation using ast-grep.

Usage:
    from scripts.astgrep import search_pattern, apply_fix
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .utils import Console, find_python_files


# Check if ast-grep is available
def _find_astgrep() -> Optional[str]:
    """Find ast-grep binary."""
    for name in ['ast-grep', 'sg']:
        try:
            result = subprocess.run(
                [name, '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return name
        except FileNotFoundError:
            continue
    return None


ASTGREP_BIN = _find_astgrep()
ASTGREP_AVAILABLE = ASTGREP_BIN is not None


@dataclass
class PatternMatch:
    """A pattern match result."""
    path: Path
    line: int
    column: int
    text: str
    matched_text: str
    pattern: str


@dataclass
class PatternRule:
    """A pattern rule for search/fix."""
    id: str
    pattern: str
    message: str
    fix: Optional[str] = None
    severity: str = "warning"
    language: str = "python"


# Built-in patterns for common issues
BUILTIN_PATTERNS = {
    'python': [
        PatternRule(
            id='bare-except',
            pattern='except:',
            message='Bare except catches all exceptions',
            fix='except Exception:',
            severity='error'
        ),
        PatternRule(
            id='print-statement',
            pattern='print($$$ARGS)',
            message='Consider using logging instead of print',
            severity='warning'
        ),
        PatternRule(
            id='mutable-default',
            pattern='def $FN($$$ARGS, $ARG=[]):',
            message='Mutable default argument',
            severity='error'
        ),
        PatternRule(
            id='hardcoded-password',
            pattern='pass' + 'word = "$VAL"',
            message='Hardcoded password detected',
            severity='error'
        ),
        PatternRule(
            id='eval-usage',
            pattern='eval($$$)',
            message='eval() is dangerous - consider alternatives',
            severity='error'
        ),
        PatternRule(
            id='exec-usage',
            pattern='exec($$$)',
            message='exec() is dangerous - consider alternatives',
            severity='error'
        ),
        PatternRule(
            id='format-string',
            pattern='"$STR".format($$$)',
            message='Consider using f-strings',
            fix='f"$STR"',
            severity='info'
        ),
        PatternRule(
            id='isinstance-type',
            pattern='type($VAR) == $TYPE',
            message='Use isinstance() instead of type() ==',
            fix='isinstance($VAR, $TYPE)',
            severity='warning'
        ),
    ],
    'javascript': [
        PatternRule(
            id='console-log',
            pattern='console.log($$$)',
            message='Remove console.log before production',
            severity='warning',
            language='javascript'
        ),
        PatternRule(
            id='var-usage',
            pattern='var $NAME = $VAL',
            message='Use const or let instead of var',
            fix='const $NAME = $VAL',
            severity='warning',
            language='javascript'
        ),
        PatternRule(
            id='double-equals',
            pattern='$A == $B',
            message='Use === for strict equality',
            fix='$A === $B',
            severity='warning',
            language='javascript'
        ),
    ],
    'typescript': [
        PatternRule(
            id='any-type',
            pattern=': any',
            message='Avoid using any type',
            severity='warning',
            language='typescript'
        ),
    ],
}


def search_pattern(
    pattern: str,
    path: Path,
    language: str = "python"
) -> List[PatternMatch]:
    """Search for pattern in code."""
    results = []

    if ASTGREP_AVAILABLE:
        return _astgrep_search(pattern, path, language)

    # Fallback to regex-based search
    return _regex_search(pattern, path)


def _astgrep_search(
    pattern: str,
    path: Path,
    language: str
) -> List[PatternMatch]:
    """Search using ast-grep."""
    results = []

    try:
        cmd = [
            ASTGREP_BIN,
            '--pattern', pattern,
            '--json',
            str(path)
        ]

        if language:
            cmd.extend(['--lang', language])

        proc = subprocess.run(cmd, capture_output=True, text=True)

        if proc.returncode == 0 and proc.stdout:
            for line in proc.stdout.strip().split('\n'):
                if line:
                    try:
                        match = json.loads(line)
                        results.append(PatternMatch(
                            path=Path(match.get('file', '')),
                            line=match.get('range', {}).get('start', {}).get('line', 0),
                            column=match.get('range', {}).get('start', {}).get('column', 0),
                            text=match.get('text', ''),
                            matched_text=match.get('text', ''),
                            pattern=pattern
                        ))
                    except json.JSONDecodeError:
                        pass

    except Exception as e:
        Console.warn(f"ast-grep error: {e}")

    return results


def _regex_search(pattern: str, path: Path) -> List[PatternMatch]:
    """Fallback regex-based search."""
    results = []

    # Convert ast-grep pattern to rough regex
    regex = pattern
    regex = re.escape(regex)
    regex = regex.replace(r'\$\$\$', '.*')  # $$$ matches anything
    regex = regex.replace(r'\$', r'\w+')     # $ matches identifier

    try:
        files = [path] if path.is_file() else list(path.rglob('*.py'))

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        if re.search(regex, line):
                            results.append(PatternMatch(
                                path=file_path,
                                line=i,
                                column=0,
                                text=line.strip(),
                                matched_text=line.strip(),
                                pattern=pattern
                            ))
            except Exception:
                pass

    except Exception:
        pass

    return results


def apply_fix(
    pattern: str,
    replacement: str,
    path: Path,
    language: str = "python",
    dry_run: bool = True
) -> int:
    """Apply fix pattern to files."""
    fixed = 0

    if ASTGREP_AVAILABLE:
        return _astgrep_fix(pattern, replacement, path, language, dry_run)

    # Fallback to regex
    return _regex_fix(pattern, replacement, path, dry_run)


def _astgrep_fix(
    pattern: str,
    replacement: str,
    path: Path,
    language: str,
    dry_run: bool
) -> int:
    """Apply fix using ast-grep."""
    cmd = [
        ASTGREP_BIN,
        '--pattern', pattern,
        '--rewrite', replacement,
    ]

    if not dry_run:
        cmd.append('--update-all')

    cmd.extend(['--lang', language, str(path)])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        # Count matches
        return proc.stdout.count('\n')
    except Exception:
        return 0


def _regex_fix(
    pattern: str,
    replacement: str,
    path: Path,
    dry_run: bool
) -> int:
    """Fallback regex-based fix."""
    fixed = 0

    # Convert patterns
    regex = pattern.replace('$$$', '(.*)').replace('$', r'(\w+)')
    repl = replacement.replace('$$$', r'\1').replace('$', r'\1')

    files = [path] if path.is_file() else list(path.rglob('*.py'))

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            new_content, count = re.subn(regex, repl, content)

            if count > 0:
                fixed += count
                if not dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
        except Exception:
            pass

    return fixed


def run_rules(
    rules: List[PatternRule],
    path: Path
) -> List[PatternMatch]:
    """Run multiple pattern rules."""
    all_matches = []

    for rule in rules:
        matches = search_pattern(rule.pattern, path, rule.language)
        for match in matches:
            match.pattern = f"{rule.id}: {rule.message}"
        all_matches.extend(matches)

    return all_matches


def get_builtin_rules(language: str = "python") -> List[PatternRule]:
    """Get built-in rules for language."""
    return BUILTIN_PATTERNS.get(language, [])


def is_astgrep_available() -> bool:
    """Check if ast-grep is available."""
    return ASTGREP_AVAILABLE


def main():
    """CLI entry point."""
    Console.header("ast-grep Wrapper")

    if ASTGREP_AVAILABLE:
        Console.ok(f"ast-grep available: {ASTGREP_BIN}")
    else:
        Console.warn("ast-grep not found, using regex fallback")

    args = [a for a in sys.argv[1:] if not a.startswith('-')]

    if len(args) < 2:
        Console.info("Usage: python astgrep.py <pattern> <path>")
        Console.info("\nBuilt-in rules:")
        for lang, rules in BUILTIN_PATTERNS.items():
            Console.info(f"\n  {lang}:")
            for rule in rules:
                Console.info(f"    - {rule.id}: {rule.message}")
        return 1

    pattern = args[0]
    path = Path(args[1])

    if not path.exists():
        Console.fail(f"Path not found: {path}")
        return 1

    Console.info(f"Pattern: {pattern}")
    Console.info(f"Path: {path}")

    matches = search_pattern(pattern, path)

    Console.info(f"Found {len(matches)} matches")

    for match in matches[:20]:
        print(f"  {match.path}:{match.line}: {match.text[:60]}...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
