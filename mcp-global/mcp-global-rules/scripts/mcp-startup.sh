#!/bin/bash
# MCP Bash/Zsh Startup Script
# Source in .bashrc or .zshrc: source ~/.mcp/scripts/mcp-startup.sh

# MCP installation path
# Defaults to directory containing this script's parent
if [ -z "$MCP_HOME" ]; then
    MCP_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
MCP_PATH="$MCP_HOME"

# Check if MCP is installed
mcp_installed() {
    [ -f "$MCP_PATH/mcp.py" ]
}

# Start MCP watch mode in background
mcp-watch-start() {
    if ! mcp_installed; then
        echo "[MCP] Not installed"
        return 1
    fi
    
    # Check if already running
    local pid_file="$MCP_PATH/watcher.pid"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file" 2>/dev/null)
        if kill -0 "$pid" 2>/dev/null; then
            echo "[MCP] Watch already running (PID $pid)"
            return 0
        fi
    fi
    
    # Start in background
    python3 "$MCP_PATH/mcp.py" watch &
    echo "[MCP] Watch mode started"
}

# Stop MCP watch mode
mcp-watch-stop() {
    python3 "$MCP_PATH/mcp.py" watch --stop
}

# Get AI context
mcp-context() {
    if ! mcp_installed; then
        echo "[MCP] Not installed"
        return 1
    fi
    
    if [ -n "$1" ]; then
        python3 "$MCP_PATH/mcp.py" context "$@"
    else
        python3 "$MCP_PATH/mcp.py" autocontext --auto
    fi
}

# Main MCP command
mcp() {
    if ! mcp_installed; then
        echo "[MCP] Not installed. Run:"
        echo "  curl -sSL https://mcp.example/install.sh | bash"
        return 1
    fi
    
    python3 "$MCP_PATH/mcp.py" "$@"
}

# Remember something
remember() {
    mcp remember "$1" "$2"
}

# Recall something
recall() {
    mcp recall "$1"
}

# Predict bugs in current directory
predict() {
    mcp predict-bugs "${1:-.}"
}

# Full index
reindex() {
    mcp index-all
}

# Aliases
alias ctx='mcp-context'
alias rem='remember'
alias rec='recall'

# Auto-start watch mode (uncomment to enable)
# if mcp_installed; then
#     mcp-watch-start 2>/dev/null
# fi

# Prompt integration (optional)
# Shows MCP status in prompt
mcp_prompt() {
    if [ -f "$MCP_PATH/watcher.pid" ]; then
        local pid=$(cat "$MCP_PATH/watcher.pid" 2>/dev/null)
        if kill -0 "$pid" 2>/dev/null; then
            echo "⚡"
        fi
    fi
}

# Auto-start NSync watch for the main project directory if it exists
NSYNC_DIR="/home/p4nd4pr0t0c01/Projects/NSync"
if [ -d "$NSYNC_DIR" ]; then
    if [[ $- == *i* ]]; then
        echo -e "\033[0;36m[MCP] Starting NSync & Autonomous Collaboration background services...\033[0m"
    fi
    (cd "$NSYNC_DIR" && python3 "$MCP_HOME/mcp.py" nsync watch > /dev/null 2>&1 &)
fi

# Wrap the message in a check for interactive shells
if [[ $- == *i* ]]; then
    echo -e "\033[0;32m[MCP] Shell integration loaded (v1.0)\033[0m"
fi
