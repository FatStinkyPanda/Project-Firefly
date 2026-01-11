"""
MCP Global Rules - Scripts Package
==================================
AI Agent Enhancement Tools for autonomous development.
"""

from .utils import (
    FunctionInfo,
    ClassInfo,
    ModuleInfo,
    GitCommit,
    find_python_files,
    find_project_root,
    parse_file,
    analyze_module,
    get_git_log,
    get_changed_files,
    get_staged_files,
    format_as_json,
    format_as_markdown_table,
    record_to_memory,
    Console
)

__version__ = "2.0.0"
__all__ = [
    'FunctionInfo',
    'ClassInfo',
    'ModuleInfo',
    'GitCommit',
    'find_python_files',
    'find_project_root',
    'parse_file',
    'analyze_module',
    'get_git_log',
    'get_changed_files',
    'get_staged_files',
    'format_as_json',
    'format_as_markdown_table',
    'record_to_memory',
    'Console'
]
