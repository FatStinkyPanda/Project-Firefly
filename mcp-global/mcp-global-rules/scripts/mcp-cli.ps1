# MCP CLI - Universal PowerShell Command Line Interface
# Works on Windows PowerShell and PowerShell Core (cross-platform)

param(
    [Parameter(Position = 0)]
    [string]$Command = "help",
    
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "SilentlyContinue"

# Detect OS
function Get-OSType {
    if ($IsWindows -or $env:OS -eq "Windows_NT") { return "windows" }
    elseif ($IsLinux) { return "linux" }
    elseif ($IsMacOS) { return "mac" }
    else { return "unknown" }
}

# Find MCP root directory
function Get-MCPRoot {
    $dir = Get-Location
    while ($dir -and $dir.Path -ne [System.IO.Path]::GetPathRoot($dir.Path)) {
        $mcpPath = Join-Path $dir.Path ".mcp"
        if (Test-Path $mcpPath) {
            return $mcpPath
        }
        $dir = Split-Path $dir.Path -Parent
        if (-not $dir) { break }
        $dir = Get-Item $dir
    }
    
    # Check current directory
    if (Test-Path ".mcp") {
        return (Resolve-Path ".mcp").Path
    }
    
    return $null
}

# Output helpers
function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Blue }
function Write-Ok { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "[WARNING] $msg" -ForegroundColor Yellow }
function Write-Fail { param($msg) Write-Host "[FAIL] $msg" -ForegroundColor Red }
function Write-Header { param($msg) Write-Host "`n=== $msg ===`n" -ForegroundColor Cyan }

