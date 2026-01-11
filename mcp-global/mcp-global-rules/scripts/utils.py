"""
MCP Global Rules - Shared Utilities
====================================
Core utility functions used by all AI agent enhancement tools.

Python 3.11+ compatible, uses only stdlib.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterator, Tuple
import ast
import json
import os
import subprocess


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FunctionInfo:
    """Information about a Python function."""
    name: str
    lineno: int
    end_lineno: int
    args: List[str]
    arg_types: Dict[str, str]
    return_type: Optional[str]
    docstring: Optional[str]
    is_async: bool = False
    is_method: bool = False
    decorators: List[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    """Information about a Python class."""
    name: str
    lineno: int
    end_lineno: int
    docstring: Optional[str]
    methods: List[FunctionInfo] = field(default_factory=list)
    bases: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)


@dataclass
class ModuleInfo:
    """Information about a Python module."""
    path: Path
    docstring: Optional[str]
    imports: List[str] = field(default_factory=list)
    from_imports: List[Tuple[str, List[str]]] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    global_vars: List[str] = field(default_factory=list)


@dataclass
class GitCommit:
    """Information about a git commit."""
    hash: str
    short_hash: str
    author: str
    date: str
    message: str
    body: str = ""
    files_changed: List[str] = field(default_factory=list)


# =============================================================================
# FILE DISCOVERY
# =============================================================================

def find_python_files(
    root: Path,
    exclude_patterns: List[str] = None
) -> Iterator[Path]:
    """
    Find all Python files in a directory tree.

    Args:
        root: Root directory to search
        exclude_patterns: Patterns to exclude (e.g., ['__pycache__', '.venv'])

    Yields:
        Path objects for each Python file found
    """
    if exclude_patterns is None:
        exclude_patterns = [
            '__pycache__', '.venv', 'venv', '.git', 'node_modules',
            '.eggs', '*.egg-info', 'dist', 'build', '.tox', '.pytest_cache'
        ]

    root = Path(root)
    if not root.exists():
        return

    for item in root.rglob('*.py'):
        # Check if any parent directory matches exclude patterns
        skip = False
        for part in item.parts:
            for pattern in exclude_patterns:
                if pattern.startswith('*'):
                    if part.endswith(pattern[1:]):
                        skip = True
                        break
                elif part == pattern:
                    skip = True
                    break
            if skip:
                break

        if not skip:
            yield item


def find_project_root(start: Path = None) -> Optional[Path]:
    """
    Find the project root by looking for common markers.

    Args:
        start: Starting directory (defaults to cwd)

    Returns:
        Project root path or None
    """
    # 1. Try environment variable set by mcp.py
    mcp_root_env = os.environ.get('MCP_ROOT')

    if start is None:
        start = Path.cwd()

    markers = ['.git', 'pyproject.toml', 'setup.py', 'setup.cfg', '.mcp']

    # helper to check markers
    def check_dir(d: Path) -> bool:
        for marker in markers:
            if (d / marker).exists():
                return True
        return False

    # A. Search up from the MCP package location first (Strongest signal)
    # If mcp-global-rules is inside a project, that's likely the project we want.
    if mcp_root_env:
        mcp_root = Path(mcp_root_env).resolve()

        # Check parent of mcp-global-rules (common case)
        if check_dir(mcp_root.parent):
            return mcp_root.parent

        # Search up from mcp_root
        curr = mcp_root.parent
        while curr != curr.parent:
            if check_dir(curr):
                return curr
            curr = curr.parent

    # B. Search up from start (cwd)
    if start is None:
        start = Path.cwd()

    current = Path(start).resolve()
    while current != current.parent:
        if check_dir(current):
            return current
        current = current.parent

    # C. Last resort: if we have mcp_root, return its parent even without markers
    if mcp_root_env:
        return Path(mcp_root_env).resolve().parent

    return None


def get_package_root() -> Path:
    """Get the absolute path to the mcp-global-rules package directory."""
    mcp_root_env = os.environ.get('MCP_ROOT')
    if mcp_root_env:
        return Path(mcp_root_env).resolve()

    # Fallback to __file__ resolution
    return Path(__file__).resolve().parent.parent


# =============================================================================
# AST PARSING
# =============================================================================

def parse_file(path: Path) -> Optional[ast.Module]:
    """
    Parse a Python file into an AST.

    Args:
        path: Path to Python file

    Returns:
        AST module or None if parsing fails
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
        return ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return None


