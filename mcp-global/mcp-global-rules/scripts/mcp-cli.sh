#!/bin/bash
# MCP CLI - Universal Command Line Interface
# Auto-detects OS and works on Windows (Git Bash/WSL), Linux, Mac
# No external dependencies required

# Detect OS and set variables
detect_os() {
    case "$(uname -s)" in
        Linux*)     OS="linux";;
        Darwin*)    OS="mac";;
        CYGWIN*|MINGW*|MSYS*) OS="windows";;
        *)          OS="unknown";;
    esac
    
    # Check for Windows Subsystem for Linux
    if [ "$OS" = "linux" ] && grep -qi microsoft /proc/version 2>/dev/null; then
        OS="wsl"
    fi
}

# Get the MCP root directory
get_mcp_root() {
    # Find .mcp directory by walking up
    local dir="$(pwd)"
    while [ "$dir" != "/" ] && [ "$dir" != "" ]; do
        if [ -d "$dir/.mcp" ]; then
            echo "$dir/.mcp"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    
    # Check current directory
    if [ -d ".mcp" ]; then
        echo "$(pwd)/.mcp"
        return 0
    fi
    
    return 1
}

# Colors (work on most terminals, degrade gracefully)
setup_colors() {
    if [ -t 1 ]; then
        RED='\033[0;31m'
        GREEN='\033[0;32m'
        YELLOW='\033[1;33m'
        BLUE='\033[0;34m'
        CYAN='\033[0;36m'
        BOLD='\033[1m'
        NC='\033[0m'
    else
        RED='' GREEN='' YELLOW='' BLUE='' CYAN='' BOLD='' NC=''
    fi
}

# Output helpers
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
ok() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
header() { echo -e "\n${CYAN}${BOLD}=== $1 ===${NC}\n"; }

# Get current timestamp (works on all platforms)
get_timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S"
}

# Get project name from config
get_project() {
    local config="$MCP_ROOT/config.json"
    if [ -f "$config" ]; then
        grep -o '"project"[[:space:]]*:[[:space:]]*"[^"]*"' "$config" | sed 's/.*: *"\([^"]*\)"/\1/'
    fi
}

# Get author from config
get_author() {
    local config="$MCP_ROOT/config.json"
    if [ -f "$config" ]; then
        grep -o '"author"[[:space:]]*:[[:space:]]*"[^"]*"' "$config" | sed 's/.*: *"\([^"]*\)"/\1/'
    fi
}

# JSON helpers (pure bash, no jq needed)
json_append() {
    local file="$1"
    local entry="$2"
    
    if [ ! -f "$file" ] || [ "$(cat "$file")" = "[]" ]; then
        echo "[$entry]" > "$file"
    else
        # Remove trailing ] and add new entry
        local content
        content=$(cat "$file")
        content="${content%]}"
        echo "${content},$entry]" > "$file"
    fi
}

json_count() {
    local file="$1"
    if [ -f "$file" ]; then
        grep -o '{' "$file" | wc -l | tr -d ' '
    else
        echo "0"
    fi
}

# =============================================================================
# COMMANDS
# =============================================================================

cmd_init() {
    header "Initialize MCP for Project"
    
    local project_name="${1:-}"
    local author="${2:-}"
    
    if [ -z "$project_name" ]; then
        echo -n "Project name (e.g., MyOrg/MyProject): "
        read -r project_name
    fi
    
    if [ -z "$author" ]; then
        echo -n "Author name: "
        read -r author
    fi
    
    # Update config
    local config="$MCP_ROOT/config.json"
    local temp_config="${config}.tmp"
    
    sed "s/\"project\": \"\"/\"project\": \"$project_name\"/" "$config" | \
    sed "s/\"author\": \"\"/\"author\": \"$author\"/" | \
    sed "s/\"created\": \"\"/\"created\": \"$(get_timestamp)\"/" > "$temp_config"
    
    mv "$temp_config" "$config"
    
    ok "Project initialized: $project_name"
    ok "Author: $author"
    
    # Record initialization
    cmd_record "action" "Initialized MCP for project $project_name"
}

cmd_status() {
    header "MCP Status"
    
    local project=$(get_project)
    local author=$(get_author)
    
    echo "Project:  ${project:-[not set]}"
    echo "Author:   ${author:-[not set]}"
    echo "OS:       $OS"
    echo "MCP Root: $MCP_ROOT"
    echo ""
    
    # Count memory entries
    local actions=$(json_count "$MCP_ROOT/memory/actions.json")
    local decisions=$(json_count "$MCP_ROOT/memory/decisions.json")
    local todos=$(json_count "$MCP_ROOT/memory/todos.json")
    local sessions=$(json_count "$MCP_ROOT/memory/sessions.json")
    
    echo "Memory Store:"
    echo "  Actions:   $actions"
    echo "  Decisions: $decisions"
    echo "  TODOs:     $todos"
    echo "  Sessions:  $sessions"
    echo ""
    
    # Compliance check
    cmd_compliance --quiet
}

