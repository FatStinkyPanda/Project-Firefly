# MCP Global Rules - Bundled Dependencies

## Core Python Tools (18 scripts)

All MCP Python tools use **Python 3.11+ standard library ONLY**. No external dependencies required.

### Stdlib Modules Used
- `ast` - Abstract syntax trees for code analysis
- `sys` - System-specific parameters
- `os` - Operating system interface  
- `re` - Regular expressions
- `pathlib` - Object-oriented paths
- `typing` - Type hints
- `dataclasses` - Data classes
- `collections` - Container datatypes
- `json` - JSON encoder/decoder
- `subprocess` - Subprocess management
- `datetime` - Date and time
- `enum` - Enumerations
- `hashlib` - Secure hashes
- `math` - Mathematical functions

## Bundled Vendor Packages (90 wheels)

Optional tools bundled for enhanced functionality. Located in `vendor/python-packages-py311/`:

### Code Quality
- `pylint-4.0.4` - Python linter
- `flake8-7.3.0` - Style guide enforcement
- `black-25.12.0` - Code formatter
- `isort-7.0.0` - Import sorter
- `mypy-1.19.1` - Static type checker

### Security
- `bandit-1.9.2` - Security linter
- `safety-3.7.0` - Dependency vulnerability scanner
- `pip_audit-2.10.0` - Pip audit tool

### Testing
- `pytest-9.0.2` - Testing framework
- `pytest_cov-7.0.0` - Coverage plugin
- `coverage-7.13.1` - Code coverage

### Analysis
- `radon-6.0.1` - Code metrics
- `astroid-4.0.2` - AST analysis

### Other Bundled Tools
- `pre_commit-4.5.1` - Pre-commit hooks
- `rich-14.2.0` - Rich text formatting
- `pydantic-2.12.5` - Data validation
- `requests-2.32.5` - HTTP library
- `cryptography-46.0.3` - Cryptographic recipes
- ... and 70+ more supporting packages

## Installation

### Option 1: Core Tools Only (No Installation)
```bash
# Just copy and run - works immediately
python mcp.py help
python mcp.py review src/
```

### Option 2: Install Bundled Wheels Locally
```bash
# Install all bundled packages offline
pip install --no-index --find-links=vendor/python-packages-py311 pylint flake8 black mypy bandit pytest
```

### Option 3: Full Installation Script
```bash
./install.sh   # Linux/Mac
.\install.ps1  # Windows
```

## Offline Verification

To verify you have everything needed:
```bash
# Test core tools (no dependencies)
python mcp.py help

# Test optional tools from vendor
pip install --no-index --find-links=vendor/python-packages-py311 pylint
pylint --version
```

## Package Size

| Component | Size |
|-----------|------|
| Core scripts/ | ~200 KB |
| vendor/python-packages-py311/ | ~70 MB |
| vendor/mcp-servers/ | ~5 MB |
| vendor/openmemory-repo/ | ~40 MB |
| **Total** | **~120 MB** |

## No Internet Required

All functionality works completely offline:
- 18 Python tools use stdlib only
- 90 wheel files bundled for optional enhanced tools
- Git hooks work offline
- All MCP memory functions work locally
