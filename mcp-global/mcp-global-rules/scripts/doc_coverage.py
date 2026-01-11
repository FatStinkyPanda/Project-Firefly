"""
Documentation Coverage Checker
==============================
Measure documentation coverage and identify undocumented code.

Usage:
    python doc_coverage.py [path] [--format google]
    python -m scripts.doc_coverage src/
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
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
class CoverageItem:
    """A single item that should have documentation."""
    path: Path
    name: str
    line: int
    item_type: str  # 'function', 'class', 'method', 'module'
    has_docstring: bool
    docstring_valid: bool = True
    issues: List[str] = field(default_factory=list)


@dataclass
class CoverageReport:
    """Documentation coverage report."""
    items: List[CoverageItem] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def documented(self) -> int:
        return sum(1 for i in self.items if i.has_docstring)

    @property
    def valid(self) -> int:
        return sum(1 for i in self.items if i.has_docstring and i.docstring_valid)

    @property
    def coverage_percent(self) -> float:
        return (self.documented / self.total * 100) if self.total > 0 else 0

    @property
    def undocumented(self) -> List[CoverageItem]:
        return [i for i in self.items if not i.has_docstring]

    @property
    def invalid(self) -> List[CoverageItem]:
        return [i for i in self.items if i.has_docstring and not i.docstring_valid]

    def to_markdown(self) -> str:
        lines = [
            "# Documentation Coverage Report",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Items | {self.total} |",
            f"| Documented | {self.documented} |",
            f"| Coverage | {self.coverage_percent:.1f}% |",
            f"| Valid Format | {self.valid} |",
            "",
        ]

        # Coverage bar
        filled = int(self.coverage_percent / 5)
        bar = "[" + "#" * filled + "-" * (20 - filled) + "]"
        lines.append(f"**Coverage:** {bar} {self.coverage_percent:.1f}%")
        lines.append("")

        # Undocumented items
        if self.undocumented:
            lines.append("## Undocumented Items")
            lines.append("")

            # Group by type
            by_type: Dict[str, List[CoverageItem]] = {}
            for item in self.undocumented:
                if item.item_type not in by_type:
                    by_type[item.item_type] = []
                by_type[item.item_type].append(item)

            for item_type, items in by_type.items():
                lines.append(f"### {item_type.title()}s ({len(items)})")
                lines.append("")
                for item in items[:20]:  # Limit display
                    lines.append(f"- `{item.name}` ({item.path}:{item.line})")
                if len(items) > 20:
                    lines.append(f"- ... and {len(items) - 20} more")
                lines.append("")

        # Invalid docstrings
        if self.invalid:
            lines.append("## Invalid Docstrings")
            lines.append("")
            for item in self.invalid[:10]:
                lines.append(f"- `{item.name}` ({item.path}:{item.line})")
                for issue in item.issues:
                    lines.append(f"  - {issue}")
            lines.append("")

        return "\n".join(lines)


class DocstringValidator:
    """Validate docstring format."""

    def __init__(self, format: str = 'google'):
        self.format = format

    def validate(self, docstring: str, node) -> Tuple[bool, List[str]]:
        """Validate docstring format."""
        issues = []

        if not docstring or not docstring.strip():
            return False, ["Empty docstring"]

        lines = docstring.strip().split('\n')

        # Check first line
        first_line = lines[0].strip()
        if not first_line:
            issues.append("First line is empty")
        elif not first_line.endswith('.') and not first_line.endswith('!'):
            issues.append("First line should end with period")

        # Check for function-specific requirements
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check Args section if function has parameters
            params = [a.arg for a in node.args.args if a.arg not in ('self', 'cls')]
            if params and 'Args:' not in docstring and 'Parameters:' not in docstring:
                issues.append(f"Missing Args section for: {', '.join(params)}")

            # Check Returns section if function returns something
            if node.returns and node.returns is not None:
                if 'Returns:' not in docstring and 'Return:' not in docstring:
                    issues.append("Missing Returns section")

        return len(issues) == 0, issues


class CoverageAnalyzer(ast.NodeVisitor):
    """Analyze documentation coverage."""

    def __init__(self, path: Path, validator: DocstringValidator):
        self.path = path
        self.validator = validator
        self.items: List[CoverageItem] = []
        self._in_class = False

    def visit_Module(self, node: ast.Module):
        # Check module docstring
        docstring = ast.get_docstring(node)
        self.items.append(CoverageItem(
            path=self.path,
            name=self.path.stem,
            line=1,
            item_type='module',
            has_docstring=docstring is not None
        ))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node):
        # Skip private/magic methods
        if node.name.startswith('_') and not node.name.startswith('__init__'):
            return

        docstring = ast.get_docstring(node)
        item_type = 'method' if self._in_class else 'function'

        item = CoverageItem(
            path=self.path,
            name=node.name,
            line=node.lineno,
            item_type=item_type,
            has_docstring=docstring is not None
        )

        if docstring:
            valid, issues = self.validator.validate(docstring, node)
            item.docstring_valid = valid
            item.issues = issues

        self.items.append(item)

    def visit_ClassDef(self, node: ast.ClassDef):
        # Skip private classes
        if node.name.startswith('_'):
            self.generic_visit(node)
            return

        docstring = ast.get_docstring(node)
        item = CoverageItem(
            path=self.path,
            name=node.name,
            line=node.lineno,
            item_type='class',
            has_docstring=docstring is not None
        )

        if docstring:
            valid, issues = self.validator.validate(docstring, node)
            item.docstring_valid = valid
            item.issues = issues

        self.items.append(item)

        # Visit methods
        old_in_class = self._in_class
        self._in_class = True
        self.generic_visit(node)
        self._in_class = old_in_class


def analyze_file(path: Path, validator: DocstringValidator) -> List[CoverageItem]:
    """Analyze documentation coverage in a file."""
    tree = parse_file(path)
    if tree is None:
        return []

    analyzer = CoverageAnalyzer(path, validator)
    analyzer.visit(tree)

    return analyzer.items


def check_coverage(
    root: Path,
    doc_format: str = 'google',
    exclude_patterns: List[str] = None
) -> CoverageReport:
    """Check documentation coverage in a project."""
    report = CoverageReport()
    validator = DocstringValidator(doc_format)

    Console.info(f"Checking documentation coverage in {root}...")

    files = list(find_python_files(root, exclude_patterns))
    Console.info(f"Found {len(files)} Python files")

    for path in files:
        items = analyze_file(path, validator)
        report.items.extend(items)

    return report


def main():
    """CLI entry point."""
    Console.header("Documentation Coverage Checker")

    # Parse args
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    doc_format = 'google'

    for i, arg in enumerate(sys.argv):
        if arg == '--format' and i + 1 < len(sys.argv):
            doc_format = sys.argv[i + 1]

    if args:
        path = Path(args[0])
    else:
        path = find_project_root() or Path.cwd()

    if not path.exists():
        Console.fail(f"Path not found: {path}")
        return 1

    Console.info(f"Analyzing: {path}")
    Console.info(f"Format: {doc_format}")

    report = check_coverage(path, doc_format)

    print(report.to_markdown())

    # Summary
    if report.coverage_percent >= 80:
        Console.ok(f"Coverage: {report.coverage_percent:.1f}%")
    elif report.coverage_percent >= 50:
        Console.warn(f"Coverage: {report.coverage_percent:.1f}% (target: 80%)")
    else:
        Console.fail(f"Coverage: {report.coverage_percent:.1f}% (target: 80%)")

    return 0 if report.coverage_percent >= 80 else 1


# Required for isinstance check in validator
from typing import Tuple


if __name__ == "__main__":
    sys.exit(main())