cmd_record() {
    local type="$1"
    shift
    local content="$*"
    
    if [ -z "$type" ] || [ -z "$content" ]; then
        fail "Usage: mcp record <type> <content>"
        echo "Types: action, decision, todo, milestone, session"
        return 1
    fi
    
    local timestamp=$(get_timestamp)
    local project=$(get_project)
    local author=$(get_author)
    local id=$(date +%s%N 2>/dev/null || date +%s)
    
    local entry="{\"id\":\"$id\",\"type\":\"$type\",\"content\":\"$content\",\"project\":\"$project\",\"author\":\"$author\",\"timestamp\":\"$timestamp\"}"
    
    case "$type" in
        action|actions)
            json_append "$MCP_ROOT/memory/actions.json" "$entry"
            ok "Recorded action: $content"
            ;;
        decision|decisions)
            json_append "$MCP_ROOT/memory/decisions.json" "$entry"
            ok "Recorded decision: $content"
            ;;
        todo|todos)
            json_append "$MCP_ROOT/memory/todos.json" "$entry"
            ok "Recorded TODO: $content"
            ;;
        milestone|milestones)
            json_append "$MCP_ROOT/memory/milestones.json" "$entry"
            ok "Recorded milestone: $content"
            ;;
        session|sessions)
            json_append "$MCP_ROOT/memory/sessions.json" "$entry"
            ok "Recorded session: $content"
            ;;
        *)
            fail "Unknown type: $type"
            return 1
            ;;
    esac
}

cmd_query() {
    local type="$1"
    local limit="${2:-10}"
    
    case "$type" in
        recent|actions)
            header "Recent Actions (last $limit)"
            tail -n "$limit" "$MCP_ROOT/memory/actions.json" 2>/dev/null | \
                grep -o '"content":"[^"]*"' | sed 's/"content":"//; s/"$//' | \
                while read -r line; do echo "  - $line"; done
            ;;
        decisions)
            header "Decisions"
            grep -o '"content":"[^"]*"' "$MCP_ROOT/memory/decisions.json" 2>/dev/null | \
                sed 's/"content":"//; s/"$//' | \
                while read -r line; do echo "  - $line"; done
            ;;
        todos)
            header "TODOs"
            grep -o '"content":"[^"]*"' "$MCP_ROOT/memory/todos.json" 2>/dev/null | \
                sed 's/"content":"//; s/"$//' | \
                while read -r line; do echo "  [ ] $line"; done
            ;;
        *)
            echo "Usage: mcp query <type> [limit]"
            echo "Types: recent, actions, decisions, todos"
            ;;
    esac
}

cmd_search() {
    local query="$1"
    
    if [ -z "$query" ]; then
        fail "Usage: mcp search <query>"
        return 1
    fi
    
    header "Search Results: '$query'"
    
    for file in "$MCP_ROOT/memory/"*.json; do
        local filename=$(basename "$file" .json)
        grep -i "$query" "$file" 2>/dev/null | \
            grep -o '"content":"[^"]*"' | sed 's/"content":"//; s/"$//' | \
            while read -r line; do echo "  [$filename] $line"; done
    done
}

cmd_compliance() {
    local quiet=false
    [ "$1" = "--quiet" ] && quiet=true
    
    local actions=$(json_count "$MCP_ROOT/memory/actions.json")
    local decisions=$(json_count "$MCP_ROOT/memory/decisions.json")
    local todos=$(json_count "$MCP_ROOT/memory/todos.json")
    
    # Simple compliance calculation
    local score=50
    [ "$actions" -gt 0 ] && score=$((score + 20))
    [ "$actions" -gt 5 ] && score=$((score + 10))
    [ "$decisions" -gt 0 ] && score=$((score + 10))
    [ "$todos" -gt 0 ] && score=$((score + 10))
    [ "$score" -gt 100 ] && score=100
    
    if [ "$quiet" = false ]; then
        header "Compliance Check"
    fi
    
    echo "Compliance Score: $score%"
    
    if [ "$score" -ge 80 ]; then
        ok "Ready for commit (>= 80)"
    elif [ "$score" -ge 70 ]; then
        warn "Acceptable for push (>= 70)"
    else
        warn "Low compliance - record more actions"
    fi
}

cmd_go() {
    header "MCP Interactive Mode"
    
    cmd_status
    
    echo ""
    echo "What would you like to do?"
    echo "  1) Record an action"
    echo "  2) Record a decision"
    echo "  3) Add a TODO"
    echo "  4) Query memory"
    echo "  5) Check compliance"
    echo "  6) Exit"
    echo ""
    echo -n "Choice: "
    read -r choice
    
    case "$choice" in
        1)
            echo -n "Action: "
            read -r action
            cmd_record action "$action"
            ;;
        2)
            echo -n "Decision: "
            read -r decision
            cmd_record decision "$decision"
            ;;
        3)
            echo -n "TODO: "
            read -r todo
            cmd_record todo "$todo"
            ;;
        4)
            cmd_query recent
            ;;
        5)
            cmd_compliance
            ;;
        6)
            ok "Goodbye!"
            ;;
        *)
            warn "Invalid choice"
            ;;
    esac
}

