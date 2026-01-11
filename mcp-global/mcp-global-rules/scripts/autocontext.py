"""
Auto-Context Loader
===================
Automatically load relevant code context for AI agents.

Usage:
    python mcp.py context --auto      # Get auto-loaded context
    python mcp.py context --recent    # Context from recent files
"""

from collections import Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import os
import sys

from .utils import Console, find_project_root


@dataclass
class ContextCache:
    """Cache of context state."""
    recent_files: List[str] = field(default_factory=list)
    hot_files: Dict[str, int] = field(default_factory=dict)  # path -> access count
    last_query: str = ""
    last_task: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ContextCache':
        return cls(**data)


@dataclass
class ContextResult:
    """Result of context loading."""
    files: List[Tuple[str, str]]  # (path, content summary)
    token_count: int
    source: str  # 'recent', 'semantic', 'dependency'


def get_cache_path(root: Path = None) -> Path:
    """Get path to context cache."""
    root = root or find_project_root() or Path.cwd()
    return root / '.mcp' / 'memory' / 'context_cache.json'


def load_cache(root: Path = None) -> ContextCache:
    """Load context cache from disk."""
    cache_path = get_cache_path(root)

    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return ContextCache.from_dict(data)
        except Exception:
            pass

    return ContextCache()


def save_cache(cache: ContextCache, root: Path = None):
    """Save context cache to disk."""
    cache_path = get_cache_path(root)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    cache.timestamp = datetime.utcnow().isoformat() + 'Z'

    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache.to_dict(), f, indent=2)


def track_file_access(path: Path, root: Path = None):
    """Track that a file was accessed."""
    cache = load_cache(root)

    path_str = str(path)

    # Update recent files (max 20)
    if path_str in cache.recent_files:
        cache.recent_files.remove(path_str)
    cache.recent_files.insert(0, path_str)
    cache.recent_files = cache.recent_files[:20]

    # Update hot files
    cache.hot_files[path_str] = cache.hot_files.get(path_str, 0) + 1

    save_cache(cache, root)


def get_recent_context(
    limit: int = 5,
    max_lines: int = 50,
    root: Path = None
) -> ContextResult:
    """Get context from recently accessed files."""
    cache = load_cache(root)
    root = root or find_project_root() or Path.cwd()

    files = []
    token_count = 0

    for file_path in cache.recent_files[:limit]:
        path = Path(file_path)
        if not path.is_absolute():
            path = root / path

        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:max_lines]
                    content = ''.join(lines)
                    files.append((str(path), content))
                    token_count += len(content.split())
            except Exception:
                pass

    return ContextResult(files=files, token_count=token_count, source='recent')


def get_hot_context(
    limit: int = 5,
    max_lines: int = 50,
    root: Path = None
) -> ContextResult:
    """Get context from most frequently accessed files."""
    cache = load_cache(root)
    root = root or find_project_root() or Path.cwd()

    # Sort by access count
    sorted_files = sorted(cache.hot_files.items(), key=lambda x: x[1], reverse=True)

    files = []
    token_count = 0

    for file_path, _ in sorted_files[:limit]:
        path = Path(file_path)
        if not path.is_absolute():
            path = root / path

        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:max_lines]
                    content = ''.join(lines)
                    files.append((str(path), content))
                    token_count += len(content.split())
            except Exception:
                pass

    return ContextResult(files=files, token_count=token_count, source='hot')


def get_semantic_context(
    query: str,
    limit: int = 5,
    root: Path = None
) -> ContextResult:
    """Get context via semantic search."""
    root = root or find_project_root() or Path.cwd()

    files = []
    token_count = 0

    try:
        from .vector_store import VectorStore
        store = VectorStore(root / '.mcp' / 'vector_index')

        if store.load():
            results = store.search(query, k=limit)

            for result in results:
                files.append((result.chunk.path, result.chunk.content))
                token_count += len(result.chunk.content.split())
    except Exception:
        pass

    # Update cache with query
    cache = load_cache(root)
    cache.last_query = query
    save_cache(cache, root)

    return ContextResult(files=files, token_count=token_count, source='semantic')


def get_dependency_context(
    file_path: Path,
    root: Path = None
) -> ContextResult:
    """Get context from file dependencies (imports)."""
    root = root or find_project_root() or Path.cwd()

    files = []
    token_count = 0

    try:
        from .treesitter_utils import parse_file
        parsed = parse_file(file_path)

        for imp in parsed.imports:
            # Try to resolve import to file
            parts = imp.replace('from ', '').replace('import ', '').split()[0].split('.')

            for i in range(len(parts), 0, -1):
                possible_path = root / '/'.join(parts[:i]) + '.py'
                if possible_path.exists():
                    try:
                        with open(possible_path, 'r', encoding='utf-8') as f:
                            content = f.read()[:2000]
                            files.append((str(possible_path), content))
                            token_count += len(content.split())
                    except Exception:
                        pass
                    break
    except Exception:
        pass

    return ContextResult(files=files, token_count=token_count, source='dependency')


