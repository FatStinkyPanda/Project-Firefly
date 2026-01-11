"""
Unified Index Manager
=====================
Run all indexes at once for complete codebase intelligence.

Usage:
    python mcp.py index-all      # Full reindex
    python mcp.py index-all --what  # Show what's indexed
"""

from datetime import datetime
from pathlib import Path
import json
import sys
import time

from .utils import Console, find_project_root


def run_all_indexes(root: Path = None, verbose: bool = True) -> dict:
    """Run all indexes and return summary."""
    root = root or find_project_root() or Path.cwd()

    if verbose:
        Console.header("Full Index Build")
        Console.info(f"Indexing {root}...")

    start_time = time.time()
    results = {}

    # 1. Semantic code index
    if verbose:
        Console.info("1/7 Semantic code index...")
    try:
        from .vector_store import VectorStore
        store = VectorStore(root / '.mcp' / 'vector_index')
        count = store.index_codebase(root)
        results['semantic'] = {'status': 'ok', 'items': count}
    except Exception as e:
        results['semantic'] = {'status': 'error', 'error': str(e)}

    # 2. Git history index
    if verbose:
        Console.info("2/7 Git history index...")
    try:
        from .git_index import index_git_history
        index = index_git_history(root, since="3 months")
        results['git'] = {'status': 'ok', 'commits': index.get('commit_count', 0)}
    except Exception as e:
        results['git'] = {'status': 'error', 'error': str(e)}

    # 3. TODO/FIXME index
    if verbose:
        Console.info("3/7 TODO/FIXME index...")
    try:
        from .todo_index import index_todos
        index = index_todos(root)
        results['todos'] = {'status': 'ok', 'items': index.get('total', 0)}
    except Exception as e:
        results['todos'] = {'status': 'error', 'error': str(e)}

    # 4. Impact graph
    if verbose:
        Console.info("4/7 Dependency impact graph...")
    try:
        from .impact import save_impact_graph
        save_impact_graph(root)
        results['impact'] = {'status': 'ok'}
    except Exception as e:
        results['impact'] = {'status': 'error', 'error': str(e)}

    # 5. Documentation index
    if verbose:
        Console.info("5/7 Documentation index...")
    try:
        from .doc_index import index_documentation
        index = index_documentation(root)
        results['docs'] = {'status': 'ok', 'items': index.get('total_items', 0)}
    except Exception as e:
        results['docs'] = {'status': 'error', 'error': str(e)}

    # 6. Config index
    if verbose:
        Console.info("6/7 Config index...")
    try:
        from .config_index import index_configs
        index = index_configs(root)
        results['config'] = {'status': 'ok', 'vars': len(index.get('env_vars', {}))}
    except Exception as e:
        results['config'] = {'status': 'error', 'error': str(e)}

    # 7. Coverage (if available)
    if verbose:
        Console.info("7/7 Coverage index...")
    try:
        from .coverage_index import index_coverage
        index = index_coverage(root)
        results['coverage'] = {'status': 'ok', 'files': index.get('total_files', 0)}
    except Exception as e:
        results['coverage'] = {'status': 'skipped', 'reason': 'No coverage data'}

    elapsed = time.time() - start_time

    # Save summary
    summary = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'duration_seconds': round(elapsed, 2),
        'root': str(root),
        'indexes': results
    }

    summary_path = root / '.mcp' / 'index_summary.json'
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    if verbose:
        print("")
        Console.ok(f"Complete in {elapsed:.1f}s")
        show_index_status(root)

    return summary


def show_index_status(root: Path = None):
    """Show what's currently indexed."""
    root = root or find_project_root() or Path.cwd()
    mcp_dir = root / '.mcp'

    print("\n## Index Status")
    print("")

    indexes = [
        ('vector_index', 'Semantic Code', 'chunks.json'),
        ('git_index.json', 'Git History', None),
        ('todo_index.json', 'TODOs/FIXMEs', None),
        ('impact_graph.json', 'Impact Graph', None),
        ('doc_index.json', 'Documentation', None),
        ('config_index.json', 'Config', None),
        ('coverage_index.json', 'Coverage', None),
    ]

    for idx_name, display_name, sub_file in indexes:
        idx_path = mcp_dir / idx_name

        if sub_file:
            idx_path = idx_path / sub_file

        if idx_path.exists():
            size = idx_path.stat().st_size
            size_str = f"{size / 1024:.1f}KB" if size > 1024 else f"{size}B"
            print(f"  ✓ {display_name:20} ({size_str})")
        else:
            print(f"  ✗ {display_name:20} (not indexed)")


def main():
    """CLI entry point."""
    root = find_project_root() or Path.cwd()

    if '--what' in sys.argv or '--status' in sys.argv:
        Console.header("Index Status")
        show_index_status(root)
        return 0

    if '--quick' in sys.argv:
        # Quick mode: only semantic + todos
        Console.header("Quick Index")

        try:
            from .vector_store import VectorStore
            store = VectorStore(root / '.mcp' / 'vector_index')
            store.index_codebase(root)
        except Exception:
            pass

        try:
            from .todo_index import index_todos
            index_todos(root)
        except Exception:
            pass

        Console.ok("Quick index complete")
        return 0

    # Full index
    run_all_indexes(root, verbose=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
