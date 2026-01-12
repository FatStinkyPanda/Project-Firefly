@echo off
REM Comprehensive rebuild of ALL native modules for Firefly IDE
REM This script rebuilds all Node.js native addons for Electron 39.2.7

setlocal enabledelayedexpansion

set VSCODE_DIR=C:\Users\dbiss\Desktop\Projects\Personal\Project-Firefly\vscode
set LOG_FILE=%VSCODE_DIR%\native_rebuild_all.log
set TARGET=39.2.7
set ARCH=x64
set DIST_URL=https://electronjs.org/headers

echo ============================================
echo Rebuilding ALL Native Modules for Firefly IDE
echo Electron Target: %TARGET%
echo Architecture: %ARCH%
echo ============================================
echo.
echo Log file: %LOG_FILE%
echo.

REM Clear the log file
echo Build started at %DATE% %TIME% > "%LOG_FILE%"

REM List of all native modules to build
set MODULES=@vscode\spdlog @vscode\sqlite3 @vscode\policy-watcher @vscode\windows-mutex @vscode\deviceid @vscode\windows-ca-certs @vscode\windows-process-tree native-keymap native-watchdog native-is-elevated node-pty kerberos windows-foreground-love @parcel\watcher

for %%M in (%MODULES%) do (
    echo.
    echo ---------------------------------------- >> "%LOG_FILE%"
    echo Building %%M... >> "%LOG_FILE%"
    echo ---------------------------------------- >> "%LOG_FILE%"
    echo Rebuilding %%M...
    
    cd /d "%VSCODE_DIR%\node_modules\%%M"
    if exist binding.gyp (
        call node-gyp rebuild --target=%TARGET% --arch=%ARCH% --dist-url=%DIST_URL% >> "%LOG_FILE%" 2>&1
        if !ERRORLEVEL! NEQ 0 (
            echo   FAILED: %%M
            echo FAILED: %%M >> "%LOG_FILE%"
        ) else (
            echo   SUCCESS: %%M
            echo SUCCESS: %%M >> "%LOG_FILE%"
        )
    ) else (
        echo   SKIPPED: %%M ^(no binding.gyp^)
        echo SKIPPED: %%M - no binding.gyp >> "%LOG_FILE%"
    )
)

echo.
echo ============================================
echo Build complete at %DATE% %TIME%
echo See %LOG_FILE% for details.
echo ============================================
