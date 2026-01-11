"""
Security Auditor
================
Deep security analysis for Python code - OWASP, secrets, injection detection.

Usage:
    python security.py [path] [--strict]
    python -m scripts.security src/
"""

from dataclasses import dataclass, field
from enum import Enum
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


class Severity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class SecurityIssue:
    """A security finding."""
    path: Path
    line: int
    severity: Severity
    category: str
    title: str
    description: str
    cwe: Optional[str] = None  # CWE identifier
    fix: Optional[str] = None


@dataclass
class SecurityReport:
    """Complete security audit report."""
    issues: List[SecurityIssue] = field(default_factory=list)
    files_scanned: int = 0

    @property
    def critical(self) -> List[SecurityIssue]:
        return [i for i in self.issues if i.severity == Severity.CRITICAL]

    @property
    def high(self) -> List[SecurityIssue]:
        return [i for i in self.issues if i.severity == Severity.HIGH]

    def to_markdown(self) -> str:
        lines = [
            "# Security Audit Report",
            "",
            "## Summary",
            "",
            f"| Severity | Count |",
            f"|----------|-------|",
        ]

        for sev in Severity:
            count = len([i for i in self.issues if i.severity == sev])
            if count > 0:
                lines.append(f"| {sev.value} | {count} |")

        lines.extend(["", f"**Files Scanned:** {self.files_scanned}", ""])

        if not self.issues:
            lines.append("No security issues found.")
            return "\n".join(lines)

        # Group by severity
        for sev in Severity:
            items = [i for i in self.issues if i.severity == sev]
            if not items:
                continue

            lines.extend([f"## {sev.value}", ""])

            for issue in items:
                lines.append(f"### {issue.category}: {issue.title}")
                lines.append(f"**File:** `{issue.path}:{issue.line}`")
                if issue.cwe:
                    lines.append(f"**CWE:** {issue.cwe}")
                lines.append("")
                lines.append(issue.description)
                if issue.fix:
                    lines.append("")
                    lines.append(f"**Fix:** {issue.fix}")
                lines.append("")

        return "\n".join(lines)


