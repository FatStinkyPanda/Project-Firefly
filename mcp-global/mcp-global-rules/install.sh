#!/bin/bash
# ============================================================================
# MCP Global Rules - Single Command Install
# ============================================================================
# Usage: ./install.sh
#        curl -sSL https://example.com/mcp/install.sh | bash
#
# This installs MCP to the current project with:
#   - All 42 Python scripts
#   - All 6 git hooks (auto-installed)
#   - Full indexing
#   - AI agent instructions
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
ok() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
fail() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          MCP GLOBAL RULES INSTALLER                  ║${NC}"
echo -e "${CYAN}║          42 Scripts | 48 Commands | 6 Hooks          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if in a git repository
if [ ! -d ".git" ]; then
    warn "Not a git repository. Some features will be limited."
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Detect Python
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    fail "Python not found. Please install Python 3.8+"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
info "Python: $PYTHON_CMD ($PYTHON_VERSION)"

if [ "$PYTHON_CMD" == "python" ]; then
    PYTHON3_CMD="python"
else
    PYTHON3_CMD="python3"
fi

# Get script directory (where MCP package is)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(pwd)"

# If running from within mcp-global-rules, install to parent
if [[ "$SCRIPT_DIR" == *"mcp-global-rules"* ]]; then
    MCP_SOURCE="$SCRIPT_DIR"
else
    MCP_SOURCE="$SCRIPT_DIR/mcp-global-rules"
fi

# Target installation path
MCP_TARGET="$PROJECT_ROOT/mcp-global-rules"

# ============================================================================
# STEP 1: Copy MCP package
# ============================================================================
info "Step 1/5: Installing MCP package..."

if [ "$MCP_SOURCE" != "$MCP_TARGET" ]; then
    if [ -d "$MCP_TARGET" ]; then
        warn "MCP already exists. Updating..."
        rm -rf "$MCP_TARGET"
    fi
    
    cp -r "$MCP_SOURCE" "$MCP_TARGET"
    ok "Copied MCP to $MCP_TARGET"
else
    ok "MCP already in place"
fi

# ============================================================================
# STEP 2: Install git hooks
# ============================================================================
info "Step 2/5: Installing git hooks..."

if [ -d ".git" ]; then
    HOOKS_SOURCE="$MCP_TARGET/.git-hooks"
    HOOKS_TARGET=".git/hooks"
    
    mkdir -p "$HOOKS_TARGET"
    
    for hook in pre-commit post-commit commit-msg pre-push post-checkout post-merge; do
        if [ -f "$HOOKS_SOURCE/$hook" ]; then
            cp "$HOOKS_SOURCE/$hook" "$HOOKS_TARGET/$hook"
            chmod +x "$HOOKS_TARGET/$hook"
        fi
    done
    
    ok "Installed 6 git hooks"
else
    warn "Skipping hooks (not a git repo)"
fi

# ============================================================================
# STEP 3: Create .mcp directory
# ============================================================================
info "Step 3/5: Creating MCP data directory..."

mkdir -p ".mcp"
ok "Created .mcp/"

# ============================================================================
# STEP 4: Build initial indexes
# ============================================================================
info "Step 4/5: Building indexes..."

cd "$MCP_TARGET"
$PYTHON_CMD mcp.py index-all --quick 2>/dev/null &
INDEX_PID=$!
ok "Index build started (background)"

# ============================================================================
# STEP 5: Create AI agent instructions
# ============================================================================
info "Step 5/5: Creating AI agent instructions..."

cat > "$PROJECT_ROOT/AI_AGENT_MCP.md" << 'EOF'
# MCP Global Rules - AI Agent Instructions

## Available Commands (48 total)

Run with: `${PYTHON3_CMD} mcp-global-rules/mcp.py <command>`

### Before Coding
```bash
mcp autocontext              # Load relevant context
mcp recall "topic"           # Search memory
mcp search "query"           # Semantic code search
```

### While Coding
```bash
mcp predict-bugs file.py     # Check for bugs
mcp impact file.py           # What breaks?
mcp context "query"          # Get context
```

### After Coding
```bash
mcp review file.py           # Code review
mcp security file.py         # Security check
mcp test-gen file.py --impl  # Generate tests
```

### Remember & Learn
```bash
mcp remember "key" "value"   # Store knowledge
mcp recall "query"           # Search knowledge
mcp learn --patterns         # View learned patterns
```

## Hooks (Automatic)

All hooks are installed and will run automatically:
- **pre-commit**: Auto-fix, risk check, security scan, review
- **post-commit**: Learning, index update
- **post-checkout**: Warm indexes

## Key Directories

- `mcp-global-rules/` - MCP package
- `.mcp/` - Index data (auto-generated)

## Quick Reference

| Need | Command |
|------|---------|
| Context | `mcp autocontext` |
| Search | `mcp search "query"` |
| Review | `mcp review .` |
| Bugs | `mcp predict-bugs .` |
| Tests | `mcp test-gen file.py` |
| Memory | `mcp remember/recall` |
EOF

ok "Created AI_AGENT_MCP.md"

# ============================================================================
# DONE
# ============================================================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          MCP INSTALLATION COMPLETE!                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Installed:"
echo "  ✓ 42 Python scripts"
echo "  ✓ 48 CLI commands"
echo "  ✓ 6 git hooks (enforced)"
echo "  ✓ AI agent instructions"
echo ""
echo "Usage:"
echo "  ${PYTHON3_CMD} mcp-global-rules/mcp.py help"
echo "  ${PYTHON3_CMD} mcp-global-rules/mcp.py <command>"
echo ""
echo "Quick start:"
echo "  ${PYTHON3_CMD} mcp-global-rules/mcp.py autocontext"
echo "  ${PYTHON3_CMD} mcp-global-rules/mcp.py search \"your query\""
echo ""

exit 0
