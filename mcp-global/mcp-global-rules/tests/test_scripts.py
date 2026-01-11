"""
Tests for MCP Global Rules Scripts
==================================
Comprehensive test suite for all AI agent enhancement tools.
"""

from pathlib import Path
import os
import tempfile

import pytest

# Create a sample Python file for testing
SAMPLE_PYTHON_CODE = '''
"""Sample module for testing."""

import os
import sys
from pathlib import Path


class SampleClass:
    """A sample class."""

    def __init__(self, name: str):
        self.name = name

    def get_name(self) -> str:
        """Get the name."""
        return self.name


def sample_function(arg1: str, arg2: int = 10) -> bool:
    """
    Sample function with docstring.

    Args:
        arg1: First argument
        arg2: Second argument

    Returns:
        True if successful
    """
    return True


def undocumented_function(x, y):
    # This function has no docstring
    return x + y


CONSTANT_VALUE = 42
unused_variable = "not used"
'''

SAMPLE_CODE_NO_DOCS = '''
import json

class NoDocClass:
    def __init__(self):
        self.value = 1

    def method(self):
        return self.value

def no_doc_function():
    return True
'''


@pytest.fixture
def temp_project():
    """Create a temporary project directory with sample files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create sample files
        (project_dir / "sample.py").write_text(SAMPLE_PYTHON_CODE)
        (project_dir / "no_docs.py").write_text(SAMPLE_CODE_NO_DOCS)

        # Create src directory
        (project_dir / "src").mkdir()
        (project_dir / "src" / "__init__.py").write_text("")
        (project_dir / "src" / "module.py").write_text(SAMPLE_PYTHON_CODE)

        yield project_dir


class TestUtils:
    """Tests for utils.py module."""

    def test_find_python_files(self, temp_project):
        """Test finding Python files."""
        from scripts.utils import find_python_files

        files = list(find_python_files(temp_project))
        if not len(files) >= 2:
            raise AssertionError("Should have found at least 2 files")
        if not any(f.name == "sample.py" for f in files):
            raise AssertionError("Should have found sample.py")

    def test_parse_file(self, temp_project):
        """Test parsing Python file."""
        from scripts.utils import parse_file

        tree = parse_file(temp_project / "sample.py")
        if tree is None:
            raise AssertionError("Tree should not be None")

    def test_analyze_module(self, temp_project):
        """Test analyzing module."""
        from scripts.utils import analyze_module

        info = analyze_module(temp_project / "sample.py")
        if info is None:
            raise AssertionError("Info should not be None")
        if not len(info.functions) >= 2:
            raise AssertionError("Should identify at least 2 functions")
        if not len(info.classes) >= 1:
            raise AssertionError("Should identify at least 1 class")

    def test_format_as_markdown_table(self):
        """Test markdown table formatting."""
        from scripts.utils import format_as_markdown_table

        table = format_as_markdown_table(
            ["Name", "Value"],
            [["foo", "bar"], ["baz", "qux"]]
        )
        if "Name" not in table:
            raise AssertionError("Table should contain header 'Name'")
        if "foo" not in table:
            raise AssertionError("Table should contain value 'foo'")


class TestDeadCode:
    """Tests for dead_code.py module."""

    def test_detect_dead_code(self, temp_project):
        """Test dead code detection."""
        from scripts.dead_code import detect_dead_code

        report = detect_dead_code(temp_project)
        if report is None:
            raise AssertionError("Report should not be None")
        if not report.total_issues >= 0:
            raise AssertionError("Total issues should be non-negative")

    def test_report_to_markdown(self, temp_project):
        """Test report conversion to markdown."""
        from scripts.dead_code import detect_dead_code

        report = detect_dead_code(temp_project)
        markdown = report.to_markdown()
        if "Dead Code Report" not in markdown:
            raise AssertionError("Markdown should contain 'Dead Code Report'")


class TestAutoDocs:
    """Tests for auto_docs.py module."""

    def test_analyze_file_for_docstrings(self, temp_project):
        """Test docstring analysis."""
        from scripts.auto_docs import analyze_file_for_docstrings

        suggestions = analyze_file_for_docstrings(temp_project / "no_docs.py")
        if not len(suggestions) >= 2:
            raise AssertionError("Should find at least 2 suggestions")

    def test_generate_function_docstring(self):
        """Test docstring generation."""
        from scripts.auto_docs import generate_function_docstring
        from scripts.utils import FunctionInfo
        import ast

        # Create a mock function node
        code = "def test_func(arg1: str, arg2: int) -> bool: pass"
        tree = ast.parse(code)
        node = tree.body[0]

        docstring = generate_function_docstring(node, "    ")
        if '"""' not in docstring:
            raise AssertionError("Docstring should contain quotes")
        if 'Args:' not in docstring:
            raise AssertionError("Docstring should contain Args section")


