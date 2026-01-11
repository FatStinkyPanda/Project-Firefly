"""
Bug Prediction
==============
Predict bugs before they happen based on code patterns.

Usage:
    python mcp.py predict-bugs [file]
    python mcp.py risk-score
"""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import ast
import json
import sys

from .utils import Console, find_python_files, find_project_root


@dataclass
class BugPrediction:
    """A predicted bug."""
    file: str
    line: int
    risk_level: str  # 'high', 'medium', 'low'
    category: str
    description: str
    confidence: float
    suggestion: str = ""


@dataclass
class RiskReport:
    """Risk assessment report."""
    total_risk_score: float
    risk_level: str
    predictions: List[BugPrediction] = field(default_factory=list)
    hotspots: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        level_label = {'high': '[HIGH]', 'medium': '[MEDIUM]', 'low': '[LOW]'}

        lines = [
            f"# Risk Report",
            "",
            f"**Overall Risk:** {level_label.get(self.risk_level, '')} {self.risk_level.upper()} ({self.total_risk_score:.1f}/100)",
            "",
        ]

        if self.predictions:
            lines.append("## Predictions")
            for pred in self.predictions[:10]:
                lines.append(f"- **{pred.category}** ({pred.risk_level}): {pred.description}")
                lines.append(f"  - {pred.file}:{pred.line}")
                if pred.suggestion:
                    lines.append(f"  - Fix: {pred.suggestion}")
            lines.append("")

        if self.hotspots:
            lines.append("## Hotspots")
            for hs in self.hotspots[:5]:
                lines.append(f"- {hs}")

        return '\n'.join(lines)


# Risk patterns
RISK_PATTERNS = {
    'complexity': {
        'threshold': 10,
        'weight': 2.0,
        'description': 'High cyclomatic complexity'
    },
    'nesting': {
        'threshold': 4,
        'weight': 1.5,
        'description': 'Deep nesting'
    },
    'function_length': {
        'threshold': 50,
        'weight': 1.0,
        'description': 'Long function'
    },
    'parameters': {
        'threshold': 5,
        'weight': 1.0,
        'description': 'Too many parameters'
    },
    'bare_except': {
        'weight': 3.0,
        'description': 'Bare except clause'
    },
    'no_error_handling': {
        'weight': 2.0,
        'description': 'No error handling in risky operation'
    },
    'magic_number': {
        'weight': 0.5,
        'description': 'Magic number'
    },
    'global_var': {
        'weight': 1.5,
        'description': 'Global variable mutation'
    }
}


class ComplexityAnalyzer(ast.NodeVisitor):
    """Analyze code complexity."""

    def __init__(self):
        self.complexity = 1
        self.max_nesting = 0
        self.current_nesting = 0
        self.function_lines = 0
        self.param_count = 0

    def visit_If(self, node):
        self.complexity += 1
        self._enter_nesting()
        self.generic_visit(node)
        self._exit_nesting()

    def visit_For(self, node):
        self.complexity += 1
        self._enter_nesting()
        self.generic_visit(node)
        self._exit_nesting()

    def visit_While(self, node):
        self.complexity += 1
        self._enter_nesting()
        self.generic_visit(node)
        self._exit_nesting()

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def _enter_nesting(self):
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)

    def _exit_nesting(self):
        self.current_nesting -= 1


