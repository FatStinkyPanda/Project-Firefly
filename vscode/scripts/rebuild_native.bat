@echo off
REM Rebuild native modules for Firefly IDE
REM This script rebuilds the native Node.js addons for Electron

echo ============================================
echo Rebuilding Native Modules for Firefly IDE
echo ============================================
echo.

set VSCODE_DIR=C:\Users\dbiss\Desktop\Projects\Personal\Project-Firefly\vscode
set LOG_FILE=%VSCODE_DIR%\native_rebuild.log

echo Log file: %LOG_FILE%
echo.

echo Rebuilding @vscode/spdlog...
cd /d "%VSCODE_DIR%\node_modules\@vscode\spdlog"
call node-gyp rebuild --target=39.2.7 --arch=x64 --dist-url=https://electronjs.org/headers >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo FAILED: @vscode/spdlog
) else (
    echo SUCCESS: @vscode/spdlog
)

echo.
echo Rebuilding @vscode/sqlite3...
cd /d "%VSCODE_DIR%\node_modules\@vscode\sqlite3"
call node-gyp rebuild --target=39.2.7 --arch=x64 --dist-url=https://electronjs.org/headers >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo FAILED: @vscode/sqlite3
) else (
    echo SUCCESS: @vscode/sqlite3
)

echo.
echo Rebuilding @vscode/policy-watcher...
cd /d "%VSCODE_DIR%\node_modules\@vscode\policy-watcher"
call node-gyp rebuild --target=39.2.7 --arch=x64 --dist-url=https://electronjs.org/headers >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo FAILED: @vscode/policy-watcher
) else (
    echo SUCCESS: @vscode/policy-watcher
)

echo.
echo ============================================
echo Build complete. Check %LOG_FILE% for details.
echo ============================================