# ... (Previous imports kept)

def get_project_map(root: Path, budget: int) -> str:
    """Layer 1: Get high-level project map."""
    summary_path = root / "CODEBASE_SUMMARY.md"
    if summary_path.exists():
        try:
            content = summary_path.read_text(encoding='utf-8')
            # Extract Directory Structure section
            if "## Directory Structure" in content:
                structure = content.split("## Directory Structure")[1].split("##")[0]
                return f"# Project Map\n{structure[:budget]}"
            return content[:budget]
        except Exception:
            pass
    return ""

def get_auto_context(
    task: str = "",
    token_budget: int = 8000, # Increased default for deep context
    root: Path = None
) -> str:
    """Get hierarchically layered context for AI agent."""
    root = root or find_project_root() or Path.cwd()
    
    # Budget Allocation
    budget_map = int(token_budget * 0.05)
    budget_mem = int(token_budget * 0.10)
    budget_active = int(token_budget * 0.40)
    budget_semantic = token_budget - (budget_map + budget_mem + budget_active)

    layers = []

    # Layer 1: Project Map
    project_map = get_project_map(root, budget_map)
    if project_map:
        layers.append(project_map)

    # Layer 2: Memory
    memories = []
    try:
        from .memory import get_store
        store = get_store()
        recent_mems = store.recall(task) if task else store.list_all()
        recent_mems.sort(key=lambda m: m.updated or m.created, reverse=True)
        
        mem_tokens_used = 0
        for mem in recent_mems[:5]:
            encoded = f"[{mem.key}] {mem.value}"
            if mem_tokens_used + len(encoded.split()) < budget_mem:
                memories.append(encoded)
                mem_tokens_used += len(encoded.split())
    except Exception:
        pass
        
    if memories:
        layers.append("# Recent Memory & Decisions\n" + "\n".join(memories))

    # Layer 3: Active & Dependencies
    active_files = {} # path -> content
    active_tokens = 0
    
    # 3a. Recent Files (Active)
    recent = get_recent_context(limit=3, root=root)
    for path, content in recent.files:
        if active_tokens < budget_active:
            active_files[path] = content
            active_tokens += len(content.split())
            
            # 3b. Dependencies of Active
            try:
                from .deps import analyze_imports
                deps = analyze_imports(Path(path))
                if deps:
                    # Very simple heuristic: try to find local module file
                    for imp in list(deps.imports)[:2]:
                        # Try finding file
                        local_path = root / f"{imp.replace('.', '/')}.py"
                        if local_path.exists() and str(local_path) not in active_files:
                             dep_content = local_path.read_text(encoding='utf-8')[:1000]
                             if active_tokens + len(dep_content.split()) < budget_active:
                                 active_files[str(local_path)] = dep_content
                                 active_tokens += len(dep_content.split())
            except Exception:
                pass

    # Layer 4: Semantic Search
    semantic_content = []
    if task:
        semantic = get_semantic_context(task, limit=5, root=root)
        semantic_tokens = 0
        for path, content in semantic.files:
            if path not in active_files and semantic_tokens < budget_semantic:
                semantic_content.append(f"## {Path(path).name} (Relevant)\n# {path}\n```python\n{content}\n```")
                semantic_tokens += len(content.split())
    
    # Assemble
    final_output = ["# Deep Context Auto-Loader", ""]
    final_output.extend(layers)
    
    if active_files:
        final_output.append("# Active Context")
        for path, content in active_files.items():
            final_output.append(f"## {Path(path).name}\n# {path}\n```python\n{content[:2000]}\n```\n")
            
    if semantic_content:
        final_output.append("# Semantic Context")
        final_output.extend(semantic_content)
        
    return "\n".join(final_output)

# ... (Main function kept same, calling get_auto_context)


def update_task(task: str, root: Path = None):
    """Update current task in cache."""
    cache = load_cache(root)
    cache.last_task = task
    save_cache(cache, root)


def main():
    """CLI entry point."""
    Console.header("Auto-Context Loader")

    args = [a for a in sys.argv[1:] if not a.startswith('-')]

    root = find_project_root() or Path.cwd()

    if '--recent' in sys.argv:
        result = get_recent_context(root=root)
        Console.info(f"Recent files: {len(result.files)}")
        for path, _ in result.files:
            print(f"  - {path}")
        return 0

    if '--hot' in sys.argv:
        result = get_hot_context(root=root)
        Console.info(f"Hot files: {len(result.files)}")
        for path, _ in result.files:
            print(f"  - {path}")
        return 0

    if '--auto' in sys.argv or not args:
        task = ' '.join(args) if args else ""
        context = get_auto_context(task=task, root=root)
        print(context)
        return 0

    # Semantic search with query
    query = ' '.join(args)
    result = get_semantic_context(query, root=root)

    Console.info(f"Found {len(result.files)} relevant files for: {query}")
    for path, content in result.files:
        print(f"\n## {path}")
        print(content[:500])

    return 0


if __name__ == "__main__":
    sys.exit(main())
