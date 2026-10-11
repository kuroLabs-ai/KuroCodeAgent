@echo off
cd /d "%~dp0.."
title KURO 2.0 Standalone Builder
echo ============================================================
echo   KURO 2.0 Console Executable Builder
echo ============================================================
echo.

python build/build_exe.py %*

echo.
if %ERRORLEVEL% EQU 0 (
    echo ============================================================
    echo   BUILD SUCCESSFUL! Executable built in dist\KuroConsole
    echo ============================================================
) else (
    echo ============================================================
    echo   BUILD FAILED! Check error output above.
    echo ============================================================
)
echo.
pause

