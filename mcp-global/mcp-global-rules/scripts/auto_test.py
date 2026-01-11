"""
Auto-Test Generator
===================
Automatically generate pytest test stubs for Python functions and classes.

Usage:
    python auto_test.py [path] [--output-dir tests/]
    python -m scripts.auto_test [path]
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional
import ast
import sys

from .utils import (
    find_python_files,
    find_project_root,
    parse_file,
    analyze_module,
    FunctionInfo,
    ClassInfo,
    Console
)


@dataclass
class TestSuite:
    """Generated test suite for a module."""
    module_path: Path
    module_name: str
    test_imports: List[str] = field(default_factory=list)
    test_functions: List[str] = field(default_factory=list)
    test_classes: List[str] = field(default_factory=list)


def generate_test_function(func: FunctionInfo, module_name: str) -> str:
    """
    Generate a pytest test function for a given function.

    Args:
        func: Function information
        module_name: Name of the module containing the function

    Returns:
        Test function source code
    """
    lines = []

    # Generate test function name
    test_name = f"test_{func.name}"

    # Add docstring
    lines.append(f"def {test_name}():")
    lines.append(f'    """Test {func.name} function."""')

    # Generate basic test structure
    if func.args:
        # Generate sample arguments
        lines.append("    # Arrange")
        for arg in func.args:
            if arg in ('self', 'cls'):
                continue

            arg_type = func.arg_types.get(arg, '')
            sample_value = _get_sample_value(arg, arg_type)
            lines.append(f"    {arg} = {sample_value}")

        lines.append("")
        lines.append("    # Act")

        # Generate function call
        call_args = [a for a in func.args if a not in ('self', 'cls')]
        if call_args:
            args_str = ", ".join(call_args)
            lines.append(f"    result = {module_name}.{func.name}({args_str})")
        else:
            lines.append(f"    result = {module_name}.{func.name}()")

        lines.append("")
        lines.append("    # Assert")

        # Generate assertion based on return type
        if func.return_type:
            assertion = _generate_assertion(func.return_type)
            lines.append(f"    {assertion}")
        else:
            lines.append("    assert result is not None  # TODO: Add specific assertion")
    else:
        lines.append("    # Act")
        lines.append(f"    result = {module_name}.{func.name}()")
        lines.append("")
        lines.append("    # Assert")
        lines.append("    assert result is not None  # TODO: Add specific assertion")

    lines.append("")
    return "\n".join(lines)


def generate_edge_case_tests(func: FunctionInfo, module_name: str) -> List[str]:
    """
    Generate edge case tests for a function.

    Args:
        func: Function information
        module_name: Module name

    Returns:
        List of edge case test functions
    """
    tests = []

    for arg in func.args:
        if arg in ('self', 'cls'):
            continue

        arg_type = func.arg_types.get(arg, '')

        # Test with None if Optional
        if 'Optional' in arg_type or 'None' in arg_type:
            test_lines = [
                f"def test_{func.name}_with_{arg}_none():",
                f'    """Test {func.name} with None {arg}."""',
                f"    # This should handle None gracefully",
                f"    try:",
                f"        result = {module_name}.{func.name}({arg}=None)",
                f"        # Assert expected behavior with None",
                f"    except (TypeError, ValueError) as e:",
                f"        pass  # Expected if None is not allowed",
                ""
            ]
            tests.append("\n".join(test_lines))

        # Test with empty for collections
        if any(t in arg_type.lower() for t in ['list', 'dict', 'set', 'tuple']):
            empty_val = "[]" if 'list' in arg_type.lower() else "{}"
            test_lines = [
                f"def test_{func.name}_with_empty_{arg}():",
                f'    """Test {func.name} with empty {arg}."""',
                f"    result = {module_name}.{func.name}({arg}={empty_val})",
                f"    # Assert behavior with empty collection",
                f"    assert result is not None",
                ""
            ]
            tests.append("\n".join(test_lines))

    return tests


def generate_test_class(cls: ClassInfo, module_name: str) -> str:
    """
    Generate a pytest test class.

    Args:
        cls: Class information
        module_name: Module name

    Returns:
        Test class source code
    """
    lines = []

    test_class_name = f"Test{cls.name}"

    lines.append(f"class {test_class_name}:")
    lines.append(f'    """Tests for {cls.name} class."""')
    lines.append("")

    # Add fixture for class instance
    lines.append("    @pytest.fixture")
    lines.append("    def instance(self):")
    lines.append(f'        """Create a {cls.name} instance for testing."""')
    lines.append(f"        return {module_name}.{cls.name}()  # TODO: Add constructor args")
    lines.append("")

    # Add test for instantiation
    lines.append("    def test_instantiation(self):")
    lines.append(f'        """Test {cls.name} can be instantiated."""')
    lines.append(f"        obj = {module_name}.{cls.name}()  # TODO: Add constructor args")
    lines.append(f"        assert obj is not None")
    lines.append(f"        assert isinstance(obj, {module_name}.{cls.name})")
    lines.append("")

    # Add tests for each public method
    for method in cls.methods:
        if method.name.startswith('_'):
            continue

        method_lines = _generate_method_test(method, cls.name)
        lines.extend(method_lines)

    return "\n".join(lines)


def _generate_method_test(method: FunctionInfo, class_name: str) -> List[str]:
    """Generate test for a class method."""
    lines = []

    lines.append(f"    def test_{method.name}(self, instance):")
    lines.append(f'        """Test {class_name}.{method.name} method."""')

    # Generate method call
    call_args = [a for a in method.args if a not in ('self', 'cls')]
    if call_args:
        lines.append("        # Arrange")
        for arg in call_args:
            arg_type = method.arg_types.get(arg, '')
            sample_value = _get_sample_value(arg, arg_type)
            lines.append(f"        {arg} = {sample_value}")

        lines.append("")
        lines.append("        # Act")
        args_str = ", ".join(call_args)
        lines.append(f"        result = instance.{method.name}({args_str})")
    else:
        lines.append("        # Act")
        lines.append(f"        result = instance.{method.name}()")

    lines.append("")
    lines.append("        # Assert")
    lines.append("        assert result is not None  # TODO: Add specific assertion")
    lines.append("")

    return lines


def _get_sample_value(arg_name: str, arg_type: str) -> str:
    """Get a sample value for a parameter."""
    type_lower = arg_type.lower()

    if 'str' in type_lower:
        return f'"test_{arg_name}"'
    elif 'int' in type_lower:
        return "42"
    elif 'float' in type_lower:
        return "3.14"
    elif 'bool' in type_lower:
        return "True"
    elif 'list' in type_lower:
        return "[]"
    elif 'dict' in type_lower:
        return "{}"
    elif 'path' in type_lower or 'path' in arg_name.lower():
        return 'Path(".")'
    elif 'none' in type_lower:
        return "None"
    else:
        # Try to infer from name
        if 'path' in arg_name.lower():
            return 'Path(".")'
        elif 'name' in arg_name.lower():
            return '"test_name"'
        elif 'id' in arg_name.lower():
            return '"test_id"'
        elif 'count' in arg_name.lower() or 'num' in arg_name.lower():
            return "10"
        elif 'flag' in arg_name.lower() or arg_name.startswith('is_'):
            return "True"
        else:
            return "None  # TODO: Provide appropriate value"


def _generate_assertion(return_type: str) -> str:
    """Generate an assertion based on return type."""
    type_lower = return_type.lower()

    if 'bool' in type_lower:
        return "assert isinstance(result, bool)"
    elif 'str' in type_lower:
        return "assert isinstance(result, str)"
    elif 'int' in type_lower:
        return "assert isinstance(result, int)"
    elif 'float' in type_lower:
        return "assert isinstance(result, (int, float))"
    elif 'list' in type_lower:
        return "assert isinstance(result, list)"
    elif 'dict' in type_lower:
        return "assert isinstance(result, dict)"
    elif 'none' in type_lower:
        return "assert result is None"
    elif 'optional' in type_lower:
        return "# Result may be None"
    else:
        return "assert result is not None  # TODO: Add specific assertion"


def generate_test_file(module_path: Path, output_dir: Path = None) -> Optional[Path]:
    """
    Generate a test file for a Python module.

    Args:
        module_path: Path to the module
        output_dir: Output directory for test files

    Returns:
        Path to generated test file, or None if no tests generated
    """
    module_info = analyze_module(module_path)
    if module_info is None:
        return None

    # Skip if no public functions or classes
    public_functions = [f for f in module_info.functions if not f.name.startswith('_')]
    public_classes = [c for c in module_info.classes if not c.name.startswith('_')]

    if not public_functions and not public_classes:
        return None

    # Generate module name
    module_name = module_path.stem

    # Build test file content
    lines = [
        '"""',
        f'Tests for {module_name} module.',
        '"""',
        '',
        'import pytest',
        'from pathlib import Path',
        '',
        f'# Import module under test',
        f'# TODO: Adjust import path as needed',
        f'# import {module_name}',
        f'# from src import {module_name}',
        '',
        '',
    ]

    # Generate function tests
    for func in public_functions:
        lines.append(generate_test_function(func, module_name))

        # Add edge case tests
        edge_tests = generate_edge_case_tests(func, module_name)
        lines.extend(edge_tests)

    # Generate class tests
    for cls in public_classes:
        lines.append(generate_test_class(cls, module_name))

    # Determine output path
    if output_dir is None:
        project_root = find_project_root(module_path)
        if project_root:
            output_dir = project_root / 'tests'
        else:
            output_dir = module_path.parent / 'tests'

    output_dir.mkdir(parents=True, exist_ok=True)

    test_filename = f"test_{module_name}.py"
    test_path = output_dir / test_filename

    # Don't overwrite existing tests
    if test_path.exists():
        Console.warn(f"Test file already exists: {test_path}")
        return None

    with open(test_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return test_path


def generate_tests(
    root: Path,
    output_dir: Path = None,
    exclude_patterns: List[str] = None
) -> int:
    """
    Generate tests for all Python files in a directory.

    Args:
        root: Root directory
        output_dir: Output directory for tests
        exclude_patterns: Patterns to exclude

    Returns:
        Number of test files generated
    """
    Console.info(f"Scanning for Python files in {root}...")

    files = list(find_python_files(root, exclude_patterns))
    Console.info(f"Found {len(files)} Python files")

    generated = 0

    for path in files:
        # Skip test files
        if path.name.startswith('test_') or 'tests' in path.parts:
            continue

        test_path = generate_test_file(path, output_dir)
        if test_path:
            Console.ok(f"Generated: {test_path}")
            generated += 1

    return generated


def main():
    """CLI entry point."""
    Console.header("Auto-Test Generator")

    # Parse args
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    output_dir = None

    for i, arg in enumerate(sys.argv):
        if arg == '--output-dir' and i + 1 < len(sys.argv):
            output_dir = Path(sys.argv[i + 1])

    # Get path
    if args:
        path = Path(args[0])
    else:
        path = find_project_root() or Path.cwd()

    if not path.exists():
        Console.fail(f"Path not found: {path}")
        sys.exit(1)

    Console.info(f"Analyzing: {path}")

    generated = generate_tests(path, output_dir)

    print()
    if generated > 0:
        Console.ok(f"Generated {generated} test files")
    else:
        Console.info("No new test files generated (all modules already have tests or no public code found)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
