"""
Migration Helper
================
Assist with Python version and framework migrations.

Usage:
    python migrate.py [path] [--target 3.11]
    python -m scripts.migrate src/
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
import ast
import re
import sys

from .utils import (
    find_python_files,
    find_project_root,
    parse_file,
    Console,
    format_as_markdown_table
)


@dataclass
class MigrationIssue:
    """A migration issue or suggestion."""
    path: Path
    line: int
    severity: str  # 'required', 'recommended', 'optional'
    category: str
    title: str
    description: str
    old_syntax: Optional[str] = None
    new_syntax: Optional[str] = None


@dataclass
class MigrationReport:
    """Complete migration report."""
    target_version: str
    issues: List[MigrationIssue] = field(default_factory=list)

    @property
    def required(self) -> List[MigrationIssue]:
        return [i for i in self.issues if i.severity == 'required']

    @property
    def recommended(self) -> List[MigrationIssue]:
        return [i for i in self.issues if i.severity == 'recommended']

    def to_markdown(self) -> str:
        lines = [
            "# Migration Report",
            "",
            f"**Target Version:** Python {self.target_version}",
            "",
            "## Summary",
            "",
            f"- **Required changes:** {len(self.required)}",
            f"- **Recommended changes:** {len(self.recommended)}",
            f"- **Total issues:** {len(self.issues)}",
            "",
        ]

        if not self.issues:
            lines.append("No migration issues found. Code is compatible.")
            return "\n".join(lines)

        for severity in ['required', 'recommended', 'optional']:
            items = [i for i in self.issues if i.severity == severity]
            if not items:
                continue

            lines.extend([f"## {severity.title()}", ""])

            for issue in items:
                lines.append(f"### {issue.title}")
                lines.append(f"**File:** `{issue.path}:{issue.line}`")
                lines.append(f"**Category:** {issue.category}")
                lines.append("")
                lines.append(issue.description)

                if issue.old_syntax and issue.new_syntax:
                    lines.extend([
                        "",
                        "```diff",
                        f"- {issue.old_syntax}",
                        f"+ {issue.new_syntax}",
                        "```",
                    ])
                lines.append("")

        return "\n".join(lines)


# Python 3.10+ features
PY310_FEATURES = {
    'match': "Match statements (structural pattern matching)",
    'TypeAlias': "Type alias syntax with TypeAlias",
    'ParamSpec': "ParamSpec for better callable types",
}

# Python 3.11+ features
PY311_FEATURES = {
    'ExceptionGroup': "Exception groups for concurrent exceptions",
    'except*': "except* for catching exception groups",
    'Self': "Self type for returning class instance",
    'Required': "Required[] for TypedDict fields",
    'NotRequired': "NotRequired[] for TypedDict fields",
}

# Deprecated patterns to modernize
DEPRECATED_PATTERNS = {
    'typing.List': ('list', '3.9+', 'Use builtin list[] instead of typing.List[]'),
    'typing.Dict': ('dict', '3.9+', 'Use builtin dict[] instead of typing.Dict[]'),
    'typing.Set': ('set', '3.9+', 'Use builtin set[] instead of typing.Set[]'),
    'typing.Tuple': ('tuple', '3.9+', 'Use builtin tuple[] instead of typing.Tuple[]'),
    'typing.Optional': ('X | None', '3.10+', 'Use X | None instead of Optional[X]'),
    'typing.Union': ('X | Y', '3.10+', 'Use X | Y instead of Union[X, Y]'),
}


class DeprecationAnalyzer(ast.NodeVisitor):
    """Analyze code for deprecated patterns."""

    def __init__(self, path: Path, target: str):
        self.path = path
        self.target = target
        self.issues: List[MigrationIssue] = []
        self._typing_imports: Set[str] = set()

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == 'typing':
            for alias in node.names:
                self._typing_imports.add(alias.name)

                # Check deprecated typing imports
                if alias.name in DEPRECATED_PATTERNS:
                    new, version, desc = DEPRECATED_PATTERNS[f'typing.{alias.name}']
                    if self._version_ge(version):
                        self.issues.append(MigrationIssue(
                            path=self.path,
                            line=node.lineno,
                            severity='recommended',
                            category='typing',
                            title=f"Deprecated: typing.{alias.name}",
                            description=desc,
                            old_syntax=f"from typing import {alias.name}",
                            new_syntax=f"# Use {new} directly"
                        ))

        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript):
        # Check for Optional[X] -> X | None
        if isinstance(node.value, ast.Attribute):
            if isinstance(node.value.value, ast.Name):
                if node.value.value.id == 'typing':
                    attr = node.value.attr
                    if attr in ('Optional', 'Union') and self._version_ge('3.10+'):
                        self.issues.append(MigrationIssue(
                            path=self.path,
                            line=node.lineno,
                            severity='recommended',
                            category='typing',
                            title=f"Modernize: typing.{attr}",
                            description=f"Python 3.10+ supports | syntax for unions",
                            old_syntax=f"typing.{attr}[...]",
                            new_syntax="X | Y | None"
                        ))

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Check for deprecated function calls
        func_name = self._get_func_name(node.func)

        # Check for old string formatting
        if func_name == 'format' or '%' in str(node):
            pass  # Would need more context

        self.generic_visit(node)

    def _get_func_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return ""

    def _version_ge(self, version: str) -> bool:
        """Check if target version is >= specified version."""
        target_parts = self.target.split('.')
        version_parts = version.replace('+', '').split('.')

        try:
            for t, v in zip(target_parts, version_parts):
                if int(t) > int(v):
                    return True
                elif int(t) < int(v):
                    return False
            return True
        except ValueError:
            return False


class SyntaxModernizer(ast.NodeVisitor):
    """Suggest syntax modernization."""

    def __init__(self, path: Path, source_lines: List[str], target: str):
        self.path = path
        self.source_lines = source_lines
        self.target = target
        self.issues: List[MigrationIssue] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Check for missing type hints
        if not node.returns and not node.name.startswith('_'):
            self.issues.append(MigrationIssue(
                path=self.path,
                line=node.lineno,
                severity='optional',
                category='type_hints',
                title=f"Add return type to {node.name}",
                description="Adding type hints improves code quality and IDE support"
            ))

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # Check for walrus operator opportunities in Python 3.8+
        pass

        self.generic_visit(node)


class StringFormatAnalyzer(ast.NodeVisitor):
    """Check string formatting patterns."""

    def __init__(self, path: Path, source_lines: List[str]):
        self.path = path
        self.source_lines = source_lines
        self.issues: List[MigrationIssue] = []

    def visit_BinOp(self, node: ast.BinOp):
        # Check for % string formatting
        if isinstance(node.op, ast.Mod):
            if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                self.issues.append(MigrationIssue(
                    path=self.path,
                    line=node.lineno,
                    severity='optional',
                    category='string_format',
                    title="Modernize string formatting",
                    description="Consider using f-strings for better readability",
                    old_syntax='"%s" % value',
                    new_syntax='f"{value}"'
                ))

        self.generic_visit(node)


def analyze_file(
    path: Path,
    target: str
) -> List[MigrationIssue]:
    """Analyze a file for migration issues."""
    issues = []

    tree = parse_file(path)
    if tree is None:
        return issues

    try:
        with open(path, 'r', encoding='utf-8') as f:
            source_lines = f.readlines()
    except Exception:
        return issues

    # Run analyzers
    deprecation = DeprecationAnalyzer(path, target)
    deprecation.visit(tree)
    issues.extend(deprecation.issues)

    modernizer = SyntaxModernizer(path, source_lines, target)
    modernizer.visit(tree)
    issues.extend(modernizer.issues)

    string_format = StringFormatAnalyzer(path, source_lines)
    string_format.visit(tree)
    issues.extend(string_format.issues)

    return issues


def check_migration(
    root: Path,
    target: str = "3.11",
    exclude_patterns: List[str] = None
) -> MigrationReport:
    """Check project for migration issues."""
    report = MigrationReport(target_version=target)

    Console.info(f"Checking migration to Python {target}...")

    files = list(find_python_files(root, exclude_patterns))
    Console.info(f"Found {len(files)} Python files")

    for path in files:
        issues = analyze_file(path, target)
        report.issues.extend(issues)

    return report


def main():
    """CLI entry point."""
    Console.header("Migration Helper")

    # Parse args
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    target = "3.11"

    for i, arg in enumerate(sys.argv):
        if arg == '--target' and i + 1 < len(sys.argv):
            target = sys.argv[i + 1]

    if args:
        path = Path(args[0])
    else:
        path = find_project_root() or Path.cwd()

    if not path.exists():
        Console.fail(f"Path not found: {path}")
        return 1

    Console.info(f"Analyzing: {path}")
    Console.info(f"Target version: Python {target}")

    report = check_migration(path, target)

    print(report.to_markdown())

    # Summary
    if report.required:
        Console.warn(f"Found {len(report.required)} required changes")
    elif report.recommended:
        Console.info(f"Found {len(report.recommended)} recommended changes")
    else:
        Console.ok("Code is ready for migration")

    return 0


if __name__ == "__main__":
    sys.exit(main())
