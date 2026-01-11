"""
Auto-Docstring Generator
========================
Automatically add missing docstrings to Python functions and classes.

Usage:
    python auto_docs.py [path] [--write]
    python -m scripts.auto_docs [path] [--write]
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple
import ast
import sys

from .utils import (
    find_python_files,
    find_project_root,
    parse_file,
    get_type_annotation,
    Console
)


@dataclass
class DocstringSuggestion:
    """A suggested docstring for a function or class."""
    path: Path
    name: str
    lineno: int
    node_type: str  # 'function', 'class', 'method'
    docstring: str
    indent: str


def generate_function_docstring(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    indent: str = "    "
) -> str:
    """
    Generate a Google-style docstring for a function.

    Args:
        node: AST function node
        indent: Indentation to use

    Returns:
        Generated docstring string
    """
    lines = ['"""']

    # First line - brief description
    if node.name.startswith('_'):
        lines[0] += f"Private {'async ' if isinstance(node, ast.AsyncFunctionDef) else ''}function {node.name}."
    else:
        # Try to generate a meaningful description from the name
        name_parts = node.name.split('_')
        if name_parts[0] in ('get', 'fetch', 'retrieve'):
            desc = f"Get {' '.join(name_parts[1:])}."
        elif name_parts[0] in ('set', 'update'):
            desc = f"Set {' '.join(name_parts[1:])}."
        elif name_parts[0] in ('is', 'has', 'can', 'should'):
            desc = f"Check if {' '.join(name_parts[1:])}."
        elif name_parts[0] == 'create':
            desc = f"Create {' '.join(name_parts[1:])}."
        elif name_parts[0] == 'delete':
            desc = f"Delete {' '.join(name_parts[1:])}."
        elif name_parts[0] == 'process':
            desc = f"Process {' '.join(name_parts[1:])}."
        elif name_parts[0] == 'validate':
            desc = f"Validate {' '.join(name_parts[1:])}."
        elif name_parts[0] == 'parse':
            desc = f"Parse {' '.join(name_parts[1:])}."
        elif name_parts[0] == 'convert':
            desc = f"Convert {' '.join(name_parts[1:])}."
        elif name_parts[0] == 'calculate':
            desc = f"Calculate {' '.join(name_parts[1:])}."
        else:
            desc = f"{' '.join(name_parts).capitalize()}."

        lines[0] += desc.capitalize()

    # Collect args (skip 'self' and 'cls')
    args_info = []
    skip_args = {'self', 'cls'}

    for arg in node.args.args:
        if arg.arg in skip_args:
            continue

        arg_name = arg.arg
        arg_type = ""
        if arg.annotation:
            arg_type = get_type_annotation(arg.annotation)

        # Generate description based on name
        arg_desc = _generate_param_description(arg_name, arg_type)
        args_info.append((arg_name, arg_type, arg_desc))

    # Add Args section
    if args_info:
        lines.append("")
        lines.append("Args:")
        for arg_name, arg_type, arg_desc in args_info:
            if arg_type:
                lines.append(f"    {arg_name} ({arg_type}): {arg_desc}")
            else:
                lines.append(f"    {arg_name}: {arg_desc}")

    # Add Returns section
    if node.returns:
        return_type = get_type_annotation(node.returns)
        lines.append("")
        lines.append("Returns:")
        if return_type.lower() in ('none', 'nonetype'):
            lines.append("    None")
        elif return_type.startswith('bool'):
            lines.append(f"    {return_type}: True if successful, False otherwise.")
        elif return_type.startswith('list') or return_type.startswith('List'):
            lines.append(f"    {return_type}: List of results.")
        elif return_type.startswith('dict') or return_type.startswith('Dict'):
            lines.append(f"    {return_type}: Dictionary with results.")
        elif return_type.startswith('Optional'):
            lines.append(f"    {return_type}: Result if found, None otherwise.")
        else:
            lines.append(f"    {return_type}: The result.")

    # Check for raises
    for child in ast.walk(node):
        if isinstance(child, ast.Raise) and child.exc:
            if isinstance(child.exc, ast.Call) and isinstance(child.exc.func, ast.Name):
                if "Raises:" not in lines:
                    lines.append("")
                    lines.append("Raises:")
                lines.append(f"    {child.exc.func.id}: If an error occurs.")
                break

    lines.append('"""')

    return '\n'.join(f"{indent}{line}" if line else "" for line in lines)