cmd_config() {
    local action="$1"
    shift
    
    case "$action" in
        show)
            header "Configuration"
            cat "$MCP_ROOT/config.json"
            ;;
        set)
            local key="$1"
            local value="$2"
            if [ -z "$key" ] || [ -z "$value" ]; then
                fail "Usage: mcp config set <key> <value>"
                return 1
            fi
            
            local config="$MCP_ROOT/config.json"
            sed -i.bak "s/\"$key\": \"[^\"]*\"/\"$key\": \"$value\"/" "$config"
            rm -f "${config}.bak"
            ok "Set $key = $value"
            ;;
        *)
            echo "Usage: mcp config <show|set> [key] [value]"
            ;;
    esac
}

cmd_help() {
    echo ""
    echo "MCP Global Rules CLI"
    echo ""
    echo "Usage: mcp <command> [options]"
    echo ""
    echo "Commands:"
    echo "  init [project] [author]   Initialize MCP for project"
    echo "  status                    Show project status"
    echo "  record <type> <content>   Record action/decision/todo"
    echo "  query <type> [limit]      Query memory"
    echo "  search <query>            Search all entries"
    echo "  compliance                Check compliance score"
    echo "  config <show|set>         View/modify configuration"
    echo "  go                        Interactive mode"
    echo "  help                      Show this help"
    echo ""
    echo "AI Enhancement Tools (Python 3.11+):"
    echo "  test [path]               Generate pytest tests"
    echo "  docs [path] [--write]     Generate missing docstrings"
    echo "  deadcode [path]           Find unused code"
    echo "  deps [path]               Analyze dependencies"
    echo "  summarize [path]          Generate codebase summary"
    echo "  changelog [--since tag]   Generate changelog from commits"
    echo "  review [path] [--strict]  Run code review checks"
    echo ""
    echo "Record Types: action, decision, todo, milestone, session"
    echo "Query Types:  recent, actions, decisions, todos"
    echo ""
}

# Python tool commands
cmd_test() {
    local python_cmd
    python_cmd=$(command -v python3 || command -v python)
    if [ -z "$python_cmd" ]; then
        fail "Python not found"
        return 1
    fi
    
    $python_cmd "$MCP_ROOT/scripts/auto_test.py" "$@"
}

cmd_docs() {
    local python_cmd
    python_cmd=$(command -v python3 || command -v python)
    if [ -z "$python_cmd" ]; then
        fail "Python not found"
        return 1
    fi
    
    $python_cmd "$MCP_ROOT/scripts/auto_docs.py" "$@"
}

cmd_deadcode() {
    local python_cmd
    python_cmd=$(command -v python3 || command -v python)
    if [ -z "$python_cmd" ]; then
        fail "Python not found"
        return 1
    fi
    
    $python_cmd "$MCP_ROOT/scripts/dead_code.py" "$@"
}

cmd_deps() {
    local python_cmd
    python_cmd=$(command -v python3 || command -v python)
    if [ -z "$python_cmd" ]; then
        fail "Python not found"
        return 1
    fi
    
    $python_cmd "$MCP_ROOT/scripts/deps.py" "$@"
}

cmd_summarize() {
    local python_cmd
    python_cmd=$(command -v python3 || command -v python)
    if [ -z "$python_cmd" ]; then
        fail "Python not found"
        return 1
    fi
    
    $python_cmd "$MCP_ROOT/scripts/summarize.py" "$@"
}

cmd_changelog() {
    local python_cmd
    python_cmd=$(command -v python3 || command -v python)
    if [ -z "$python_cmd" ]; then
        fail "Python not found"
        return 1
    fi
    
    $python_cmd "$MCP_ROOT/scripts/changelog.py" "$@"
}

cmd_review() {
    local python_cmd
    python_cmd=$(command -v python3 || command -v python)
    if [ -z "$python_cmd" ]; then
        fail "Python not found"
        return 1
    fi
    
    $python_cmd "$MCP_ROOT/scripts/review.py" "$@"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    setup_colors
    detect_os
    
    MCP_ROOT=$(get_mcp_root)
    if [ -z "$MCP_ROOT" ]; then
        fail "MCP not initialized. Run installer first or cd to project directory."
        exit 1
    fi
    
    export MCP_ROOT
    
    local command="${1:-help}"
    shift 2>/dev/null || true
    
    case "$command" in
        init)       cmd_init "$@" ;;
        status)     cmd_status "$@" ;;
        record)     cmd_record "$@" ;;
        query)      cmd_query "$@" ;;
        search)     cmd_search "$@" ;;
        compliance) cmd_compliance "$@" ;;
        config)     cmd_config "$@" ;;
        go)         cmd_go "$@" ;;
        # AI Enhancement Tools
        test)       cmd_test "$@" ;;
        docs)       cmd_docs "$@" ;;
        deadcode)   cmd_deadcode "$@" ;;
        deps)       cmd_deps "$@" ;;
        summarize)  cmd_summarize "$@" ;;
        changelog)  cmd_changelog "$@" ;;
        review)     cmd_review "$@" ;;
        help|--help|-h) cmd_help ;;
        *)
            fail "Unknown command: $command"
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"
