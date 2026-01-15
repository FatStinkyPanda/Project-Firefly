"""
Architecture Validator
======================
Enforce architectural patterns and layer separation.

Usage:
    python architecture.py [path] [--config arch.json]
    python -m scripts.architecture src/
"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import ast
import re
import sys

from .utils import (
    find_python_files,
    find_project_root,
    parse_file,
    Console
)


@dataclass
class LayerRule:
    """A layer dependency rule."""
    layer: str
    can_depend_on: List[str]
    patterns: List[str]  # Path patterns for this layer


@dataclass
class ArchViolation:
    """An architecture violation."""
    path: Path
    line: int
    severity: str  # 'error', 'warning'
    category: str
    message: str
    from_layer: Optional[str] = None
    to_layer: Optional[str] = None


@dataclass
class ArchReport:
    """Architecture analysis report."""
    violations: List[ArchViolation] = field(default_factory=list)
    layer_mapping: Dict[str, str] = field(default_factory=dict)
    dependencies: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))

    @property
    def errors(self) -> List[ArchViolation]:
        return [v for v in self.violations if v.severity == 'error']

    def to_markdown(self) -> str:
        lines = [
            "# Architecture Analysis",
            "",
            "## Layer Structure",
            "",
            "```mermaid",
            "graph TD",
        ]

        # Add layer nodes
        layers_seen = set()
        for layer in self.layer_mapping.values():
            if layer and layer not in layers_seen:
                lines.append(f'    {layer}["{layer}"]')
                layers_seen.add(layer)

        # Add dependencies
        for from_layer, to_layers in self.dependencies.items():
            for to_layer in to_layers:
                if from_layer and to_layer:
                    lines.append(f'    {from_layer} --> {to_layer}')

        lines.extend(["```", ""])

        # Summary
        lines.extend([
            "## Summary",
            "",
            f"- **Modules analyzed:** {len(self.layer_mapping)}",
            f"- **Violations:** {len(self.violations)}",
            f"- **Errors:** {len(self.errors)}",
            "",
        ])

        # Violations
        if self.violations:
            lines.extend(["## Violations", ""])

            for v in self.violations:
                emoji = "[ERROR]" if v.severity == 'error' else "[WARN]"
                lines.append(f"### {emoji} {v.category}")
                lines.append(f"**File:** `{v.path}:{v.line}`")
                lines.append("")
                lines.append(v.message)
                if v.from_layer and v.to_layer:
                    lines.append(f"**Dependency:** {v.from_layer} -> {v.to_layer}")
                lines.append("")

        return "\n".join(lines)


# Default layer rules (can be customized)
DEFAULT_RULES = [
    LayerRule(
        layer='test',
        can_depend_on=['controller', 'service', 'repository', 'model', 'util'],
        patterns=['*test*', '*mock*', '*fixture*']
    ),
    LayerRule(
        layer='main',
        can_depend_on=['controller', 'service', 'repository', 'model', 'util'],
        patterns=['main', 'app', 'run', 'cli']
    ),
    LayerRule(
        layer='controller',
        can_depend_on=['service', 'model', 'util'],
        patterns=['*controller*', '*handler*', '*route*', 'app.api*', 'app.view*']
    ),
    LayerRule(
        layer='service',
        can_depend_on=['repository', 'model', 'util'],
        patterns=['*service*', '*manager*', '*logic*']
    ),
    LayerRule(
        layer='repository',
        can_depend_on=['model', 'util'],
        patterns=['*repository*', '*dao*', '*dal*']
    ),
    LayerRule(
        layer='model',
        can_depend_on=['util'],
        patterns=['*model*', '*entity*', '*schema*', '*dto*']
    ),
    LayerRule(
        layer='util',
        can_depend_on=[],
        patterns=['*util*', '*helper*', '*common*', '*lib*']
    ),
]


def detect_layer(path: Path, rules: List[LayerRule]) -> Optional[str]:
    """Detect the layer a module belongs to based on path patterns."""
    name = path.stem.lower()
    parts = [p.lower() for p in path.parts]

    for rule in rules:
        for pattern in rule.patterns:
            # Convert glob to regex
            regex = pattern.replace('*', '.*')
            if re.search(regex, name) or any(re.search(regex, p) for p in parts):
                return rule.layer

    return None


class ImportAnalyzer(ast.NodeVisitor):
    """Analyze imports for architecture violations."""

    def __init__(self, path: Path, layer: Optional[str], rules: List[LayerRule]):
        self.path = path
        self.layer = layer
        self.rules = rules
        self.violations: List[ArchViolation] = []
        self.imports: Set[str] = set()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.add(alias.name)
            self._check_import(alias.name, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.imports.add(node.module)
            self._check_import(node.module, node.lineno)
        self.generic_visit(node)

    def _check_import(self, module: str, lineno: int):
        if not self.layer:
            return

        # Get allowed dependencies for current layer
        allowed = set()
        for rule in self.rules:
            if rule.layer == self.layer:
                allowed = set(rule.can_depend_on)
                break

        # Check if import violates layer rules
        module_lower = module.lower()
        for rule in self.rules:
            for pattern in rule.patterns:
                regex = pattern.replace('*', '.*')
                if re.search(regex, module_lower):
                    imported_layer = rule.layer

                    if imported_layer != self.layer and imported_layer not in allowed:
                        self.violations.append(ArchViolation(
                            path=self.path,
                            line=lineno,
                            severity='error',
                            category='Layer Violation',
                            message=f"'{self.layer}' layer should not depend on '{imported_layer}' layer",
                            from_layer=self.layer,
                            to_layer=imported_layer
                        ))
                    break


class NamingConventionChecker:
    """Check naming conventions by layer."""

    CONVENTIONS = {
        'controller': ['Controller', 'Handler', 'View', 'Router', 'Api', 'Manager'],
        'service': ['Service', 'Manager', 'Logic', 'Settings', 'Response'],
        'repository': ['Repository', 'Repo', 'DAO', 'Dal'],
        'model': ['Model', 'Entity', 'Schema', 'DTO', 'Base', 'Create', 'Read', 'Update', 'Item', 'Info', 'Status', 'Payload', 'Login', 'Response', 'Request', 'Analytics', 'Performance', 'Risk', 'Grade', 'Token', 'WithStudent', 'Account', 'Institution', 'Classroom', 'Assignment', 'Announcement', 'Subscription', 'Transaction', 'GameSave', 'BugReport', 'Product', 'Permission', 'Enrollment', 'Submission', 'Condition', 'Link', 'Jurisdiction', 'Log', 'Message', 'Cache', 'Category', 'Image', 'Review', 'Question', 'Option', 'Answer', 'Module', 'Progress', 'Type'],
    }

    def __init__(self, path: Path, layer: Optional[str]):
        self.path = path
        self.layer = layer
        self.violations: List[ArchViolation] = []

    def check(self, tree: ast.Module):
        if not self.layer or self.layer not in self.CONVENTIONS or self.layer == 'test':
            return

        expected = self.CONVENTIONS[self.layer]

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name.startswith('_') or node.name == 'Config':
                    continue

                # Check if class name follows convention
                if not any(node.name.endswith(suffix) for suffix in expected):
                    self.violations.append(ArchViolation(
                        path=self.path,
                        line=node.lineno,
                        severity='warning',
                        category='Naming Convention',
                        message=f"Class '{node.name}' in '{self.layer}' layer should end with: {', '.join(expected)}"
                    ))


def analyze_file(
    path: Path,
    rules: List[LayerRule]
) -> Tuple[Optional[str], List[ArchViolation], Set[str]]:
    """Analyze a file for architecture violations."""
    violations = []
    imports = set()

    layer = detect_layer(path, rules)

    tree = parse_file(path)
    if tree is None:
        return layer, violations, imports

    # Import analysis
    import_analyzer = ImportAnalyzer(path, layer, rules)
    import_analyzer.visit(tree)
    violations.extend(import_analyzer.violations)
    imports = import_analyzer.imports

    # Naming conventions
    naming = NamingConventionChecker(path, layer)
    naming.check(tree)
    violations.extend(naming.violations)

    return layer, violations, imports


def analyze_architecture(
    root: Path,
    rules: List[LayerRule] = None,
    exclude_patterns: List[str] = None
) -> ArchReport:
    """Analyze project architecture."""
    if rules is None:
        rules = DEFAULT_RULES

    report = ArchReport()

    Console.info(f"Analyzing architecture in {root}...")

    files = list(find_python_files(root, exclude_patterns))
    Console.info(f"Found {len(files)} Python files")

    for path in files:
        layer, violations, imports = analyze_file(path, rules)

        # Track layer mapping
        report.layer_mapping[str(path)] = layer or 'unknown'

        # Track violations
        report.violations.extend(violations)

        # Track dependencies
        if layer:
            for imp in imports:
                for rule in rules:
                    for pattern in rule.patterns:
                        regex = pattern.replace('*', '.*')
                        if re.search(regex, imp.lower()):
                            report.dependencies[layer].add(rule.layer)
                            break

    return report


def main():
    """CLI entry point."""
    Console.header("Architecture Validator")

    # Parse args
    strict = '--strict' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('-')]

    if args:
        path = Path(args[0])
    else:
        path = find_project_root() or Path.cwd()

    if not path.exists():
        Console.fail(f"Path not found: {path}")
        return 1

    Console.info(f"Analyzing: {path}")

    report = analyze_architecture(path)

    print(report.to_markdown())

    # Summary
    if report.errors:
        Console.fail(f"Found {len(report.errors)} architecture violations")
        return 1
    elif report.violations:
        if strict:
            Console.fail(f"Found {len(report.violations)} warnings (strict mode)")
            return 1
        else:
            Console.warn(f"Found {len(report.violations)} warnings")
    else:
        Console.ok("Architecture is clean")

    return 0


if __name__ == "__main__":
    sys.exit(main())
