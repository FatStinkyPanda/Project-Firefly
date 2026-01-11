"""
Smart Context Loader
====================
Extract relevant context from codebases for AI agents with token budgets.

Usage:
    python context.py "query" [path] [--tokens 4000]
    python -m scripts.context "authentication" src/
"""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import ast
import math
import re
import sys

from .utils import (
    find_python_files,
    find_project_root,
    parse_file,
    analyze_module,
    get_changed_files,
    run_git_command,
    Console
)


@dataclass
class ContextItem:
    """A piece of context from the codebase."""
    path: Path
    content: str
    relevance_score: float
    item_type: str  # 'function', 'class', 'file', 'docstring'
    line_start: int
    line_end: int
    tokens: int  # Estimated token count


@dataclass
class ContextResult:
    """Result of context extraction."""
    query: str
    items: List[ContextItem] = field(default_factory=list)
    total_tokens: int = 0
    files_scanned: int = 0

    def to_markdown(self) -> str:
        """Format context as markdown."""
        lines = [
            f"# Context for: {self.query}",
            "",
            f"**Files scanned:** {self.files_scanned}",
            f"**Total tokens:** {self.total_tokens}",
            f"**Items found:** {len(self.items)}",
            "",
        ]

        for item in self.items:
            lines.extend([
                f"## {item.item_type.title()}: {item.path}:{item.line_start}",
                f"**Relevance:** {item.relevance_score:.2f}",
                "",
                "```python",
                item.content,
                "```",
                "",
            ])

        return "\n".join(lines)


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough: 4 chars per token)."""
    return len(text) // 4


def tokenize_query(query: str) -> List[str]:
    """Tokenize query into searchable terms."""
    # Convert to lowercase and split on non-alphanumeric
    terms = re.findall(r'[a-z0-9]+', query.lower())

    # Expand common abbreviations
    expansions = {
        'auth': ['authentication', 'authorize', 'authorization'],
        'db': ['database', 'connection'],
        'api': ['endpoint', 'route', 'handler'],
        'cfg': ['config', 'configuration', 'settings'],
        'msg': ['message', 'notification'],
        'err': ['error', 'exception'],
        'req': ['request', 'require'],
        'res': ['response', 'result'],
    }

    expanded = list(terms)
    for term in terms:
        if term in expansions:
            expanded.extend(expansions[term])

    return expanded


def calculate_tf_idf(
    terms: List[str],
    document: str,
    all_documents: List[str]
) -> float:
    """Calculate TF-IDF relevance score."""
    doc_lower = document.lower()

    # Term frequency in this document
    tf_scores = []
    for term in terms:
        tf = doc_lower.count(term)
        if tf > 0:
            tf_scores.append(1 + math.log(tf))
        else:
            tf_scores.append(0)

    if not tf_scores or sum(tf_scores) == 0:
        return 0.0

    # Inverse document frequency
    idf_scores = []
    for term in terms:
        docs_with_term = sum(1 for doc in all_documents if term in doc.lower())
        if docs_with_term > 0:
            idf = math.log(len(all_documents) / docs_with_term)
            idf_scores.append(idf)
        else:
            idf_scores.append(0)

    # Combined TF-IDF
    score = sum(tf * idf for tf, idf in zip(tf_scores, idf_scores))
    return score


def get_recent_files(root: Path, limit: int = 10) -> List[Path]:
    """Get recently modified files from git."""
    output = run_git_command(
        ['log', '--name-only', '--format=', '-n', '50'],
        cwd=root
    )

    if not output:
        return []

    recent = []
    seen = set()
    for line in output.split('\n'):
        line = line.strip()
        if line and line.endswith('.py') and line not in seen:
            path = root / line
            if path.exists():
                recent.append(path)
                seen.add(line)
            if len(recent) >= limit:
                break

    return recent


def extract_function_context(
    path: Path,
    tree: ast.Module,
    source_lines: List[str]
) -> List[Tuple[str, int, int, str]]:
    """Extract function definitions with context."""
    results = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Get function signature and docstring
            start = node.lineno - 1
            end = node.end_lineno if node.end_lineno else start + 1

            # Include signature + docstring + first few lines
            content_lines = source_lines[start:min(end, start + 20)]
            content = '\n'.join(content_lines)

            results.append((node.name, start + 1, end, content))

    return results


def extract_class_context(
    path: Path,
    tree: ast.Module,
    source_lines: List[str]
) -> List[Tuple[str, int, int, str]]:
    """Extract class definitions with context."""
    results = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            start = node.lineno - 1
            end = node.end_lineno if node.end_lineno else start + 1

            # Include class definition + docstring + method signatures
            content_lines = source_lines[start:min(end, start + 30)]
            content = '\n'.join(content_lines)

            results.append((node.name, start + 1, end, content))

    return results


def load_context(
    query: str,
    root: Path,
    token_budget: int = 4000,
    exclude_patterns: List[str] = None
) -> ContextResult:
    """
    Load relevant context for a query.

    Args:
        query: Search query
        root: Root directory
        token_budget: Maximum tokens to return
        exclude_patterns: Patterns to exclude

    Returns:
        ContextResult with relevant items
    """
    result = ContextResult(query=query)

    Console.info(f"Searching for context: '{query}'")

    # Tokenize query
    terms = tokenize_query(query)
    Console.info(f"Search terms: {', '.join(terms)}")

    # Get all Python files
    files = list(find_python_files(root, exclude_patterns))
    result.files_scanned = len(files)

    Console.info(f"Scanning {len(files)} files...")

    # Get recent files for priority boost
    recent_files = set(get_recent_files(root))

    # Load all file contents for IDF calculation
    all_contents = []
    file_data = []

    for path in files:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                all_contents.append(content)
                file_data.append((path, content))
        except Exception:
            continue

    # Score and extract context items
    context_items = []

    for path, content in file_data:
        # Calculate base relevance
        relevance = calculate_tf_idf(terms, content, all_contents)

        if relevance == 0:
            continue

        # Boost for recent files
        if path in recent_files:
            relevance *= 1.5

        # Boost for filename match
        if any(term in path.name.lower() for term in terms):
            relevance *= 2.0

        # Parse and extract items
        tree = parse_file(path)
        if tree is None:
            continue

        source_lines = content.split('\n')

        # Extract functions
        for name, start, end, func_content in extract_function_context(path, tree, source_lines):
            item_relevance = relevance
            if any(term in name.lower() for term in terms):
                item_relevance *= 2.0

            context_items.append(ContextItem(
                path=path,
                content=func_content,
                relevance_score=item_relevance,
                item_type='function',
                line_start=start,
                line_end=end,
                tokens=estimate_tokens(func_content)
            ))

        # Extract classes
        for name, start, end, class_content in extract_class_context(path, tree, source_lines):
            item_relevance = relevance
            if any(term in name.lower() for term in terms):
                item_relevance *= 2.0

            context_items.append(ContextItem(
                path=path,
                content=class_content,
                relevance_score=item_relevance,
                item_type='class',
                line_start=start,
                line_end=end,
                tokens=estimate_tokens(class_content)
            ))

    # Sort by relevance
    context_items.sort(key=lambda x: x.relevance_score, reverse=True)

    # Fill token budget
    tokens_used = 0
    for item in context_items:
        if tokens_used + item.tokens <= token_budget:
            result.items.append(item)
            tokens_used += item.tokens

        if tokens_used >= token_budget:
            break

    result.total_tokens = tokens_used

    Console.info(f"Found {len(result.items)} relevant items ({tokens_used} tokens)")

    return result


def main():
    """CLI entry point."""
    Console.header("Smart Context Loader")

    # Parse args
    args = [a for a in sys.argv[1:] if not a.startswith('-')]

    token_budget = 4000
    for i, arg in enumerate(sys.argv):
        if arg == '--tokens' and i + 1 < len(sys.argv):
            try:
                token_budget = int(sys.argv[i + 1])
            except ValueError:
                pass

    if not args:
        Console.fail("Usage: mcp context <query> [path] [--tokens N]")
        print("\nExamples:")
        print('  mcp context "authentication"')
        print('  mcp context "database connection" src/')
        print('  mcp context "api handler" --tokens 8000')
        return 1

    query = args[0]

    if len(args) > 1:
        path = Path(args[1])
    else:
        path = find_project_root() or Path.cwd()

    if not path.exists():
        Console.fail(f"Path not found: {path}")
        return 1

    Console.info(f"Root: {path}")
    Console.info(f"Token budget: {token_budget}")

    result = load_context(query, path, token_budget)

    print(result.to_markdown())

    return 0


if __name__ == "__main__":
    sys.exit(main())
