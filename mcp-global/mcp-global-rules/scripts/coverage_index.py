"""
Coverage Index
==============
Track and index test coverage data.

Usage:
    python mcp.py coverage [file]
    python mcp.py coverage --uncovered
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
import json
import sys

from .utils import Console, find_project_root


@dataclass
class CoverageData:
    """Coverage data for a file."""
    file: str
    covered_lines: List[int] = field(default_factory=list)
    uncovered_lines: List[int] = field(default_factory=list)
    total_lines: int = 0
    coverage_pct: float = 0.0


def load_coverage_file(coverage_path: Path) -> Optional[Dict]:
    """Load coverage data from .coverage or coverage.json."""
    # Try JSON format
    json_path = coverage_path.parent / 'coverage.json'
    if json_path.exists():
        try:
            with open(json_path, 'r') as f:
                return json.load(f)
        except Exception:
            pass

    # Try coverage.py format
    if coverage_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(coverage_path))
            cursor = conn.cursor()

            # Query coverage data
            cursor.execute("SELECT file_id, path FROM file")
            files = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute("SELECT file_id, lineno FROM line_bits")
            lines = {}
            for file_id, lineno in cursor.fetchall():
                if file_id not in lines:
                    lines[file_id] = []
                lines[file_id].append(lineno)

            conn.close()

            return {
                "files": {files[fid]: {"covered": lns} for fid, lns in lines.items() if fid in files}
            }
        except Exception:
            pass

    return None


def get_file_coverage(file_path: Path, root: Path = None) -> Optional[CoverageData]:
    """Get coverage data for a specific file."""
    root = root or find_project_root() or Path.cwd()
    coverage_path = root / '.coverage'

    data = load_coverage_file(coverage_path)
    if not data:
        return None

    file_key = str(file_path.relative_to(root)) if file_path.is_absolute() else str(file_path)

    for key, file_data in data.get('files', {}).items():
        if file_key in key or key.endswith(file_key):
            covered = file_data.get('covered', file_data.get('executed_lines', []))
            total = file_data.get('total', len(covered) + len(file_data.get('missing', [])))
            missing = file_data.get('missing', file_data.get('uncovered', []))

            pct = (len(covered) / total * 100) if total > 0 else 0

            return CoverageData(
                file=file_key,
                covered_lines=covered,
                uncovered_lines=missing,
                total_lines=total,
                coverage_pct=pct
            )

    return None


def get_tests_for_file(file_path: Path, root: Path = None) -> List[str]:
    """Find tests that likely cover a file."""
    root = root or find_project_root() or Path.cwd()

    tests = []
    file_name = file_path.stem

    # Look for test files
    for test_file in root.rglob('test_*.py'):
        if file_name in test_file.stem or file_name in test_file.read_text(errors='ignore'):
            tests.append(str(test_file.relative_to(root)))

    for test_file in root.rglob('*_test.py'):
        if file_name in test_file.stem:
            tests.append(str(test_file.relative_to(root)))

    # Check tests/ directory
    tests_dir = root / 'tests'
    if tests_dir.exists():
        for test_file in tests_dir.rglob('*.py'):
            if file_name in test_file.stem:
                tests.append(str(test_file.relative_to(root)))

    return list(set(tests))


def suggest_tests_needed(file_path: Path, root: Path = None) -> List[str]:
    """Suggest what tests are needed for a file."""
    root = root or find_project_root() or Path.cwd()

    suggestions = []
    file_name = file_path.stem

    existing_tests = get_tests_for_file(file_path, root)

    if not existing_tests:
        suggestions.append(f"Create test file: tests/test_{file_name}.py")

    # Check coverage
    coverage = get_file_coverage(file_path, root)
    if coverage and coverage.uncovered_lines:
        suggestions.append(f"Add tests for uncovered lines: {coverage.uncovered_lines[:10]}")

    # Check for public functions without tests
    try:
        import ast
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                test_name = f"test_{node.name}"
                # Check if test exists
                found = False
                for test_file in existing_tests:
                    test_path = root / test_file
                    if test_path.exists():
                        content = test_path.read_text(errors='ignore')
                        if test_name in content:
                            found = True
                            break

                if not found:
                    suggestions.append(f"Add test for: {node.name}()")
    except Exception:
        pass

    return suggestions


def index_coverage(root: Path = None) -> Dict:
    """Build coverage index."""
    root = root or find_project_root() or Path.cwd()
    coverage_path = root / '.coverage'

    Console.info("Indexing coverage data...")

    data = load_coverage_file(coverage_path)
    if not data:
        Console.warn("No coverage data found. Run pytest --cov first.")
        return {}

    index = {
        "total_files": 0,
        "covered_files": 0,
        "average_coverage": 0.0,
        "files": {}
    }

    total_pct = 0.0

    for file_key, file_data in data.get('files', {}).items():
        covered = len(file_data.get('covered', file_data.get('executed_lines', [])))
        missing = len(file_data.get('missing', file_data.get('uncovered', [])))
        total = covered + missing

        pct = (covered / total * 100) if total > 0 else 0

        index["files"][file_key] = {
            "covered": covered,
            "missing": missing,
            "total": total,
            "percentage": round(pct, 1)
        }

        index["total_files"] += 1
        if pct > 0:
            index["covered_files"] += 1
        total_pct += pct

    if index["total_files"] > 0:
        index["average_coverage"] = round(total_pct / index["total_files"], 1)

    # Save index
    index_path = root / '.mcp' / 'coverage_index.json'
    index_path.parent.mkdir(parents=True, exist_ok=True)

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)

    Console.ok(f"Coverage: {index['average_coverage']}% across {index['total_files']} files")

    return index


def main():
    """CLI entry point."""
    Console.header("Coverage Index")

    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    root = find_project_root() or Path.cwd()

    if '--index' in sys.argv:
        index_coverage(root)
        return 0

    if '--suggest' in sys.argv and args:
        file_path = Path(args[0])
        suggestions = suggest_tests_needed(file_path, root)
        Console.info(f"Test suggestions for {file_path.name}:")
        for s in suggestions:
            print(f"  - {s}")
        return 0

    if args:
        file_path = Path(args[0])
        coverage = get_file_coverage(file_path, root)

        if coverage:
            print(f"Coverage: {coverage.coverage_pct:.1f}%")
            print(f"Covered lines: {len(coverage.covered_lines)}")
            if coverage.uncovered_lines:
                print(f"Uncovered: {coverage.uncovered_lines[:20]}")
        else:
            Console.warn("No coverage data for this file")

        tests = get_tests_for_file(file_path, root)
        if tests:
            print(f"\nRelated tests:")
            for t in tests:
                print(f"  - {t}")
    else:
        # Show summary
        index = index_coverage(root)
        if index.get('files'):
            print(f"\nLowest coverage files:")
            sorted_files = sorted(index['files'].items(), key=lambda x: x[1]['percentage'])
            for file_key, data in sorted_files[:10]:
                print(f"  {data['percentage']:5.1f}%  {Path(file_key).name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
