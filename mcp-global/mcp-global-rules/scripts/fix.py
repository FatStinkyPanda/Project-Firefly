"""
Auto-Fix Tool
=============
Automatically fix common code issues.

Usage:
    python fix.py [path] [--lint] [--format] [--imports]
    python -m scripts.fix src/
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
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
class FixResult:
    """Result of a fix operation."""
    path: Path
    fix_type: str
    original: str
    fixed: str
    line: int
    description: str


@dataclass
class FixReport:
    """Complete fix report."""
    fixes_applied: List[FixResult] = field(default_factory=list)
    files_modified: int = 0

    def to_markdown(self) -> str:
        lines = [
            "# Auto-Fix Report",
            "",
            f"**Files modified:** {self.files_modified}",
            f"**Fixes applied:** {len(self.fixes_applied)}",
            "",
        ]

        if not self.fixes_applied:
            lines.append("No fixes needed.")
            return "\n".join(lines)

        # Group by file
        by_file: Dict[Path, List[FixResult]] = {}
        for fix in self.fixes_applied:
            if fix.path not in by_file:
                by_file[fix.path] = []
            by_file[fix.path].append(fix)

        for path, fixes in by_file.items():
            lines.append(f"## {path}")
            lines.append("")
            for fix in fixes:
                lines.append(f"- **Line {fix.line}:** {fix.description}")
            lines.append("")

        return "\n".join(lines)


def sort_imports(content: str) -> Tuple[str, List[FixResult]]:
    """Sort and organize imports."""
    fixes = []
    lines = content.split('\n')

    # Find import block
    import_lines = []
    import_start = None
    import_end = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('import ') or stripped.startswith('from '):
            if import_start is None:
                import_start = i
            import_end = i
            import_lines.append((i, line))
        elif import_start is not None and stripped and not stripped.startswith('#'):
            break

    if not import_lines:
        return content, fixes

    # Group imports
    stdlib = []
    third_party = []
    local = []

    STDLIB = {
        'os', 'sys', 're', 'json', 'pathlib', 'typing', 'collections',
        'itertools', 'functools', 'datetime', 'time', 'logging', 'ast',
        'subprocess', 'threading', 'multiprocessing', 'queue', 'socket',
        'http', 'urllib', 'email', 'html', 'xml', 'configparser',
        'argparse', 'io', 'string', 'textwrap', 'copy', 'pprint',
        'dataclasses', 'abc', 'contextlib', 'warnings', 'traceback',
        'unittest', 'doctest', 'sqlite3', 'csv', 'pickle', 'shelve',
        'hashlib', 'hmac', 'secrets', 'random', 'math', 'statistics',
        'enum', 'tempfile', 'shutil', 'glob', 'fnmatch', 'gc', 'inspect',
    }

    for _, line in import_lines:
        stripped = line.strip()

        # Extract module name
        if stripped.startswith('from '):
            match = re.match(r'from\s+(\w+)', stripped)
            module = match.group(1) if match else ''
        else:
            match = re.match(r'import\s+(\w+)', stripped)
            module = match.group(1) if match else ''

        if module.startswith('.'):
            local.append(line)
        elif module in STDLIB:
            stdlib.append(line)
        else:
            third_party.append(line)

    # Sort each group
    stdlib.sort(key=lambda x: x.strip().lower())
    third_party.sort(key=lambda x: x.strip().lower())
    local.sort(key=lambda x: x.strip().lower())

    # Build new import block
    new_imports = []
    if stdlib:
        new_imports.extend(stdlib)
        new_imports.append('')
    if third_party:
        new_imports.extend(third_party)
        new_imports.append('')
    if local:
        new_imports.extend(local)

    # Remove extra blank lines
    while new_imports and not new_imports[-1].strip():
        new_imports.pop()

    # Replace in content
    new_lines = lines[:import_start] + new_imports + lines[import_end + 1:]
    new_content = '\n'.join(new_lines)

    if new_content != content:
        fixes.append(FixResult(
            path=Path(''),
            fix_type='imports',
            original='',
            fixed='',
            line=import_start + 1,
            description='Sorted and organized imports'
        ))

    return new_content, fixes


def fix_trailing_whitespace(content: str) -> Tuple[str, List[FixResult]]:
    """Remove trailing whitespace."""
    fixes = []
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        if line != line.rstrip():
            fixes.append(FixResult(
                path=Path(''),
                fix_type='whitespace',
                original=line,
                fixed=line.rstrip(),
                line=i + 1,
                description='Removed trailing whitespace'
            ))
            fixed_lines.append(line.rstrip())
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines), fixes


def fix_blank_lines(content: str) -> Tuple[str, List[FixResult]]:
    """Fix excessive blank lines."""
    fixes = []

    # Replace 3+ blank lines with 2
    pattern = r'\n{4,}'
    if re.search(pattern, content):
        content = re.sub(pattern, '\n\n\n', content)
        fixes.append(FixResult(
            path=Path(''),
            fix_type='formatting',
            original='',
            fixed='',
            line=0,
            description='Reduced excessive blank lines'
        ))

    # Ensure file ends with single newline
    if content and not content.endswith('\n'):
        content += '\n'
        fixes.append(FixResult(
            path=Path(''),
            fix_type='formatting',
            original='',
            fixed='',
            line=0,
            description='Added final newline'
        ))

    return content, fixes


def remove_unused_imports(path: Path, content: str) -> Tuple[str, List[FixResult]]:
    """Remove unused imports."""
    fixes = []

    tree = parse_file(path)
    if tree is None:
        return content, fixes

    # Find all imports
    imported_names = {}  # name -> line
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split('.')[0]
                imported_names[name] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != '*':
                    name = alias.asname or alias.name
                    imported_names[name] = node.lineno

    # Find all name usages
    used_names: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                used_names.add(node.value.id)

    # Find unused
    unused = set(imported_names.keys()) - used_names

    # Don't remove special imports
    unused -= {'__future__', 'TYPE_CHECKING'}

    if not unused:
        return content, fixes

    # Remove unused import lines
    lines = content.split('\n')
    new_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        should_remove = False

        for name in unused:
            if f'import {name}' in stripped or f'import {name},' in stripped:
                should_remove = True
                fixes.append(FixResult(
                    path=path,
                    fix_type='unused_import',
                    original=line,
                    fixed='',
                    line=i + 1,
                    description=f'Removed unused import: {name}'
                ))
                break

        if not should_remove:
            new_lines.append(line)

    return '\n'.join(new_lines), fixes


def fix_file(
    path: Path,
    fix_imports: bool = True,
    fix_whitespace: bool = True,
    fix_formatting: bool = True,
    fix_unused: bool = True,
    dry_run: bool = False
) -> List[FixResult]:
    """Fix issues in a single file."""
    all_fixes = []

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return all_fixes

    original = content

    # Apply fixes
    if fix_imports:
        content, fixes = sort_imports(content)
        for fix in fixes:
            fix.path = path
        all_fixes.extend(fixes)

    if fix_whitespace:
        content, fixes = fix_trailing_whitespace(content)
        for fix in fixes:
            fix.path = path
        all_fixes.extend(fixes)

    if fix_formatting:
        content, fixes = fix_blank_lines(content)
        for fix in fixes:
            fix.path = path
        all_fixes.extend(fixes)

    if fix_unused:
        content, fixes = remove_unused_imports(path, content)
        for fix in fixes:
            fix.path = path
        all_fixes.extend(fixes)

    # Write if changed
    if content != original and not dry_run:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    return all_fixes


def fix_project(
    root: Path,
    fix_imports: bool = True,
    fix_whitespace: bool = True,
    fix_formatting: bool = True,
    fix_unused: bool = True,
    dry_run: bool = False,
    exclude_patterns: List[str] = None
) -> FixReport:
    """Fix issues in a project."""
    report = FixReport()

    Console.info(f"Fixing issues in {root}...")
    if dry_run:
        Console.warn("DRY RUN - no files will be modified")

    files = list(find_python_files(root, exclude_patterns))
    Console.info(f"Found {len(files)} Python files")

    for path in files:
        fixes = fix_file(
            path,
            fix_imports=fix_imports,
            fix_whitespace=fix_whitespace,
            fix_formatting=fix_formatting,
            fix_unused=fix_unused,
            dry_run=dry_run
        )

        if fixes:
            report.files_modified += 1
            report.fixes_applied.extend(fixes)

    return report


def fix_staged_files(dry_run: bool = False) -> FixReport:
    """Fix only git staged files."""
    import subprocess

    report = FixReport()

    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
            capture_output=True, text=True
        )
        staged = [f.strip() for f in result.stdout.strip().split('\n') if f.strip().endswith('.py')]
    except Exception:
        return report

    if not staged:
        return report

    Console.info(f"Fixing {len(staged)} staged files...")

    for file_path in staged:
        path = Path(file_path)
        if path.exists():
            fixes = fix_file(path, dry_run=dry_run)
            if fixes:
                report.files_modified += 1
                report.fixes_applied.extend(fixes)

    return report


def main():
    """CLI entry point."""
    Console.header("Auto-Fix Tool")

    # Parse args
    args = [a for a in sys.argv[1:] if not a.startswith('-')]

    dry_run = '--dry-run' in sys.argv
    safe_only = '--safe' in sys.argv
    apply_mode = '--apply' in sys.argv
    staged_only = '--staged' in sys.argv

    # Safe mode: only whitespace, imports, formatting (no complex changes)
    if safe_only:
        fix_imports = True
        fix_format = True
        fix_lint = False  # Don't remove unused imports in safe mode
    else:
        fix_imports = '--imports' in sys.argv or not any(
            a in sys.argv for a in ['--imports', '--lint', '--format']
        )
        fix_format = '--format' in sys.argv or not any(
            a in sys.argv for a in ['--imports', '--lint', '--format']
        )
        fix_lint = '--lint' in sys.argv or not any(
            a in sys.argv for a in ['--imports', '--lint', '--format']
        )

    # Apply mode: actually apply fixes (not dry run)
    if apply_mode:
        dry_run = False

    if staged_only:
        report = fix_staged_files(dry_run=dry_run)
    else:
        if args:
            path = Path(args[0])
        else:
            path = find_project_root() or Path.cwd()

        if not path.exists():
            Console.fail(f"Path not found: {path}")
            return 1

        Console.info(f"Fixing: {path}")

        report = fix_project(
            path,
            fix_imports=fix_imports,
            fix_whitespace=fix_format,
            fix_formatting=fix_format,
            fix_unused=fix_lint,
            dry_run=dry_run
        )

    print(report.to_markdown())

    if report.fixes_applied:
        Console.ok(f"Applied {len(report.fixes_applied)} fixes to {report.files_modified} files")
    else:
        Console.ok("No fixes needed")

    return 0


if __name__ == "__main__":
    sys.exit(main())