def get_type_annotation(node: ast.expr) -> str:
    """Convert an AST type annotation to a string."""
    if node is None:
        return ""

    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Constant):
        return repr(node.value)
    elif isinstance(node, ast.Subscript):
        base = get_type_annotation(node.value)
        if isinstance(node.slice, ast.Tuple):
            args = ', '.join(get_type_annotation(e) for e in node.slice.elts)
        else:
            args = get_type_annotation(node.slice)
        return f"{base}[{args}]"
    elif isinstance(node, ast.Attribute):
        return f"{get_type_annotation(node.value)}.{node.attr}"
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        # Union type with | operator
        left = get_type_annotation(node.left)
        right = get_type_annotation(node.right)
        return f"{left} | {right}"
    else:
        return ast.unparse(node) if hasattr(ast, 'unparse') else ""


def extract_function_info(node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
    """
    Extract information from a function definition node.

    Args:
        node: AST function definition node

    Returns:
        FunctionInfo dataclass
    """
    # Get arguments
    args = []
    arg_types = {}

    for arg in node.args.args:
        arg_name = arg.arg
        args.append(arg_name)
        if arg.annotation:
            arg_types[arg_name] = get_type_annotation(arg.annotation)

    # Get return type
    return_type = None
    if node.returns:
        return_type = get_type_annotation(node.returns)

    # Get docstring
    docstring = ast.get_docstring(node)

    # Get decorators
    decorators = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            decorators.append(dec.id)
        elif isinstance(dec, ast.Attribute):
            decorators.append(f"{get_type_annotation(dec.value)}.{dec.attr}")
        elif isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Name):
                decorators.append(dec.func.id)
            elif isinstance(dec.func, ast.Attribute):
                decorators.append(dec.func.attr)

    return FunctionInfo(
        name=node.name,
        lineno=node.lineno,
        end_lineno=node.end_lineno or node.lineno,
        args=args,
        arg_types=arg_types,
        return_type=return_type,
        docstring=docstring,
        is_async=isinstance(node, ast.AsyncFunctionDef),
        decorators=decorators
    )


def extract_class_info(node: ast.ClassDef) -> ClassInfo:
    """
    Extract information from a class definition node.

    Args:
        node: AST class definition node

    Returns:
        ClassInfo dataclass
    """
    # Get methods
    methods = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_info = extract_function_info(item)
            func_info.is_method = True
            methods.append(func_info)

    # Get base classes
    bases = [get_type_annotation(base) for base in node.bases]

    # Get decorators
    decorators = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            decorators.append(dec.id)

    return ClassInfo(
        name=node.name,
        lineno=node.lineno,
        end_lineno=node.end_lineno or node.lineno,
        docstring=ast.get_docstring(node),
        methods=methods,
        bases=bases,
        decorators=decorators
    )


def analyze_module(path: Path) -> Optional[ModuleInfo]:
    """
    Analyze a Python module and extract all information.

    Args:
        path: Path to Python file

    Returns:
        ModuleInfo dataclass or None if parsing fails
    """
    tree = parse_file(path)
    if tree is None:
        return None

    info = ModuleInfo(
        path=path,
        docstring=ast.get_docstring(tree)
    )

    for node in ast.walk(tree):
        # Imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                info.imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names = [alias.name for alias in node.names]
                info.from_imports.append((node.module, names))

    # Top-level items only
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            info.functions.append(extract_function_info(node))
        elif isinstance(node, ast.ClassDef):
            info.classes.append(extract_class_info(node))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    info.global_vars.append(target.id)

    return info


# =============================================================================
# GIT INTEGRATION
# =============================================================================

