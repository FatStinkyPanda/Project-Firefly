@echo off
REM Install Spectre-mitigated libraries for Visual Studio 2026 Build Tools
REM This script must be run as Administrator

echo ============================================
echo Installing Spectre-Mitigated Libraries
echo for Visual Studio 2026 Build Tools
echo ============================================
echo.
echo This will install the following components:
echo   - MSVC v145 x64/x86 Spectre-mitigated libs
echo.

set LOG_FILE=%~dp0spectre_install.log
echo Log file: %LOG_FILE%
echo.

"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vs_installer.exe" modify ^
    --installPath "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools" ^
    --add Microsoft.VisualStudio.Component.VC.Runtimes.x86.x64.Spectre ^
    --quiet --norestart > "%LOG_FILE%" 2>&1

set EXIT_CODE=%ERRORLEVEL%
echo Exit code: %EXIT_CODE% >> "%LOG_FILE%"

if %EXIT_CODE% EQU 0 (
    echo SUCCESS: Spectre libraries installed!
) else (
    echo FAILED: Exit code %EXIT_CODE%
    echo Check log file for details.
)

echo.
echo ============================================
type "%LOG_FILE%"
echo ============================================
pause
