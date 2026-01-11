# MCP PowerShell Startup Script
# Add to your $PROFILE for auto-startup

# MCP installation path
if (-not $env:MCP_HOME) {
    $env:MCP_HOME = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
}
$MCPPath = $env:MCP_HOME

# Check if MCP is installed
function Test-MCPInstalled {
    return (Test-Path "$MCPPath\mcp.py")
}

# Start MCP watch mode in background
function Start-MCPWatcher {
    if (-not (Test-MCPInstalled)) {
        return
    }
    
    # Check if already running
    $pidFile = "$MCPPath\watcher.pid"
    if (Test-Path $pidFile) {
        $pid = Get-Content $pidFile -ErrorAction SilentlyContinue
        if ($pid -and (Get-Process -Id $pid -ErrorAction SilentlyContinue)) {
            return  # Already running
        }
    }
    
    # Start in background
    Start-Job -Name "MCP-Watcher" -ScriptBlock {
        param($mcpPath)
        Set-Location $mcpPath
        python mcp.py watch
    } -ArgumentList $MCPPath | Out-Null
    
    # Auto-start NSync watch for the main project directory if it exists
    $nsync_dir = "C:\Users\dbiss\Desktop\Projects\_BLANK_\NSync"
    if (Test-Path $nsync_dir) {
        Write-Host "[MCP] Starting NSync & Autonomous Collaboration background services..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-Command", "cd $nsync_dir; python $MCPPath/mcp.py nsync watch" -WindowStyle Hidden
    }

    Write-Host "[MCP] Shell integration loaded (v1.0)" -ForegroundColor Green
}

# Stop MCP watch mode
function Stop-MCPWatcher {
    python "$MCPPath\mcp.py" watch --stop
    Write-Host "[MCP] Watch mode stopped" -ForegroundColor Yellow
}

# Get AI context for current directory
function Get-MCPContext {
    param(
        [string]$Query = ""
    )
    
    if (-not (Test-MCPInstalled)) {
        Write-Host "MCP not installed" -ForegroundColor Red
        return
    }
    
    if ($Query) {
        python "$MCPPath\mcp.py" context $Query
    }
    else {
        python "$MCPPath\mcp.py" autocontext --auto
    }
}

# Quick MCP commands
function mcp {
    param(
        [Parameter(Position = 0)]
        [string]$Command,
        [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
        [string[]]$Args
    )
    
    if (-not (Test-MCPInstalled)) {
        Write-Host "MCP not installed. Run: " -NoNewline -ForegroundColor Red
        Write-Host "irm https://mcp.example/install.ps1 | iex" -ForegroundColor Cyan
        return
    }
    
    python "$MCPPath\mcp.py" $Command @Args
}

# Remember something
function Remember {
    param(
        [Parameter(Mandatory = $true, Position = 0)]
        [string]$Key,
        [Parameter(Mandatory = $true, Position = 1)]
        [string]$Value
    )
    
    mcp remember $Key $Value
}

# Recall something
function Recall {
    param(
        [Parameter(Mandatory = $true, Position = 0)]
        [string]$Query
    )
    
    mcp recall $Query
}

# Aliases
Set-Alias -Name ctx -Value Get-MCPContext
Set-Alias -Name rem -Value Remember
Set-Alias -Name rec -Value Recall

# Auto-start watch mode on new terminal (uncomment to enable)
# Start-MCPWatcher

Write-Host "[MCP] PowerShell integration loaded. Type 'mcp help' for commands." -ForegroundColor Cyan
