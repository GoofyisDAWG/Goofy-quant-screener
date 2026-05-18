@echo off
:: ═══════════════════════════════════════════════════════════
::   GOOFY SCREENER — PHASE 3  (Windows launcher)
::   Double-click this file to run the full multi-market scan
::   Markets: US + ASX + Japan (JPX)
:: ═══════════════════════════════════════════════════════════

echo.
echo  Starting Goofy Phase 3 Screener...
echo  Markets: US + ASX + JPX
echo  This will take ~5-15 minutes depending on internet speed.
echo.

:: Try Anaconda Python first, then fall back to system Python
set SCRIPT_DIR=%~dp0

:: Try common Anaconda paths
if exist "%USERPROFILE%\anaconda3\python.exe" (
    set PYTHON="%USERPROFILE%\anaconda3\python.exe"
) else if exist "%USERPROFILE%\miniconda3\python.exe" (
    set PYTHON="%USERPROFILE%\miniconda3\python.exe"
) else if exist "C:\ProgramData\anaconda3\python.exe" (
    set PYTHON="C:\ProgramData\anaconda3\python.exe"
) else (
    set PYTHON=python
)

echo  Using Python: %PYTHON%
echo.

%PYTHON% "%SCRIPT_DIR%goofy_screener_phase3.py" --market ALL

echo.
echo  Done! Check the screener_output folder for your Excel report.
echo.
pause
