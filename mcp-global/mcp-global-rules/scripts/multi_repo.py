"""
Multi-Repo Search
=================
Search across all registered projects.

Usage:
    python mcp.py search-all "query"
    python mcp.py repos --add /path/to/repo
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json
import sys

from .utils import Console, find_project_root


@dataclass
class RepoInfo:
    """Information about a registered repository."""
    path: str
    name: str
    added: str
    last_indexed: Optional[str] = None
    file_count: int = 0


@dataclass
class SearchResult:
    """A search result from multi-repo search."""
    repo: str
    file: str
    line: int
    content: str
    score: float


class MultiRepoStore:
    """Manage multiple repository indexes."""

    def __init__(self):
        home = Path.home()
        self.storage_path = home / '.mcp' / 'repos'
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.repos: Dict[str, RepoInfo] = {}
        self.load()

    def _config_path(self) -> Path:
        return self.storage_path / 'repos.json'

    def load(self):
        """Load repo list."""
        config = self._config_path()
        if config.exists():
            try:
                with open(config, 'r') as f:
                    data = json.load(f)
                    self.repos = {k: RepoInfo(**v) for k, v in data.items()}
            except Exception:
                pass

    def save(self):
        """Save repo list."""
        config = self._config_path()
        with open(config, 'w') as f:
            json.dump({k: asdict(v) for k, v in self.repos.items()}, f, indent=2)

    def add_repo(self, path: Path) -> bool:
        """Add a repository to track."""
        path = path.resolve()
        if not path.exists():
            return False

        key = str(path)

        # Count files
        file_count = sum(1 for _ in path.rglob('*.py'))

        self.repos[key] = RepoInfo(
            path=key,
            name=path.name,
            added=datetime.utcnow().isoformat() + 'Z',
            file_count=file_count
        )

        self.save()
        return True

    def remove_repo(self, path: str) -> bool:
        """Remove a repository."""
        if path in self.repos:
            del self.repos[path]
            self.save()
            return True
        return False

    def list_repos(self) -> List[RepoInfo]:
        """List all registered repos."""
        return list(self.repos.values())

    def search_all(self, query: str, limit: int = 20) -> List[SearchResult]:
        """Search across all repos."""
        results = []
        query_lower = query.lower()

        for repo_path, repo_info in self.repos.items():
            path = Path(repo_path)
            if not path.exists():
                continue

            # Search files
            for file_path in path.rglob('*.py'):
                if '.git' in str(file_path) or 'node_modules' in str(file_path):
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f, 1):
                            if query_lower in line.lower():
                                results.append(SearchResult(
                                    repo=repo_info.name,
                                    file=str(file_path.relative_to(path)),
                                    line=i,
                                    content=line.strip()[:100],
                                    score=1.0 if query == line.strip() else 0.5
                                ))

                                if len(results) >= limit * 2:
                                    break
                except Exception:
                    pass

        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def find_similar_code(self, code_snippet: str, limit: int = 10) -> List[SearchResult]:
        """Find similar code across repos."""
        results = []

        # Tokenize snippet
        tokens = set(code_snippet.lower().split())
        tokens = {t for t in tokens if len(t) > 2}

        if not tokens:
            return results

        for repo_path, repo_info in self.repos.items():
            path = Path(repo_path)
            if not path.exists():
                continue

            for file_path in path.rglob('*.py'):
                if '.git' in str(file_path):
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Calculate similarity
                    file_tokens = set(content.lower().split())
                    overlap = len(tokens & file_tokens) / len(tokens) if tokens else 0

                    if overlap > 0.3:  # At least 30% token overlap
                        results.append(SearchResult(
                            repo=repo_info.name,
                            file=str(file_path.relative_to(path)),
                            line=0,
                            content=f"Similarity: {overlap:.0%}",
                            score=overlap
                        ))
                except Exception:
                    pass

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]


# Global store
_store: Optional[MultiRepoStore] = None


def get_store() -> MultiRepoStore:
    global _store
    if _store is None:
        _store = MultiRepoStore()
    return _store


def main():
    """CLI entry point."""
    Console.header("Multi-Repo Search")

    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    store = get_store()

    Console.info(f"Registered repos: {len(store.repos)}")

    if '--add' in sys.argv and args:
        path = Path(args[0]).resolve()
        if store.add_repo(path):
            Console.ok(f"Added: {path}")
        else:
            Console.fail(f"Not found: {path}")
        return 0

    if '--remove' in sys.argv and args:
        if store.remove_repo(args[0]):
            Console.ok(f"Removed: {args[0]}")
        else:
            Console.fail(f"Not found: {args[0]}")
        return 0

    if '--list' in sys.argv or not args:
        repos = store.list_repos()
        if repos:
            print("\n## Registered Repositories")
            for repo in repos:
                print(f"  [{repo.name}] {repo.path}")
                print(f"    Files: {repo.file_count}, Added: {repo.added[:10]}")
        else:
            Console.warn("No repositories registered")
            Console.info("Add with: mcp repos --add /path/to/repo")
        return 0

    # Search
    query = ' '.join(args)
    Console.info(f"Searching: {query}")

    results = store.search_all(query)

    if results:
        Console.ok(f"Found {len(results)} results")
        for r in results[:15]:
            print(f"\n  [{r.repo}] {r.file}:{r.line}")
            print(f"  {r.content}")
    else:
        Console.warn("No results found")

    return 0


if __name__ == "__main__":
    sys.exit(main())
