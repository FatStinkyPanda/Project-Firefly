"""
Tree-sitter Utilities
=====================
Multi-language code parsing using tree-sitter.
Supports Python, JavaScript, TypeScript, Go, Rust, Java, C, C++, and more.

Usage:
    from scripts.treesitter_utils import parse_file, get_functions, get_classes
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterator, Callable
from dataclasses import dataclass, field

# Try to import tree-sitter, fall back gracefully
try:
    import tree_sitter
    from tree_sitter import Language, Parser, Tree, Node
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    Tree = Any
    Node = Any

from .utils import Console


@dataclass
class CodeItem:
    """A code item (function, class, etc)."""
    name: str
    item_type: str  # 'function', 'class', 'method', 'import', 'variable'
    line_start: int
    line_end: int
    signature: str = ""
    docstring: Optional[str] = None
    language: str = ""
    children: List['CodeItem'] = field(default_factory=list)


@dataclass
class ParsedFile:
    """Result of parsing a file."""
    path: Path
    language: str
    tree: Optional[Any] = None
    source: bytes = b""
    functions: List[CodeItem] = field(default_factory=list)
    classes: List[CodeItem] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    error: Optional[str] = None


# Language detection by extension
LANGUAGE_MAP = {
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.go': 'go',
    '.rs': 'rust',
    '.java': 'java',
    '.c': 'c',
    '.h': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.hpp': 'cpp',
    '.cs': 'c_sharp',
    '.rb': 'ruby',
    '.php': 'php',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.lua': 'lua',
    '.sh': 'bash',
    '.bash': 'bash',
    '.json': 'json',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.html': 'html',
    '.css': 'css',
    '.sql': 'sql',
    '.md': 'markdown',
}

# Node types for functions by language
FUNCTION_TYPES = {
    'python': ['function_definition', 'async_function_definition'],
    'javascript': ['function_declaration', 'function_expression', 'arrow_function', 'method_definition'],
    'typescript': ['function_declaration', 'function_expression', 'arrow_function', 'method_definition'],
    'go': ['function_declaration', 'method_declaration'],
    'rust': ['function_item', 'impl_item'],
    'java': ['method_declaration', 'constructor_declaration'],
    'c': ['function_definition'],
    'cpp': ['function_definition'],
}

# Node types for classes by language
CLASS_TYPES = {
    'python': ['class_definition'],
    'javascript': ['class_declaration'],
    'typescript': ['class_declaration', 'interface_declaration'],
    'go': ['type_declaration'],
    'rust': ['struct_item', 'enum_item', 'impl_item'],
    'java': ['class_declaration', 'interface_declaration'],
    'cpp': ['class_specifier', 'struct_specifier'],
}

# Node types for imports
IMPORT_TYPES = {
    'python': ['import_statement', 'import_from_statement'],
    'javascript': ['import_statement', 'import_declaration'],
    'typescript': ['import_statement', 'import_declaration'],
    'go': ['import_declaration'],
    'rust': ['use_declaration'],
    'java': ['import_declaration'],
}


# Parser cache
_parsers: Dict[str, Any] = {}
_languages: Dict[str, Any] = {}


def detect_language(path: Path) -> Optional[str]:
    """Detect language from file extension."""
    return LANGUAGE_MAP.get(path.suffix.lower())


def get_parser(language: str) -> Optional[Any]:
    """Get or create parser for language."""
    if not TREE_SITTER_AVAILABLE:
        return None

    if language in _parsers:
        return _parsers[language]

    try:
        # Try to load language
        lang_module = __import__(f'tree_sitter_{language}', fromlist=[language])
        if hasattr(lang_module, 'language'):
            lang = Language(lang_module.language())
            parser = Parser(lang)
            _parsers[language] = parser
            _languages[language] = lang
            return parser
    except ImportError:
        pass
    except Exception as e:
        Console.warn(f"Could not load tree-sitter-{language}: {e}")

    return None


def parse_source(source: bytes, language: str) -> Optional[Tree]:
    """Parse source code into tree."""
    parser = get_parser(language)
    if parser is None:
        return None

    return parser.parse(source)


def parse_file(path: Path) -> ParsedFile:
    """Parse a source file."""
    result = ParsedFile(path=path, language="")

    # Detect language
    language = detect_language(path)
    if not language:
        result.error = f"Unknown language for {path.suffix}"
        return result

    result.language = language

    # Read file
    try:
        with open(path, 'rb') as f:
            source = f.read()
        result.source = source
    except Exception as e:
        result.error = f"Could not read file: {e}"
        return result

    # Parse with tree-sitter if available
    if TREE_SITTER_AVAILABLE:
        tree = parse_source(source, language)
        if tree:
            result.tree = tree
            result.functions = extract_functions(tree, language, source)
            result.classes = extract_classes(tree, language, source)
            result.imports = extract_imports(tree, language, source)
            return result

    # Fallback to Python's ast for Python files
    if language == 'python':
        result = _parse_python_fallback(path, source, result)

    return result


def _parse_python_fallback(path: Path, source: bytes, result: ParsedFile) -> ParsedFile:
    """Fallback parser for Python using stdlib ast."""
    import ast

    try:
        tree = ast.parse(source.decode('utf-8', errors='ignore'))

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                item = CodeItem(
                    name=node.name,
                    item_type='function',
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    docstring=ast.get_docstring(node),
                    language='python'
                )
                result.functions.append(item)

            elif isinstance(node, ast.ClassDef):
                item = CodeItem(
                    name=node.name,
                    item_type='class',
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    docstring=ast.get_docstring(node),
                    language='python'
                )
                result.classes.append(item)

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    result.imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    result.imports.append(node.module)

    except SyntaxError:
        result.error = "Syntax error in Python file"

    return result


def extract_functions(tree: Tree, language: str, source: bytes) -> List[CodeItem]:
    """Extract functions from tree."""
    functions = []
    func_types = FUNCTION_TYPES.get(language, [])

    def visit(node: Node):
        if node.type in func_types:
            name = _get_node_name(node, language)
            if name:
                item = CodeItem(
                    name=name,
                    item_type='function',
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    signature=_get_signature(node, source),
                    language=language
                )
                functions.append(item)

        for child in node.children:
            visit(child)

    if tree and tree.root_node:
        visit(tree.root_node)

    return functions


def extract_classes(tree: Tree, language: str, source: bytes) -> List[CodeItem]:
    """Extract classes from tree."""
    classes = []
    class_types = CLASS_TYPES.get(language, [])

    def visit(node: Node):
        if node.type in class_types:
            name = _get_node_name(node, language)
            if name:
                item = CodeItem(
                    name=name,
                    item_type='class',
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    language=language
                )
                classes.append(item)

        for child in node.children:
            visit(child)

    if tree and tree.root_node:
        visit(tree.root_node)

    return classes


def extract_imports(tree: Tree, language: str, source: bytes) -> List[str]:
    """Extract imports from tree."""
    imports = []
    import_types = IMPORT_TYPES.get(language, [])

    def visit(node: Node):
        if node.type in import_types:
            # Get the import text
            import_text = source[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')
            imports.append(import_text.strip())

        for child in node.children:
            visit(child)

    if tree and tree.root_node:
        visit(tree.root_node)

    return imports


def _get_node_name(node: Node, language: str) -> Optional[str]:
    """Extract name from node."""
    # Look for identifier child
    for child in node.children:
        if child.type in ('identifier', 'name', 'property_identifier'):
            return child.text.decode('utf-8', errors='ignore')
    return None


def _get_signature(node: Node, source: bytes) -> str:
    """Get function/method signature."""
    # Get first line
    start = node.start_byte
    end = node.end_byte
    text = source[start:end].decode('utf-8', errors='ignore')
    first_line = text.split('\n')[0]
    return first_line[:100]


def walk_tree(tree: Tree, callback: Callable[[Node], None]):
    """Walk entire tree calling callback on each node."""
    def visit(node: Node):
        callback(node)
        for child in node.children:
            visit(child)

    if tree and tree.root_node:
        visit(tree.root_node)


def find_nodes(tree: Tree, node_types: List[str]) -> List[Node]:
    """Find all nodes of given types."""
    results = []

    def visit(node: Node):
        if node.type in node_types:
            results.append(node)
        for child in node.children:
            visit(child)

    if tree and tree.root_node:
        visit(tree.root_node)

    return results


def get_node_text(node: Node, source: bytes) -> str:
    """Get text content of node."""
    return source[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')


def supported_languages() -> List[str]:
    """Get list of supported languages."""
    return list(LANGUAGE_MAP.values())


def is_tree_sitter_available() -> bool:
    """Check if tree-sitter is available."""
    return TREE_SITTER_AVAILABLE


def main():
    """CLI entry point."""
    Console.header("Tree-sitter Utilities")

    if not TREE_SITTER_AVAILABLE:
        Console.warn("tree-sitter not installed, using Python ast fallback")
    else:
        Console.ok("tree-sitter available")

    # Parse arguments
    args = [a for a in sys.argv[1:] if not a.startswith('-')]

    if not args:
        Console.info("Supported languages:")
        for ext, lang in sorted(LANGUAGE_MAP.items()):
            Console.info(f"  {ext} -> {lang}")
        return 0

    path = Path(args[0])
    if not path.exists():
        Console.fail(f"File not found: {path}")
        return 1

    result = parse_file(path)

    print(f"\nFile: {result.path}")
    print(f"Language: {result.language}")
    print(f"Functions: {len(result.functions)}")
    print(f"Classes: {len(result.classes)}")
    print(f"Imports: {len(result.imports)}")

    if result.functions:
        print("\n## Functions")
        for f in result.functions[:10]:
            print(f"  - {f.name} (lines {f.line_start}-{f.line_end})")

    if result.classes:
        print("\n## Classes")
        for c in result.classes[:10]:
            print(f"  - {c.name} (lines {c.line_start}-{c.line_end})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