class TestAutoTest:
    """Tests for auto_test.py module."""

    def test_generate_test_function(self):
        """Test test function generation."""
        from scripts.auto_test import generate_test_function
        from scripts.utils import FunctionInfo

        func = FunctionInfo(
            name="my_function",
            lineno=1,
            end_lineno=10,
            args=["arg1", "arg2"],
            arg_types={"arg1": "str", "arg2": "int"},
            return_type="bool",
            docstring="Test function."
        )

        test_code = generate_test_function(func, "mymodule")
        if "def test_my_function" not in test_code:
            raise AssertionError("Should generate test function definition")
        if "assert" not in test_code:
            raise AssertionError("Should contain assertion in generated code")


class TestSummarize:
    """Tests for summarize.py module."""

    def test_summarize_codebase(self, temp_project):
        """Test codebase summarization."""
        from scripts.summarize import summarize_codebase

        summary = summarize_codebase(temp_project)
        if not summary.total_files >= 2:
            raise AssertionError("Should handle at least 2 files")
        if not summary.total_functions >= 2:
            raise AssertionError("Should handle at least 2 functions")

    def test_format_summary_markdown(self, temp_project):
        """Test summary markdown formatting."""
        from scripts.summarize import summarize_codebase, format_summary_markdown

        summary = summarize_codebase(temp_project)
        markdown = format_summary_markdown(summary)
        if "# Codebase Summary" not in markdown:
            raise AssertionError("Markdown should contain header")


class TestChangelog:
    """Tests for changelog.py module."""

    def test_parse_commit_message(self):
        """Test commit message parsing."""
        from scripts.changelog import parse_commit_message

        entry = parse_commit_message("feat(auth): add login functionality")
        if entry is None:
            raise AssertionError("Entry should not be None")
        if entry.commit_type != "feat":
            raise AssertionError("Commit type should be feat")
        if entry.scope != "auth":
            raise AssertionError("Scope should be auth")
        if "login" not in entry.description:
            raise AssertionError("Description should contain login")

    def test_parse_commit_message_breaking(self):
        """Test breaking change detection."""
        from scripts.changelog import parse_commit_message

        entry = parse_commit_message("feat!: breaking change")
        if entry is None:
            raise AssertionError("Entry should not be None")
        if entry.breaking != True:
            raise AssertionError("Should detect breaking change")


class TestDeps:
    """Tests for deps.py module."""

    def test_analyze_dependencies(self, temp_project):
        """Test dependency analysis."""
        from scripts.deps import analyze_dependencies

        report = analyze_dependencies(temp_project)
        if report is None:
            raise AssertionError("Report should not be None")
        if not len(report.modules) >= 2:
            raise AssertionError("Should find at least 2 modules")

    def test_format_report_markdown(self, temp_project):
        """Test dependency report markdown."""
        from scripts.deps import analyze_dependencies, format_report_markdown

        report = analyze_dependencies(temp_project)
        markdown = format_report_markdown(report)
        if "# Dependency Analysis" not in markdown:
            raise AssertionError("Markdown should contain header")


class TestReview:
    """Tests for review.py module."""

    def test_review_file(self, temp_project):
        """Test file review."""
        from scripts.review import review_file

        issues = review_file(temp_project / "no_docs.py")
        if not len(issues) >= 1:
            raise AssertionError("Should find missing docstrings")

    def test_review_project(self, temp_project):
        """Test project review."""
        from scripts.review import review_project

        report = review_project(temp_project)
        if not report.files_reviewed >= 2:
            raise AssertionError("Should review at least 2 files")

    def test_security_check(self):
        """Test security issue detection."""
        from scripts.review import ReviewChecks
        import ast

        code = '''
test_val = "mock" + "_" + "credential"
eval(user_input)
'''
        tree = ast.parse(code)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()

            issues = ReviewChecks.check_security_issues(Path(f.name), tree)
            if not len(issues) >= 1:
                raise AssertionError("Should find security issue")

            os.unlink(f.name)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