class BugPredictor(ast.NodeVisitor):
    """Predict bugs in code."""

    def __init__(self, source_lines: List[str]):
        self.predictions: List[BugPrediction] = []
        self.source_lines = source_lines
        self.current_file = ""

    def analyze_function(self, node: ast.FunctionDef):
        """Analyze a function for bug risks."""
        # Complexity analysis
        analyzer = ComplexityAnalyzer()
        analyzer.visit(node)

        line_count = (node.end_lineno or node.lineno) - node.lineno
        param_count = len(node.args.args)

        # Check complexity
        if analyzer.complexity > RISK_PATTERNS['complexity']['threshold']:
            self.predictions.append(BugPrediction(
                file=self.current_file,
                line=node.lineno,
                risk_level='high' if analyzer.complexity > 20 else 'medium',
                category='complexity',
                description=f"Cyclomatic complexity {analyzer.complexity} in {node.name}()",
                confidence=0.8,
                suggestion="Break into smaller functions"
            ))

        # Check nesting
        if analyzer.max_nesting > RISK_PATTERNS['nesting']['threshold']:
            self.predictions.append(BugPrediction(
                file=self.current_file,
                line=node.lineno,
                risk_level='medium',
                category='nesting',
                description=f"Deep nesting ({analyzer.max_nesting} levels) in {node.name}()",
                confidence=0.7,
                suggestion="Extract nested logic into helper functions"
            ))

        # Check function length
        if line_count > RISK_PATTERNS['function_length']['threshold']:
            self.predictions.append(BugPrediction(
                file=self.current_file,
                line=node.lineno,
                risk_level='medium',
                category='function_length',
                description=f"Long function ({line_count} lines): {node.name}()",
                confidence=0.6,
                suggestion="Consider splitting into smaller functions"
            ))

        # Check parameter count
        if param_count > RISK_PATTERNS['parameters']['threshold']:
            self.predictions.append(BugPrediction(
                file=self.current_file,
                line=node.lineno,
                risk_level='low',
                category='parameters',
                description=f"Too many parameters ({param_count}): {node.name}()",
                confidence=0.5,
                suggestion="Consider using a configuration object"
            ))

    def visit_FunctionDef(self, node):
        self.analyze_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.analyze_function(node)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if node.type is None:
            self.predictions.append(BugPrediction(
                file=self.current_file,
                line=node.lineno,
                risk_level='high',
                category='bare_except',
                description="Bare except catches all exceptions",
                confidence=0.95,
                suggestion="Specify exception type: except Exception:"
            ))
        self.generic_visit(node)

    def visit_Global(self, node):
        self.predictions.append(BugPrediction(
            file=self.current_file,
            line=node.lineno,
            risk_level='medium',
            category='global_var',
            description=f"Global variable: {', '.join(node.names)}",
            confidence=0.6,
            suggestion="Consider using a class or passing as parameter"
        ))
        self.generic_visit(node)


def predict_bugs(file_path: Path) -> List[BugPrediction]:
    """Predict bugs in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
            lines = source.split('\n')

        tree = ast.parse(source)
    except Exception:
        return []

    predictor = BugPredictor(lines)
    predictor.current_file = str(file_path)
    predictor.visit(tree)

    return predictor.predictions


def predict_bugs_project(root: Path) -> List[BugPrediction]:
    """Predict bugs across project."""
    all_predictions = []

    exclude = ['node_modules', 'venv', '.venv', '__pycache__', '.git', 'vendor']

    for file_path in find_python_files(root, exclude):
        predictions = predict_bugs(file_path)
        all_predictions.extend(predictions)

    # Sort by risk level
    level_order = {'high': 0, 'medium': 1, 'low': 2}
    all_predictions.sort(key=lambda p: level_order.get(p.risk_level, 3))

    return all_predictions


def calculate_risk_score(predictions: List[BugPrediction]) -> float:
    """Calculate overall risk score (0-100)."""
    if not predictions:
        return 0.0

    score = 0.0
    for pred in predictions:
        weight = RISK_PATTERNS.get(pred.category, {}).get('weight', 1.0)
        level_mult = {'high': 3, 'medium': 2, 'low': 1}.get(pred.risk_level, 1)
        score += weight * level_mult * pred.confidence

    # Normalize to 0-100
    return min(100, score)


def get_risk_report(root: Path = None) -> RiskReport:
    """Generate risk report for project."""
    root = root or find_project_root() or Path.cwd()

    predictions = predict_bugs_project(root)
    score = calculate_risk_score(predictions)

    # Determine level
    if score >= 50:
        level = 'high'
    elif score >= 20:
        level = 'medium'
    else:
        level = 'low'

    # Find hotspots (files with most issues)
    file_counts = Counter(p.file for p in predictions)
    hotspots = [f"{path} ({count} issues)" for path, count in file_counts.most_common(5)]

    return RiskReport(
        total_risk_score=score,
        risk_level=level,
        predictions=predictions,
        hotspots=hotspots
    )


def main():
    """CLI entry point."""
    Console.header("Bug Prediction")

    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    root = find_project_root() or Path.cwd()

    if args:
        file_path = Path(args[0])
        if file_path.exists() and file_path.is_file():
            Console.info(f"Analyzing {file_path}...")
            predictions = predict_bugs(file_path)

            if predictions:
                Console.warn(f"Found {len(predictions)} potential issues")
                for pred in predictions:
                    level_color = {'high': '\033[91m', 'medium': '\033[93m', 'low': '\033[92m'}
                    nc = '\033[0m'
                    print(f"\n  {level_color.get(pred.risk_level, '')}{pred.risk_level.upper()}{nc}: {pred.category}")
                    print(f"  Line {pred.line}: {pred.description}")
                    if pred.suggestion:
                        print(f"  Suggestion: {pred.suggestion}")
            else:
                Console.ok("No high-risk patterns detected")
            return 0

    # Full project report
    Console.info(f"Analyzing {root}...")
    report = get_risk_report(root)

    print(report.to_markdown())

    return 0


if __name__ == "__main__":
    sys.exit(main())
