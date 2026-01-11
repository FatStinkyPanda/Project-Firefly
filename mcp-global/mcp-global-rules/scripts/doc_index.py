"""
Documentation Index
====================
Index READMEs, docstrings, and module summaries.

Usage:
    python mcp.py doc-index
    python mcp.py doc-index --search "api"
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import ast
import json
import re
import sys

from .utils import Console, find_python_files, find_project_root


@dataclass
class DocItem:
    """A documentation item."""
    type: str  # 'readme', 'module', 'class', 'function'
    name: str
    path: str
    summary: str
    full_text: str = ""


def extract_module_docstring(file_path: Path) -> Optional[str]:
    """Extract module docstring from a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        return ast.get_docstring(tree)
    except Exception:
        return None


def extract_docstrings(file_path: Path) -> List[DocItem]:
    """Extract all docstrings from a file."""
    docs = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception:
        return docs

    # Module docstring
    module_doc = ast.get_docstring(tree)
    if module_doc:
        docs.append(DocItem(
            type='module',
            name=file_path.stem,
            path=str(file_path),
            summary=module_doc.split('\n')[0][:100],
            full_text=module_doc[:500]
        ))

    # Function and class docstrings
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            doc = ast.get_docstring(node)
            if doc:
                docs.append(DocItem(
                    type='function',
                    name=node.name,
                    path=str(file_path),
                    summary=doc.split('\n')[0][:100],
                    full_text=doc[:500]
                ))
        elif isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node)
            if doc:
                docs.append(DocItem(
                    type='class',
                    name=node.name,
                    path=str(file_path),
                    summary=doc.split('\n')[0][:100],
                    full_text=doc[:500]
                ))

    return docs


def find_readme_files(root: Path) -> List[Path]:
    """Find README files in project."""
    readmes = []
    patterns = ['README', 'README.md', 'README.rst', 'README.txt', 'DOCUMENTATION.md']

    for pattern in patterns:
        for readme in root.rglob(pattern):
            if '.git' not in str(readme) and 'node_modules' not in str(readme):
                readmes.append(readme)

    return readmes


def index_readme(readme_path: Path) -> DocItem:
    """Index a README file."""
    try:
        content = readme_path.read_text(encoding='utf-8', errors='ignore')

        # Get first paragraph as summary
        lines = content.split('\n')
        summary_lines = []
        for line in lines:
            if line.strip() and not line.startswith('#'):
                summary_lines.append(line)
                if len(summary_lines) >= 3:
                    break

        summary = ' '.join(summary_lines)[:200]

        return DocItem(
            type='readme',
            name=readme_path.name,
            path=str(readme_path),
            summary=summary,
            full_text=content[:2000]
        )
    except Exception:
        return None


def index_documentation(root: Path = None) -> Dict:
    """Build documentation index."""
    root = root or find_project_root() or Path.cwd()

    Console.info("Indexing documentation...")

    index = {
        "total_items": 0,
        "by_type": {"readme": 0, "module": 0, "class": 0, "function": 0},
        "items": []
    }

    # Index READMEs
    for readme in find_readme_files(root):
        item = index_readme(readme)
        if item:
            index["items"].append({
                "type": item.type,
                "name": item.name,
                "path": str(item.path),
                "summary": item.summary
            })
            index["by_type"]["readme"] += 1
            index["total_items"] += 1

    # Index Python docstrings
    exclude = ['node_modules', 'venv', '.venv', '__pycache__', '.git', 'vendor']
    for file_path in find_python_files(root, exclude):
        docs = extract_docstrings(file_path)
        for item in docs:
            index["items"].append({
                "type": item.type,
                "name": item.name,
                "path": str(item.path),
                "summary": item.summary
            })
            index["by_type"][item.type] += 1
            index["total_items"] += 1

    # Save index
    index_path = root / '.mcp' / 'doc_index.json'
    index_path.parent.mkdir(parents=True, exist_ok=True)

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)

    Console.ok(f"Indexed {index['total_items']} documentation items")

    return index


def search_docs(query: str, root: Path = None) -> List[DocItem]:
    """Search documentation index."""
    root = root or find_project_root() or Path.cwd()
    index_path = root / '.mcp' / 'doc_index.json'

    if not index_path.exists():
        index_documentation(root)

    with open(index_path, 'r') as f:
        index = json.load(f)

    results = []
    query_lower = query.lower()

    for item in index.get('items', []):
        if query_lower in item['name'].lower() or query_lower in item['summary'].lower():
            results.append(DocItem(
                type=item['type'],
                name=item['name'],
                path=item['path'],
                summary=item['summary']
            ))

    return results


def get_module_summary(module_path: Path) -> str:
    """Get summary of a module."""
    docs = extract_docstrings(module_path)

    lines = [f"# Module: {module_path.stem}", ""]

    # Module docstring
    module_docs = [d for d in docs if d.type == 'module']
    if module_docs:
        lines.append(module_docs[0].full_text)
        lines.append("")

    # Classes
    class_docs = [d for d in docs if d.type == 'class']
    if class_docs:
        lines.append("## Classes")
        for d in class_docs:
            lines.append(f"- **{d.name}**: {d.summary}")
        lines.append("")

    # Functions
    func_docs = [d for d in docs if d.type == 'function']
    if func_docs:
        lines.append("## Functions")
        for d in func_docs[:10]:
            lines.append(f"- **{d.name}**: {d.summary}")

    return '\n'.join(lines)


def main():
    """CLI entry point."""
    Console.header("Documentation Index")

    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    root = find_project_root() or Path.cwd()

    if '--index' in sys.argv:
        index_documentation(root)
        return 0

    if '--search' in sys.argv and args:
        query = args[0]
        results = search_docs(query, root)
        Console.info(f"Found {len(results)} results for '{query}':")
        for r in results[:15]:
            print(f"  [{r.type}] {r.name}: {r.summary[:50]}...")
        return 0

    if args:
        # Show module summary
        file_path = Path(args[0])
        if file_path.exists():
            summary = get_module_summary(file_path)
            print(summary)
    else:
        # Just index
        index_documentation(root)

    return 0


if __name__ == "__main__":
    sys.exit(main())
