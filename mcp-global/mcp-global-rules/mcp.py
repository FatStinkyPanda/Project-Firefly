#!/usr/bin/env python3
"""
MCP Tools Runner
================
Single entry point for all MCP AI enhancement tools.

Works correctly regardless of:
- How it's invoked (relative path, absolute path, symlink)
- Current working directory
- Installation location in project
"""

from pathlib import Path
import os
import sys

# =============================================================================
# CRITICAL: Resolve the ACTUAL location of this script
# =============================================================================

def get_package_root():
    """
    Get the absolute path to the mcp-global-rules directory.
    Handles symlinks, relative paths, and various invocation methods.
    """
    # Method 1: Use __file__ (works in most cases)
    if '__file__' in dir():
        script_path = Path(__file__).resolve()
        return script_path.parent

    # Method 2: Use sys.argv[0] (when __file__ isn't available)
    if sys.argv:
        script_path = Path(sys.argv[0]).resolve()
        if script_path.name == 'mcp.py':
            return script_path.parent

    # Method 3: Search common locations
    cwd = Path.cwd()

    # Check if mcp-global-rules is in current directory
    if (cwd / 'mcp-global-rules' / 'mcp.py').exists():
        return cwd / 'mcp-global-rules'

    # Check if we're inside mcp-global-rules
    if (cwd / 'mcp.py').exists() and (cwd / 'scripts').exists():
        return cwd

    # Check parent directories
    for parent in cwd.parents:
        if (parent / 'mcp-global-rules' / 'mcp.py').exists():
            return parent / 'mcp-global-rules'

    return None


# Get MCP root and add to path
MCP_ROOT = get_package_root()

if MCP_ROOT is None:
    print("[FAIL] Cannot find mcp-global-rules directory")
    print("Make sure you're running from a project with mcp-global-rules installed")
    sys.exit(1)

# Add MCP root to path for imports
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

# Store for other modules to use
os.environ['MCP_ROOT'] = str(MCP_ROOT)


def show_help():
    """Show help message."""
    print("""
MCP AI Enhancement Tools (48 Commands)
=======================================

Usage: python3 mcp-global-rules/mcp.py <command> [args...]

Code Quality:
    review [path] [--strict]    Code review automation
    docs [path] [--write]       Generate missing docstrings
    test [path]                 Generate pytest test stubs
    deadcode [path]             Find unused code
    fix [path] [--safe --apply] Auto-fix issues

Analysis:
    deps [path]                 Dependency analysis
    profile [path]              Performance/complexity
    security [path]             Security audit
    errors [path]               Error handling
    architecture [path]         Architecture validation

Intelligence:
    context "query" [path]      Smart context extraction
    find "query" [path]         Natural language search
    refactor [path]             Suggest refactorings

Indexes:
    index-all                   Full reindex (all 7)
    git-history [file]          Git commit history
    todos                       List TODOs/FIXMEs
    impact [file]               What breaks?
    test-coverage               Coverage data

AI Memory:
    remember "key" "value"      Store knowledge
    recall "query"              Search memories
    forget "key"                Remove memory
    learn [--patterns]          Learn from feedback

AI Prediction:
    predict-bugs [file]         Predict bugs
    risk-score                  Change risk score
    test-gen [file] --impl      Generate full tests

Multi-Repo:
    search-all "query"          Search all projects
    repos --add [path]          Manage repos

CI/CD:
    github-action               Generate workflow
    pipeline [--gitlab]         Generate pipeline

Automation:
    watch [path]                Live index updates
    autocontext                 Auto-load context
    warm                        Pre-warm indexes

Setup:
    setup --all                 Full setup
    setup --hooks               Install git hooks
    setup --profile             Install shell profile
""")


# Map commands to modules
COMMANDS = {
    # Original tools
    'test': 'auto_test',
    'docs': 'auto_docs',
    'deadcode': 'dead_code',
    'deps': 'deps',
    'summarize': 'summarize',
    'changelog': 'changelog',
    'review': 'review',
    # Phase 2 tools
    'context': 'context',
    'refactor': 'refactor',
    'apidocs': 'api_docs',
    'coverage': 'doc_coverage',
    'security': 'security',
    'profile': 'profile',
    "rem": "reminder",
    "rec": "record",
    "cybersec": "cybersec",
    "nsync": "nsync",
    "comms": "agent_comms",
    "model": "model_manager",
    'find': 'finder',
    'errors': 'errors',
    'migrate': 'migrate',
    'architecture': 'architecture',
    'arch': 'architecture',
    'fix': 'fix',
    'record': 'record',
    'trigger-loop': 'trigger_loop',
    # Semantic
    'index': 'vector_store',
    'search': 'vector_store',
    'pattern': 'astgrep',
    'parse': 'treesitter_utils',
    'embed': 'embeddings',
    # Automation
    'watch': 'watcher',
    'autocontext': 'autocontext',
    'auto': 'autocontext',
    # Advanced indexes
    'index-all': 'index_all',
    'git-history': 'git_index',
    'blame': 'git_index',
    'todos': 'todo_index',
    'impact': 'impact',
    'test-coverage': 'coverage_index',
    'doc-index': 'doc_index',
    'config-index': 'config_index',
    # AI Enhancements
    'remember': 'memory',
    'recall': 'memory',
    'forget': 'memory',
    'learn': 'learning',
    'predict-bugs': 'predict',
    'risk-score': 'predict',
    'search-all': 'multi_repo',
    'repos': 'multi_repo',
    'github-action': 'cicd',
    'pipeline': 'cicd',
    'test-gen': 'test_gen',
    # Setup & Automation
    'setup': 'setup',
    'warm': 'warm',
    'auto-learn': 'auto_learn',
}


def main():
    """Main entry point."""
    if len(sys.argv) < 2 or sys.argv[1] in ('help', '-h', '--help'):
        show_help()
        return 0

    command = sys.argv[1]
    args = sys.argv[2:]

    if command not in COMMANDS:
        print(f"[FAIL] Unknown command: {command}")
        show_help()
        return 1

    module_name = COMMANDS[command]

    try:
        # Import the module
        module = __import__(f'scripts.{module_name}', fromlist=[module_name])

        # Update sys.argv for the module
        sys.argv = [f'scripts/{module_name}.py'] + args

        if hasattr(module, 'main'):
            return module.main() or 0
        else:
            print(f"[FAIL] Module {module_name} has no main function")
            return 1

    except ImportError as e:
        print(f"[FAIL] Could not import {module_name}: {e}")
        print(f"MCP_ROOT: {MCP_ROOT}")
        print(f"sys.path: {sys.path[:3]}")
        return 1
    except Exception as e:
        print(f"[FAIL] Error running {command}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
