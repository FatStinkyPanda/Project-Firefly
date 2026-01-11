"""
Smart File Finder
=================
Find files by natural language queries and patterns.

Usage:
    python finder.py "authentication" [path]
    python -m scripts.finder "database handler"
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import sys

from .utils import (
    find_python_files,
    find_project_root,
    parse_file,
    analyze_module,
    run_git_command,
    Console
)


@dataclass
class SearchResult:
    """A search result."""
    path: Path
    score: float
    match_type: str  # 'filename', 'content', 'import', 'function', 'class'
    context: str
    line: Optional[int] = None


@dataclass
class SearchResults:
    """Collection of search results."""
    query: str
    results: List[SearchResult] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            f"# Search: {self.query}",
            "",
            f"**Found:** {len(self.results)} results",
            "",
        ]

        if not self.results:
            lines.append("No results found.")
            return "\n".join(lines)

        # Group by match type
        by_type: Dict[str, List[SearchResult]] = {}
        for r in self.results:
            if r.match_type not in by_type:
                by_type[r.match_type] = []
            by_type[r.match_type].append(r)

        type_order = ['filename', 'function', 'class', 'import', 'content']
        for match_type in type_order:
            items = by_type.get(match_type, [])
            if not items:
                continue

            lines.append(f"## {match_type.title()} Matches")
            lines.append("")

            for r in sorted(items, key=lambda x: x.score, reverse=True)[:10]:
                if r.line:
                    lines.append(f"- `{r.path}:{r.line}` (score: {r.score:.2f})")
                else:
                    lines.append(f"- `{r.path}` (score: {r.score:.2f})")
                lines.append(f"  {r.context[:100]}...")
            lines.append("")

        return "\n".join(lines)


# Query expansion patterns
QUERY_EXPANSIONS = {
    'auth': ['authentication', 'authorize', 'authorization', 'login', 'logout'],
    'db': ['database', 'connection', 'query', 'sql'],
    'api': ['endpoint', 'route', 'handler', 'controller'],
    'config': ['configuration', 'settings', 'options'],
    'test': ['testing', 'unittest', 'pytest', 'mock'],
    'user': ['account', 'profile', 'member'],
    'file': ['upload', 'download', 'storage', 'io'],
    'email': ['mail', 'notification', 'send'],
    'cache': ['caching', 'redis', 'memcache'],
    'log': ['logging', 'logger', 'debug'],
}


def expand_query(query: str) -> List[str]:
    """Expand query into search terms."""
    terms = re.findall(r'[a-z0-9]+', query.lower())
    expanded = list(terms)

    for term in terms:
        if term in QUERY_EXPANSIONS:
            expanded.extend(QUERY_EXPANSIONS[term])

    return list(set(expanded))


def score_filename_match(filename: str, terms: List[str]) -> float:
    """Score a filename against search terms."""
    name_lower = filename.lower()
    score = 0.0

    for term in terms:
        if term in name_lower:
            # Exact match gets higher score
            score += 2.0
            # Even higher if at word boundary
            if f"_{term}" in name_lower or name_lower.startswith(term):
                score += 1.0

    return score


def search_file_content(
    path: Path,
    terms: List[str]
) -> List[Tuple[int, str, float]]:
    """Search file content for terms."""
    matches = []

    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return matches

    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        score = sum(1.0 for term in terms if term in line_lower)
        if score > 0:
            matches.append((i, line.strip()[:100], score))

    return matches


def search_module_structure(
    path: Path,
    terms: List[str]
) -> List[SearchResult]:
    """Search module functions and classes."""
    results = []

    module = analyze_module(path)
    if module is None:
        return results

    # Search functions
    for func in module.functions:
        name_lower = func.name.lower()
        score = sum(2.0 for term in terms if term in name_lower)

        # Check docstring
        if func.docstring:
            doc_lower = func.docstring.lower()
            score += sum(0.5 for term in terms if term in doc_lower)

        if score > 0:
            results.append(SearchResult(
                path=path,
                score=score,
                match_type='function',
                context=f"def {func.name}(): {func.docstring or ''}",
                line=func.lineno
            ))

    # Search classes
    for cls in module.classes:
        name_lower = cls.name.lower()
        score = sum(2.0 for term in terms if term in name_lower)

        if cls.docstring:
            doc_lower = cls.docstring.lower()
            score += sum(0.5 for term in terms if term in doc_lower)

        if score > 0:
            results.append(SearchResult(
                path=path,
                score=score,
                match_type='class',
                context=f"class {cls.name}: {cls.docstring or ''}",
                line=cls.lineno
            ))

    # Search imports
    for imp in module.imports:
        if any(term in imp.lower() for term in terms):
            results.append(SearchResult(
                path=path,
                score=1.0,
                match_type='import',
                context=f"import {imp}",
                line=1
            ))

    return results


def find_files(
    query: str,
    root: Path,
    limit: int = 20,
    exclude_patterns: List[str] = None
) -> SearchResults:
    """Find files matching a query."""
    results = SearchResults(query=query)
    terms = expand_query(query)

    Console.info(f"Searching for: '{query}'")
    Console.info(f"Terms: {', '.join(terms)}")

    files = list(find_python_files(root, exclude_patterns))
    Console.info(f"Scanning {len(files)} files...")

    all_results = []

    for path in files:
        # Filename match
        filename_score = score_filename_match(path.name, terms)
        if filename_score > 0:
            all_results.append(SearchResult(
                path=path,
                score=filename_score,
                match_type='filename',
                context=path.name
            ))

        # Module structure search
        structure_results = search_module_structure(path, terms)
        all_results.extend(structure_results)

        # Content search (only if not found in structure)
        if not structure_results:
            content_matches = search_file_content(path, terms)
            for line_num, context, score in content_matches[:3]:  # Limit per file
                all_results.append(SearchResult(
                    path=path,
                    score=score,
                    match_type='content',
                    context=context,
                    line=line_num
                ))

    # Sort by score and limit
    all_results.sort(key=lambda x: x.score, reverse=True)
    results.results = all_results[:limit]

    return results


def main():
    """CLI entry point."""
    Console.header("Smart File Finder")

    # Parse args
    args = [a for a in sys.argv[1:] if not a.startswith('-')]

    if not args:
        Console.fail("Usage: mcp find <query> [path]")
        print("\nExamples:")
        print('  mcp find "authentication"')
        print('  mcp find "database handler"')
        print('  mcp find "api endpoint" src/')
        return 1

    query = args[0]

    if len(args) > 1:
        path = Path(args[1])
    else:
        path = find_project_root() or Path.cwd()

    if not path.exists():
        Console.fail(f"Path not found: {path}")
        return 1

    Console.info(f"Searching in: {path}")

    results = find_files(query, path)

    print(results.to_markdown())

    Console.ok(f"Found {len(results.results)} results")

    return 0


if __name__ == "__main__":
    sys.exit(main())