# Get timestamp
function Get-Timestamp {
    return (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
}

# Read JSON safely
function Read-JsonFile {
    param([string]$Path)
    if (Test-Path $Path) {
        try {
            $content = Get-Content $Path -Raw
            return $content | ConvertFrom-Json
        }
        catch {
            return @()
        }
    }
    return @()
}

# Write JSON safely
function Write-JsonFile {
    param([string]$Path, [object]$Data)
    $Data | ConvertTo-Json -Depth 10 | Set-Content $Path -Encoding UTF8
}

# Get config value
function Get-ConfigValue {
    param([string]$Key)
    $configPath = Join-Path $script:MCPRoot "config.json"
    if (Test-Path $configPath) {
        $config = Get-Content $configPath -Raw | ConvertFrom-Json
        return $config.$Key
    }
    return $null
}

# Set config value
function Set-ConfigValue {
    param([string]$Key, [string]$Value)
    $configPath = Join-Path $script:MCPRoot "config.json"
    if (Test-Path $configPath) {
        $config = Get-Content $configPath -Raw | ConvertFrom-Json
        $config.$Key = $Value
        $config | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8
    }
}

# =============================================================================
# COMMANDS
# =============================================================================

function Invoke-Init {
    param([string[]]$params)
    
    Write-Header "Initialize MCP for Project"
    
    $projectName = if ($params.Count -gt 0) { $params[0] } else {
        Read-Host "Project name (e.g., MyOrg/MyProject)"
    }
    
    $author = if ($params.Count -gt 1) { $params[1] } else {
        Read-Host "Author name"
    }
    
    Set-ConfigValue "project" $projectName
    Set-ConfigValue "author" $author
    Set-ConfigValue "created" (Get-Timestamp)
    
    Write-Ok "Project initialized: $projectName"
    Write-Ok "Author: $author"
    
    Invoke-Record @("action", "Initialized MCP for project $projectName")
}

function Invoke-Status {
    Write-Header "MCP Status"
    
    $project = Get-ConfigValue "project"
    $author = Get-ConfigValue "author"
    $os = Get-OSType
    
    Write-Host "Project:  $(if ($project) { $project } else { '[not set]' })"
    Write-Host "Author:   $(if ($author) { $author } else { '[not set]' })"
    Write-Host "OS:       $os"
    Write-Host "MCP Root: $script:MCPRoot"
    Write-Host ""
    
    # Count entries
    $actions = (Read-JsonFile (Join-Path $script:MCPRoot "memory\actions.json")).Count
    $decisions = (Read-JsonFile (Join-Path $script:MCPRoot "memory\decisions.json")).Count
    $todos = (Read-JsonFile (Join-Path $script:MCPRoot "memory\todos.json")).Count
    $sessions = (Read-JsonFile (Join-Path $script:MCPRoot "memory\sessions.json")).Count
    
    Write-Host "Memory Store:"
    Write-Host "  Actions:   $actions"
    Write-Host "  Decisions: $decisions"
    Write-Host "  TODOs:     $todos"
    Write-Host "  Sessions:  $sessions"
    Write-Host ""
    
    Invoke-Compliance -Quiet
}

function Invoke-Record {
    param([string[]]$params)
    
    if ($params.Count -lt 2) {
        Write-Fail "Usage: mcp record <type> <content>"
        Write-Host "Types: action, decision, todo, milestone, session"
        return
    }
    
    $type = $params[0]
    $content = $params[1..($params.Count - 1)] -join " "
    
    $entry = @{
        id        = [DateTimeOffset]::Now.ToUnixTimeMilliseconds().ToString()
        type      = $type
        content   = $content
        project   = Get-ConfigValue "project"
        author    = Get-ConfigValue "author"
        timestamp = Get-Timestamp
    }
    
    $typeMap = @{
        "action" = "actions"; "actions" = "actions"
        "decision" = "decisions"; "decisions" = "decisions"
        "todo" = "todos"; "todos" = "todos"
        "milestone" = "milestones"; "milestones" = "milestones"
        "session" = "sessions"; "sessions" = "sessions"
    }
    
    $fileName = $typeMap[$type]
    if (-not $fileName) {
        Write-Fail "Unknown type: $type"
        return
    }
    
    $filePath = Join-Path $script:MCPRoot "memory\$fileName.json"
    $data = Read-JsonFile $filePath
    if ($data -isnot [array]) { $data = @() }
    $data += $entry
    Write-JsonFile $filePath $data
    
    Write-Ok "Recorded $type`: $content"
}

function Invoke-Query {
    param([string[]]$params)
    
    $type = if ($params.Count -gt 0) { $params[0] } else { "recent" }
    $limit = if ($params.Count -gt 1) { [int]$params[1] } else { 10 }
    
    switch ($type) {
        { $_ -in "recent", "actions" } {
            Write-Header "Recent Actions (last $limit)"
            $actions = Read-JsonFile (Join-Path $script:MCPRoot "memory\actions.json")
            $actions | Select-Object -Last $limit | ForEach-Object {
                Write-Host "  - $($_.content)"
            }
        }
        "decisions" {
            Write-Header "Decisions"
            $decisions = Read-JsonFile (Join-Path $script:MCPRoot "memory\decisions.json")
            $decisions | ForEach-Object { Write-Host "  - $($_.content)" }
        }
        "todos" {
            Write-Header "TODOs"
            $todos = Read-JsonFile (Join-Path $script:MCPRoot "memory\todos.json")
            $todos | ForEach-Object { Write-Host "  [ ] $($_.content)" }
        }
        default {
            Write-Host "Usage: mcp query <type> [limit]"
            Write-Host "Types: recent, actions, decisions, todos"
        }
    }
}

function Invoke-Search {
    param([string[]]$params)
    
    if ($params.Count -lt 1) {
        Write-Fail "Usage: mcp search <query>"
        return
    }
    
    $query = $params -join " "
    Write-Header "Search Results: '$query'"
    
    $memoryDir = Join-Path $script:MCPRoot "memory"
    Get-ChildItem $memoryDir -Filter "*.json" | ForEach-Object {
        $fileName = $_.BaseName
        $data = Read-JsonFile $_.FullName
        $data | Where-Object { $_.content -like "*$query*" } | ForEach-Object {
            Write-Host "  [$fileName] $($_.content)"
        }
    }
}

function Invoke-Compliance {
    param([switch]$Quiet)
    
    $actions = (Read-JsonFile (Join-Path $script:MCPRoot "memory\actions.json")).Count
    $decisions = (Read-JsonFile (Join-Path $script:MCPRoot "memory\decisions.json")).Count
    $todos = (Read-JsonFile (Join-Path $script:MCPRoot "memory\todos.json")).Count
    
    $score = 50
    if ($actions -gt 0) { $score += 20 }
    if ($actions -gt 5) { $score += 10 }
    if ($decisions -gt 0) { $score += 10 }
    if ($todos -gt 0) { $score += 10 }
    if ($score -gt 100) { $score = 100 }
    
    if (-not $Quiet) {
        Write-Header "Compliance Check"
    }
    
    Write-Host "Compliance Score: $score%"
    
    if ($score -ge 80) {
        Write-Ok "Ready for commit (>= 80)"
    }
    elseif ($score -ge 70) {
        Write-Warn "Acceptable for push (>= 70)"
    }
    else {
        Write-Warn "Low compliance - record more actions"
    }
}

function Invoke-Go {
    Write-Header "MCP Interactive Mode"
    
    Invoke-Status
    
    Write-Host ""
    Write-Host "What would you like to do?"
    Write-Host "  1) Record an action"
    Write-Host "  2) Record a decision"
    Write-Host "  3) Add a TODO"
    Write-Host "  4) Query memory"
    Write-Host "  5) Check compliance"
    Write-Host "  6) Exit"
    Write-Host ""
    $choice = Read-Host "Choice"
    
    switch ($choice) {
        "1" {
            $action = Read-Host "Action"
            Invoke-Record @("action", $action)
        }
        "2" {
            $decision = Read-Host "Decision"
            Invoke-Record @("decision", $decision)
        }
        "3" {
            $todo = Read-Host "TODO"
            Invoke-Record @("todo", $todo)
        }
        "4" { Invoke-Query @("recent") }
        "5" { Invoke-Compliance }
        "6" { Write-Ok "Goodbye!" }
        default { Write-Warn "Invalid choice" }
    }
}

function Invoke-Config {
    param([string[]]$params)
    
    $action = if ($params.Count -gt 0) { $params[0] } else { "show" }
    
    switch ($action) {
        "show" {
            Write-Header "Configuration"
            Get-Content (Join-Path $script:MCPRoot "config.json")
        }
        "set" {
            if ($params.Count -lt 3) {
                Write-Fail "Usage: mcp config set <key> <value>"
                return
            }
            $key = $params[1]
            $value = $params[2]
            Set-ConfigValue $key $value
            Write-Ok "Set $key = $value"
        }
        default {
            Write-Host "Usage: mcp config <show|set> [key] [value]"
        }
    }
}

function Invoke-Help {
    Write-Host ""
    Write-Host "MCP Global Rules CLI"
    Write-Host ""
    Write-Host "Usage: mcp <command> [options]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  init [project] [author]   Initialize MCP for project"
    Write-Host "  status                    Show project status"
    Write-Host "  record <type> <content>   Record action/decision/todo"
    Write-Host "  query <type> [limit]      Query memory"
    Write-Host "  search <query>            Search all entries"
    Write-Host "  compliance                Check compliance score"
    Write-Host "  config <show|set>         View/modify configuration"
    Write-Host "  go                        Interactive mode"
    Write-Host "  help                      Show this help"
    Write-Host ""
    Write-Host "Record Types: action, decision, todo, milestone, session"
    Write-Host "Query Types:  recent, actions, decisions, todos"
    Write-Host ""
}

# =============================================================================
# MAIN
# =============================================================================

$script:MCPRoot = Get-MCPRoot

if (-not $script:MCPRoot) {
    Write-Fail "MCP not initialized. Run installer first or cd to project directory."
    exit 1
}

switch ($Command.ToLower()) {
    "init" { Invoke-Init $Args }
    "status" { Invoke-Status }
    "record" { Invoke-Record $Args }
    "query" { Invoke-Query $Args }
    "search" { Invoke-Search $Args }
    "compliance" { Invoke-Compliance }
    "config" { Invoke-Config $Args }
    "go" { Invoke-Go }
    { $_ -in "help", "--help", "-h" } { Invoke-Help }
    default {
        Write-Fail "Unknown command: $Command"
        Invoke-Help
        exit 1
    }
}