def _generate_param_description(name: str, type_hint: str) -> str:
    """Generate a description for a parameter based on its name."""
    # Common patterns
    if name in ('path', 'filepath', 'file_path'):
        return "Path to the file."
    elif name in ('root', 'root_dir', 'directory', 'dir'):
        return "Root directory."
    elif name in ('data', 'content'):
        return "Input data."
    elif name in ('name', 'filename'):
        return "The name."
    elif name in ('key', 'id', 'identifier'):
        return "Unique identifier."
    elif name in ('value', 'val'):
        return "The value."
    elif name in ('config', 'settings', 'options'):
        return "Configuration options."
    elif name in ('callback', 'func', 'function'):
        return "Callback function."
    elif name in ('timeout', 'delay'):
        return "Timeout in seconds."
    elif name in ('count', 'limit', 'max', 'min'):
        return f"The {name} value."
    elif name.startswith('is_') or name.startswith('has_') or name.startswith('enable'):
        return "Flag to enable/disable."
    elif name.endswith('_list') or name.endswith('_items'):
        return f"List of {name.rsplit('_', 1)[0]}."
    elif name.endswith('_dict') or name.endswith('_map'):
        return f"Dictionary of {name.rsplit('_', 1)[0]}."
    else:
        return f"The {name.replace('_', ' ')}."


def generate_class_docstring(node: ast.ClassDef, indent: str = "    ") -> str:
    """
    Generate a Google-style docstring for a class.

    Args:
        node: AST class node
        indent: Indentation to use

    Returns:
        Generated docstring string
    """
    lines = ['"""']

    # First line - class description
    name_parts = []
    for i, char in enumerate(node.name):
        if char.isupper() and i > 0:
            name_parts.append(' ')
        name_parts.append(char.lower())

    desc = ''.join(name_parts).capitalize()
    lines[0] += f"{desc} class."

    # Check for __init__ to get attributes
    init_method = None
    for item in node.body:
        if isinstance(item, ast.FunctionDef) and item.name == '__init__':
            init_method = item
            break

    # Extract attributes from __init__
    if init_method:
        attrs = []
        for stmt in ast.walk(init_method):
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Attribute):
                        if isinstance(target.value, ast.Name) and target.value.id == 'self':
                            if not target.attr.startswith('_'):
                                attrs.append(target.attr)

        if attrs:
            lines.append("")
            lines.append("Attributes:")
            for attr in attrs[:5]:  # Limit to 5 attributes
                lines.append(f"    {attr}: The {attr.replace('_', ' ')}.")

    lines.append('"""')

    return '\n'.join(f"{indent}{line}" if line else "" for line in lines)


class DocstringAnalyzer(ast.NodeVisitor):
    """Analyze a module for missing docstrings."""

    def __init__(self, path: Path, source_lines: List[str]):
        self.path = path
        self.source_lines = source_lines
        self.suggestions: List[DocstringSuggestion] = []
        self._class_stack: List[str] = []

    def _get_indent(self, lineno: int) -> str:
        """Get the indentation of a line."""
        if lineno <= 0 or lineno > len(self.source_lines):
            return "    "
        line = self.source_lines[lineno - 1]
        return line[:len(line) - len(line.lstrip())]

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        """Check if a function needs a docstring."""
        # Skip private and dunder methods
        if node.name.startswith('__') and node.name.endswith('__'):
            return

        # Check if docstring exists
        if ast.get_docstring(node):
            return

        # Get indentation for the docstring
        body_indent = self._get_indent(node.lineno) + "    "

        # Generate docstring
        docstring = generate_function_docstring(node, body_indent)

        node_type = 'method' if self._class_stack else 'function'

        self.suggestions.append(DocstringSuggestion(
            path=self.path,
            name=node.name,
            lineno=node.lineno,
            node_type=node_type,
            docstring=docstring,
            indent=body_indent
        ))

    def visit_ClassDef(self, node: ast.ClassDef):
        """Check if a class needs a docstring."""
        # Skip private classes
        if node.name.startswith('_'):
            self.generic_visit(node)
            return

        # Check if docstring exists
        if not ast.get_docstring(node):
            body_indent = self._get_indent(node.lineno) + "    "
            docstring = generate_class_docstring(node, body_indent)

            self.suggestions.append(DocstringSuggestion(
                path=self.path,
                name=node.name,
                lineno=node.lineno,
                node_type='class',
                docstring=docstring,
                indent=body_indent
            ))

        # Visit methods
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()