def run_git_command(args: List[str], cwd: Path = None) -> Optional[str]:
    """
    Run a git command and return output.

    Args:
        args: Git command arguments
        cwd: Working directory

    Returns:
        Command output or None if failed
    """
    try:
        result = subprocess.run(
            ['git'] + args,
            capture_output=True,
            text=True,
            cwd=cwd or Path.cwd(),
            timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def get_git_log(
    count: int = 50,
    cwd: Path = None
) -> List[GitCommit]:
    """
    Get recent git commits.

    Args:
        count: Number of commits to retrieve
        cwd: Working directory

    Returns:
        List of GitCommit objects
    """
    # Use a delimiter that won't appear in commit messages
    delimiter = "---COMMIT_DELIMITER---"
    format_str = f"%H{delimiter}%h{delimiter}%an{delimiter}%ai{delimiter}%s{delimiter}%b"

    output = run_git_command(
        ['log', f'-{count}', f'--format={format_str}'],
        cwd=cwd
    )

    if not output:
        return []

    commits = []
    for entry in output.split('\n'):
        if not entry.strip():
            continue

        parts = entry.split(delimiter)
        if len(parts) >= 5:
            commits.append(GitCommit(
                hash=parts[0],
                short_hash=parts[1],
                author=parts[2],
                date=parts[3],
                message=parts[4],
                body=parts[5] if len(parts) > 5 else ""
            ))

    return commits


def get_changed_files(since_commit: str = "HEAD~1", cwd: Path = None) -> List[str]:
    """
    Get list of files changed since a commit.

    Args:
        since_commit: Git reference to compare against
        cwd: Working directory

    Returns:
        List of changed file paths
    """
    output = run_git_command(
        ['diff', '--name-only', since_commit],
        cwd=cwd
    )

    if not output:
        return []

    return [f for f in output.split('\n') if f.strip()]


def get_staged_files(cwd: Path = None) -> List[str]:
    """Get list of staged files."""
    output = run_git_command(['diff', '--cached', '--name-only'], cwd=cwd)
    return [f for f in (output or '').split('\n') if f.strip()]


# =============================================================================
# OUTPUT FORMATTERS
# =============================================================================

def format_as_json(data: Any, indent: int = 2) -> str:
    """Format data as JSON string."""
    def default_serializer(obj):
        if isinstance(obj, Path):
            return str(obj)
        if hasattr(obj, '__dataclass_fields__'):
            return {k: getattr(obj, k) for k in obj.__dataclass_fields__}
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    return json.dumps(data, indent=indent, default=default_serializer)


def format_as_markdown_table(
    headers: List[str],
    rows: List[List[str]]
) -> str:
    """Format data as a Markdown table."""
    if not headers or not rows:
        return ""

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    # Format header
    header_row = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"
    separator = "|" + "|".join("-" * (w + 2) for w in widths) + "|"

    # Format rows
    data_rows = []
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            width = widths[i] if i < len(widths) else len(str(cell))
            cells.append(str(cell).ljust(width))
        data_rows.append("| " + " | ".join(cells) + " |")

    return "\n".join([header_row, separator] + data_rows)


# =============================================================================
# MCP MEMORY INTEGRATION
# =============================================================================

def get_mcp_data_dir() -> Optional[Path]:
    """Find the .mcp directory."""
    project_root = find_project_root()
    if project_root:
        mcp_dir = project_root / '.mcp'
        if mcp_dir.exists():
            return mcp_dir
    return None


def record_to_memory(
    entry_type: str,
    content: str,
    tags: List[str] = None,
    metadata: Dict[str, Any] = None
) -> bool:
    """
    Record an entry to MCP memory.

    Args:
        entry_type: Type of entry (action, decision, todo, etc.)
        content: Content of the entry
        tags: Optional tags
        metadata: Optional metadata

    Returns:
        True if successful
    """
    mcp_data = get_mcp_data_dir()
    if not mcp_data:
        return False

    memory_dir = mcp_data / 'memory'
    if not memory_dir.exists():
        memory_dir.mkdir(parents=True)

    # Map entry types to files
    type_files = {
        'action': 'actions.json',
        'decision': 'decisions.json',
        'todo': 'todos.json',
        'milestone': 'milestones.json',
        'session': 'sessions.json'
    }

    filename = type_files.get(entry_type, 'actions.json')
    filepath = memory_dir / filename

    # Load existing entries
    entries = []
    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                entries = json.load(f)
        except json.JSONDecodeError:
            entries = []

    # Create new entry
    entry = {
        'id': str(int(datetime.now().timestamp() * 1000)),
        'type': entry_type,
        'content': content,
        'timestamp': datetime.now().isoformat(),
        'tags': tags or [],
        'metadata': metadata or {}
    }

    entries.append(entry)

    # Save
    try:
        with open(filepath, 'w') as f:
            json.dump(entries, f, indent=2)
        return True
    except Exception:
        return False


# =============================================================================
# CONSOLE OUTPUT
# =============================================================================

class Console:
    """Simple console output with colors."""

    COLORS = {
        'red': '\033[0;31m',
        'green': '\033[0;32m',
        'yellow': '\033[1;33m',
        'blue': '\033[0;34m',
        'cyan': '\033[0;36m',
        'bold': '\033[1m',
        'reset': '\033[0m'
    }

    @classmethod
    def _supports_color(cls) -> bool:
        """Check if terminal supports color."""
        import sys
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

    @classmethod
    def _color(cls, text: str, color: str) -> str:
        """Apply color to text."""
        if not cls._supports_color():
            return text
        return f"{cls.COLORS.get(color, '')}{text}{cls.COLORS['reset']}"

    @classmethod
    def info(cls, msg: str):
        """Print info message."""
        print(f"{cls._color('[INFO]', 'blue')} {msg}")

    @classmethod
    def ok(cls, msg: str):
        """Print success message."""
        print(f"{cls._color('[OK]', 'green')} {msg}")

    @classmethod
    def warn(cls, msg: str):
        """Print warning message."""
        print(f"{cls._color('[WARNING]', 'yellow')} {msg}")

    @classmethod
    def fail(cls, msg: str):
        """Print failure message."""
        print(f"{cls._color('[FAIL]', 'red')} {msg}")

    @classmethod
    def header(cls, msg: str):
        """Print header."""
        print(f"\n{cls._color('=== ' + msg + ' ===', 'cyan')}\n")
