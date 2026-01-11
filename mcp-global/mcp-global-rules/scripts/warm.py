"""
Warm-Up Command
===============
Pre-warm all indexes for faster AI agent responses.

Usage:
    python mcp.py warm
"""

from pathlib import Path
import sys
import time

from .utils import Console, find_project_root
from concurrent.futures import ThreadPoolExecutor, as_completed


def warm_all(root: Path = None) -> dict:
    """Pre-warm all indexes and caches."""
    root = root or find_project_root() or Path.cwd()

    Console.header("Warming Indexes")
    Console.info(f"Project: {root}")

    start_time = time.time()
    results = {}

    # Define warm-up tasks
    tasks = {
        'semantic': ('vector_store', 'VectorStore', 'index_codebase'),
        'todos': ('todo_index', 'index_todos', None),
        'impact': ('impact', 'save_impact_graph', None),
        'docs': ('doc_index', 'index_documentation', None),
        'config': ('config_index', 'index_configs', None),
        'context': ('autocontext', 'warm_context', None),
    }

    def run_task(name, module_name, func_or_class, method):
        try:
            import importlib
            module = importlib.import_module(f"scripts.{module_name}")

            if method:
                # Class with method
                cls = getattr(module, func_or_class)
                instance = cls(root / '.mcp' / 'vector_index')
                getattr(instance, method)(root)
            else:
                # Direct function
                func = getattr(module, func_or_class)
                func(root)

            return name, 'ok', None
        except Exception as e:
            return name, 'error', str(e)

    # Run tasks in parallel
    Console.info("Running warm-up tasks...")

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for name, (module, func, method) in tasks.items():
            future = executor.submit(run_task, name, module, func, method)
            futures[future] = name

        for future in as_completed(futures):
            name, status, error = future.result()
            results[name] = status

            if status == 'ok':
                Console.ok(f"Warmed: {name}")
            else:
                Console.warn(f"Skipped: {name}")

    elapsed = time.time() - start_time

    Console.ok(f"Warm-up complete in {elapsed:.1f}s")

    # Show status
    ok_count = sum(1 for s in results.values() if s == 'ok')
    print(f"\n{ok_count}/{len(tasks)} indexes warmed")

    return results


def main():
    """CLI entry point."""
    root = find_project_root() or Path.cwd()

    if '--quick' in sys.argv:
        # Quick warm - just semantic and todos
        Console.header("Quick Warm")

        try:
            from .vector_store import VectorStore
            store = VectorStore(root / '.mcp' / 'vector_index')
            store.index_codebase(root)
            Console.ok("Semantic index warmed")
        except Exception:
            pass

        try:
            from .todo_index import index_todos
            index_todos(root)
            Console.ok("TODO index warmed")
        except Exception:
            pass

        return 0

    warm_all(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