def analyze_file_for_docstrings(path: Path) -> List[DocstringSuggestion]:
    """
    Analyze a file for missing docstrings.

    Args:
        path: Path to Python file

    Returns:
        List of docstring suggestions
    """
    tree = parse_file(path)
    if tree is None:
        return []

    try:
        with open(path, 'r', encoding='utf-8') as f:
            source_lines = f.readlines()
    except Exception:
        return []

    analyzer = DocstringAnalyzer(path, source_lines)
    analyzer.visit(tree)

    return analyzer.suggestions


def add_docstrings_to_file(path: Path, suggestions: List[DocstringSuggestion]) -> str:
    """
    Add docstrings to a file.

    Args:
        path: Path to Python file
        suggestions: List of docstring suggestions for this file

    Returns:
        Modified source code
    """
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Sort suggestions by line number in reverse order
    # so we can insert from bottom to top without affecting line numbers
    sorted_suggestions = sorted(suggestions, key=lambda s: s.lineno, reverse=True)

    for suggestion in sorted_suggestions:
        # Find the line with the function/class definition
        def_line = suggestion.lineno - 1  # Convert to 0-indexed

        # Find where to insert (after the definition line and any decorators)
        insert_line = def_line + 1

        # Skip past the colon and any existing pass/... statements
        while insert_line < len(lines):
            line = lines[insert_line].strip()
            if line and not line.startswith('#'):
                break
            insert_line += 1

        # Insert the docstring
        docstring_lines = suggestion.docstring.split('\n')
        for i, doc_line in enumerate(reversed(docstring_lines)):
            lines.insert(insert_line, doc_line + '\n')

    return ''.join(lines)


def generate_docstrings(
    root: Path,
    write: bool = False,
    exclude_patterns: List[str] = None
) -> Tuple[int, int]:
    """
    Generate docstrings for all Python files in a directory.

    Args:
        root: Root directory
        write: Whether to write changes to files
        exclude_patterns: Patterns to exclude

    Returns:
        Tuple of (files_with_missing, total_missing)
    """
    all_suggestions: List[DocstringSuggestion] = []
    files_with_missing = 0

    Console.info(f"Scanning for Python files in {root}...")

    files = list(find_python_files(root, exclude_patterns))
    Console.info(f"Found {len(files)} Python files")

    for path in files:
        suggestions = analyze_file_for_docstrings(path)
        if suggestions:
            files_with_missing += 1
            all_suggestions.extend(suggestions)

            if write:
                # Group suggestions by file
                modified = add_docstrings_to_file(path, suggestions)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(modified)
                Console.ok(f"Added {len(suggestions)} docstrings to {path.name}")

    return files_with_missing, len(all_suggestions)


def main():
    """CLI entry point."""
    Console.header("Auto-Docstring Generator")

    # Parse args
    write = '--write' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('-')]

    # Get path
    if args:
        path = Path(args[0])
    else:
        path = find_project_root() or Path.cwd()

    if not path.exists():
        Console.fail(f"Path not found: {path}")
        sys.exit(1)

    Console.info(f"Analyzing: {path}")
    Console.info(f"Write mode: {'ON' if write else 'OFF (use --write to apply changes)'}")

    files_with_missing, total_missing = generate_docstrings(path, write=write)

    print()
    if total_missing > 0:
        Console.warn(f"Found {total_missing} missing docstrings in {files_with_missing} files")
        if write:
            Console.ok("Docstrings have been added")
        else:
            Console.info("Run with --write to add docstrings")
    else:
        Console.ok("All functions and classes have docstrings")

    return 0 if total_missing == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