# Secret patterns
SECRET_PATTERNS = [
    (r'(?i)password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
    (r'(?i)secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret"),
    (r'(?i)api_?key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
    (r'(?i)token\s*=\s*["\'][^"\']+["\']', "Hardcoded token"),
    (r'(?i)auth\s*=\s*["\'][^"\']+["\']', "Hardcoded auth"),
    (r'(?i)private_?key\s*=\s*["\'][^"\']+["\']', "Hardcoded private key"),
    (r'(?i)aws_?secret', "AWS secret reference"),
    (r'(?i)credentials\s*=\s*["\'][^"\']+["\']', "Hardcoded credentials"),
    (r'(?i)bearer\s+[a-z0-9]{20,}', "Bearer token in code"),
    (r'(?i)-----BEGIN'
     r'.*PRIVATE KEY-----', "Private key in code"),
]

# Dangerous functions
DANGEROUS_FUNCTIONS = {
    'eval': ("Code Injection", Severity.CRITICAL, "CWE-94",
             "eval() executes arbitrary code. Use ast.literal_eval() for data."),
    'exec': ("Code Injection", Severity.CRITICAL, "CWE-94",
             "exec() executes arbitrary code. Avoid if possible."),
    'compile': ("Code Injection", Severity.HIGH, "CWE-94",
                "compile() can be used to execute code. Review carefully."),
    '__import__': ("Dynamic Import", Severity.MEDIUM, "CWE-94",
                   "Dynamic imports can load malicious modules."),
    'pickle.loads': ("Insecure Deserialization", Severity.HIGH, "CWE-502",
                     "Pickle can execute arbitrary code. Use JSON instead."),
    'pickle.load': ("Insecure Deserialization", Severity.HIGH, "CWE-502",
                    "Pickle can execute arbitrary code. Use JSON instead."),
    'yaml.load': ("Insecure Deserialization", Severity.HIGH, "CWE-502",
                  "Use yaml.safe_load() instead of yaml.load()."),
    'marshal.loads': ("Insecure Deserialization", Severity.HIGH, "CWE-502",
                      "Marshal can execute code. Use JSON instead."),
    'shelve.open': ("Insecure Deserialization", Severity.MEDIUM, "CWE-502",
                    "Shelve uses pickle internally. Use with caution."),
    'subprocess.call': ("Command Injection Risk", Severity.MEDIUM, "CWE-78",
                        "Use subprocess with shell=False and argument lists."),
    'subprocess.Popen': ("Command Injection Risk", Severity.MEDIUM, "CWE-78",
                         "Use subprocess with shell=False and argument lists."),
    'os.system': ("Command Injection", Severity.HIGH, "CWE-78",
                  "os.system() is vulnerable to injection. Use subprocess."),
    'os.popen': ("Command Injection", Severity.HIGH, "CWE-78",
                 "os.popen() is vulnerable. Use subprocess.run() instead."),
}

# SQL patterns
SQL_INJECTION_PATTERNS = [
    r'execute\s*\(\s*["\'].*%s',
    r'execute\s*\(\s*["\'].*\+',
    r'execute\s*\(\s*f["\']',
    r'execute\s*\(\s*["\'].*\.format',
    r'cursor\.execute\s*\(\s*[^,]+\s*%\s*',
]


class SecurityAnalyzer(ast.NodeVisitor):
    """Analyze code for security issues."""

    def __init__(self, path: Path, source: str):
        self.path = path
        self.source = source
        self.source_lines = source.split('\n')
        self.issues: List[SecurityIssue] = []
        self._imports: Set[str] = set()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self._imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self._imports.add(node.module)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Check for dangerous function calls
        func_name = self._get_func_name(node.func)

        if func_name in DANGEROUS_FUNCTIONS:
            title, severity, cwe, desc = DANGEROUS_FUNCTIONS[func_name]
            self.issues.append(SecurityIssue(
                path=self.path,
                line=node.lineno,
                severity=severity,
                category="Dangerous Function",
                title=title,
                description=f"Use of {func_name}(): {desc}",
                cwe=cwe,
                fix=f"Review usage of {func_name}() and consider safer alternatives"
            ))

        # Check for shell=True
        if func_name in ('subprocess.call', 'subprocess.run', 'subprocess.Popen'):
            for keyword in node.keywords:
                if keyword.arg == 'shell':
                    if isinstance(keyword.value, ast.Constant) and keyword.value.value:
                        self.issues.append(SecurityIssue(
                            path=self.path,
                            line=node.lineno,
                            severity=Severity.HIGH,
                            category="Command Injection",
                            title="shell=True in subprocess",
                            description="Using shell=True allows command injection attacks",
                            cwe="CWE-78",
                            fix="Use shell=False with a list of arguments"
                        ))

        # Check for input() without validation
        if func_name == 'input':
            self.issues.append(SecurityIssue(
                path=self.path,
                line=node.lineno,
                severity=Severity.INFO,
                category="Input Validation",
                title="Unvalidated input",
                description="input() should be validated before use",
                fix="Add input validation and sanitization"
            ))

        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert):
        # Asserts are removed in optimized bytecode
        self.issues.append(SecurityIssue(
            path=self.path,
            line=node.lineno,
            severity=Severity.LOW,
            category="Security Control",
            title="Assert used for security check",
            description="Assert statements are removed when Python runs with -O flag",
            fix="Use proper if/raise for security checks"
        ))
        self.generic_visit(node)

    def _get_func_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return f"{node.value.id}.{node.attr}"
            return node.attr
        return ""


def check_secrets(path: Path, source: str) -> List[SecurityIssue]:
    """Check for hardcoded secrets."""
    issues = []
    lines = source.split('\n')

    for i, line in enumerate(lines, 1):
        # Skip comments
        stripped = line.strip()
        if stripped.startswith('#'):
            continue

        for pattern, title in SECRET_PATTERNS:
            if re.search(pattern, line):
                # Exclude obvious non-secrets
                if 'example' in line.lower() or 'test' in line.lower():
                    continue
                if '""' in line or "''" in line:  # Empty strings
                    continue
                if 'os.environ' in line or 'getenv' in line:
                    continue

                issues.append(SecurityIssue(
                    path=path,
                    line=i,
                    severity=Severity.CRITICAL,
                    category="Hardcoded Secret",
                    title=title,
                    description=f"Potential secret found: {line.strip()[:50]}...",
                    cwe="CWE-798",
                    fix="Use environment variables or secret management"
                ))
                break  # One issue per line

    return issues


def check_sql_injection(path: Path, source: str) -> List[SecurityIssue]:
    """Check for SQL injection patterns."""
    issues = []
    lines = source.split('\n')

    for i, line in enumerate(lines, 1):
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append(SecurityIssue(
                    path=path,
                    line=i,
                    severity=Severity.HIGH,
                    category="SQL Injection",
                    title="Potential SQL injection",
                    description="SQL query appears to use string formatting instead of parameterization",
                    cwe="CWE-89",
                    fix="Use parameterized queries with placeholders"
                ))
                break

    return issues


def audit_file(path: Path) -> List[SecurityIssue]:
    """Audit a single file for security issues."""
    issues = []

    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
    except Exception:
        return issues

    # AST-based analysis
    tree = parse_file(path)
    if tree:
        analyzer = SecurityAnalyzer(path, source)
        analyzer.visit(tree)
        issues.extend(analyzer.issues)

    # Pattern-based checks
    issues.extend(check_secrets(path, source))
    issues.extend(check_sql_injection(path, source))

    return issues


def security_audit(
    root: Path,
    strict: bool = False,
    exclude_patterns: List[str] = None
) -> SecurityReport:
    """Perform security audit on a project."""
    report = SecurityReport()

    Console.info(f"Security audit of {root}...")

    files = list(find_python_files(root, exclude_patterns))
    report.files_scanned = len(files)
    Console.info(f"Scanning {len(files)} files...")

    for path in files:
        issues = audit_file(path)

        # In strict mode, include all issues; otherwise filter INFO
        if strict:
            report.issues.extend(issues)
        else:
            report.issues.extend([i for i in issues if i.severity != Severity.INFO])

    return report


def main():
    """CLI entry point."""
    Console.header("Security Auditor")

    # Parse args
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    strict = '--strict' in sys.argv

    if args:
        path = Path(args[0])
    else:
        path = find_project_root() or Path.cwd()

    if not path.exists():
        Console.fail(f"Path not found: {path}")
        return 1

    Console.info(f"Auditing: {path}")
    Console.info(f"Mode: {'strict' if strict else 'standard'}")

    report = security_audit(path, strict=strict)

    print(report.to_markdown())

    # Summary
    if report.critical:
        Console.fail(f"CRITICAL: {len(report.critical)} critical issues found!")
    elif report.high:
        Console.warn(f"HIGH: {len(report.high)} high severity issues found")
    elif report.issues:
        Console.warn(f"Found {len(report.issues)} security issues")
    else:
        Console.ok("No security issues found")

    return 1 if report.critical or report.high else 0


if __name__ == "__main__":
    sys.exit(main())
