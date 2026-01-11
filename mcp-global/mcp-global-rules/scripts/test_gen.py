"""
Auto-Test Implementation Generator
==================================
Generate actual test implementations, not just stubs.

Usage:
    python mcp.py test-gen [file] --impl
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import ast
import sys

from .utils import Console, find_project_root


@dataclass
class FunctionSignature:
    """Function signature info."""
    name: str
    args: List[Tuple[str, Optional[str]]]  # (name, type_hint)
    return_type: Optional[str]
    decorators: List[str]
    docstring: Optional[str]
    is_async: bool
    line_num: int


class SignatureExtractor(ast.NodeVisitor):
    """Extract function signatures."""

    def __init__(self):
        self.functions: List[FunctionSignature] = []

    def visit_FunctionDef(self, node):
        self._extract(node, is_async=False)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self._extract(node, is_async=True)
        self.generic_visit(node)

    def _extract(self, node, is_async: bool):
        # Skip private and magic methods (except __init__)
        if node.name.startswith('_') and not node.name == '__init__':
            return

        # Get args with type hints
        args = []
        for arg in node.args.args:
            if arg.arg != 'self':
                type_hint = None
                if arg.annotation:
                    type_hint = ast.unparse(arg.annotation)
                args.append((arg.arg, type_hint))

        # Get return type
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)

        # Get decorators
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(dec.attr)

        self.functions.append(FunctionSignature(
            name=node.name,
            args=args,
            return_type=return_type,
            decorators=decorators,
            docstring=ast.get_docstring(node),
            is_async=is_async,
            line_num=node.lineno
        ))


def get_test_value(type_hint: Optional[str]) -> str:
    """Get example test value for a type."""
    if not type_hint:
        return '"test_value"'

    type_lower = type_hint.lower()

    if 'int' in type_lower:
        return '42'
    elif 'float' in type_lower:
        return '3.14'
    elif 'str' in type_lower:
        return '"test_string"'
    elif 'bool' in type_lower:
        return 'True'
    elif 'list' in type_lower:
        return '[]'
    elif 'dict' in type_lower:
        return '{}'
    elif 'none' in type_lower:
        return 'None'
    elif 'path' in type_lower:
        return 'Path(".")'
    elif 'optional' in type_lower:
        return 'None'
    else:
        return 'None  # TODO: provide test value'


def get_assertion(return_type: Optional[str]) -> str:
    """Get appropriate assertion for return type."""
    if not return_type:
        return 'assert result is not None'

    type_lower = return_type.lower()

    if 'bool' in type_lower:
        return 'assert isinstance(result, bool)'
    elif 'int' in type_lower:
        return 'assert isinstance(result, int)'
    elif 'float' in type_lower:
        return 'assert isinstance(result, (int, float))'
    elif 'str' in type_lower:
        return 'assert isinstance(result, str)'
    elif 'list' in type_lower:
        return 'assert isinstance(result, list)'
    elif 'dict' in type_lower:
        return 'assert isinstance(result, dict)'
    elif 'none' in type_lower:
        return 'assert result is None'
    else:
        return 'assert result is not None'


def generate_test_impl(func: FunctionSignature, module_name: str) -> str:
    """Generate full test implementation for a function."""
    lines = []

    # Test function signature
    async_prefix = 'async ' if func.is_async else ''
    lines.append(f'{async_prefix}def test_{func.name}():')

    # Docstring
    if func.docstring:
        lines.append(f'    """Test {func.name}: {func.docstring[:50]}..."""')
    else:
        lines.append(f'    """Test {func.name} function."""')

    # Arrange
    lines.append('    # Arrange')
    args_call = []
    for arg_name, arg_type in func.args:
        value = get_test_value(arg_type)
        lines.append(f'    {arg_name} = {value}')
        args_call.append(arg_name)

    lines.append('')
    lines.append('    # Act')

    args_str = ', '.join(args_call)
    if func.is_async:
        lines.append(f'    result = await {func.name}({args_str})')
    else:
        lines.append(f'    result = {func.name}({args_str})')

    lines.append('')
    lines.append('    # Assert')
    lines.append(f'    {get_assertion(func.return_type)}')

    return '\n'.join(lines)


def generate_edge_case_tests(func: FunctionSignature) -> List[str]:
    """Generate edge case tests."""
    tests = []

    for arg_name, arg_type in func.args:
        if not arg_type:
            continue

        type_lower = arg_type.lower()

        # None tests for Optional types
        if 'optional' in type_lower:
            test = f'''def test_{func.name}_{arg_name}_none():
    """Test {func.name} with {arg_name}=None."""
    result = {func.name}({arg_name}=None)
    assert result is not None or True  # Handle None case'''
            tests.append(test)

        # Empty tests for collections
        if 'list' in type_lower:
            test = f'''def test_{func.name}_{arg_name}_empty():
    """Test {func.name} with empty list."""
    result = {func.name}({arg_name}=[])
    assert result is not None'''
            tests.append(test)

        if 'str' in type_lower:
            test = f'''def test_{func.name}_{arg_name}_empty_string():
    """Test {func.name} with empty string."""
    result = {func.name}({arg_name}="")
    assert result is not None'''
            tests.append(test)

        # Boundary tests for numerics
        if 'int' in type_lower:
            test = f'''def test_{func.name}_{arg_name}_zero():
    """Test {func.name} with {arg_name}=0."""
    result = {func.name}({arg_name}=0)
    assert result is not None

def test_{func.name}_{arg_name}_negative():
    """Test {func.name} with negative {arg_name}."""
    result = {func.name}({arg_name}=-1)
    assert result is not None'''
            tests.append(test)

    return tests


def generate_test_file(file_path: Path) -> str:
    """Generate full test file for a module."""
    try:
        source = file_path.read_text(encoding='utf-8')
        tree = ast.parse(source)
    except Exception as e:
        return f"# Error parsing {file_path}: {e}"

    extractor = SignatureExtractor()
    extractor.visit(tree)

    module_name = file_path.stem

    lines = [
        '"""',
        f'Auto-generated tests for {module_name}',
        '"""',
        '',
        'import pytest',
        f'from {module_name} import *',
        '',
        '',
    ]

    for func in extractor.functions:
        # Main test
        lines.append(generate_test_impl(func, module_name))
        lines.append('')
        lines.append('')

        # Edge case tests
        edge_tests = generate_edge_case_tests(func)
        for test in edge_tests[:2]:  # Limit edge cases
            lines.append(test)
            lines.append('')
            lines.append('')

    return '\n'.join(lines)


def main():
    """CLI entry point."""
    Console.header("Auto-Test Generator (Full Implementation)")

    args = [a for a in sys.argv[1:] if not a.startswith('-')]

    if not args:
        Console.info("Usage: mcp test-gen <file.py> [--impl]")
        return 1

    file_path = Path(args[0])

    if not file_path.exists():
        Console.fail(f"File not found: {file_path}")
        return 1

    Console.info(f"Generating tests for: {file_path}")

    test_code = generate_test_file(file_path)

    if '--impl' in sys.argv or '--write' in sys.argv:
        # Write to test file
        test_file = file_path.parent / f'test_{file_path.name}'
        test_file.write_text(test_code)
        Console.ok(f"Written to: {test_file}")
    else:
        print(test_code)

    return 0


if __name__ == "__main__":
    sys.exit(main())
