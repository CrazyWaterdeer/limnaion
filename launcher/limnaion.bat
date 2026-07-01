@echo off
REM =============================================================
REM  Limnaion TRPG -- Windows Launcher
REM  Tries Windows Terminal (wt) first for a richer experience.
REM  Falls back to running limnaion in the current console window
REM  if wt is not installed.
REM =============================================================
REM  Prerequisites: "limnaion" must be on PATH (installed via pipx
REM  or pip, or the repo's virtual-env activated).

where wt >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    REM  Open a new Windows Terminal tab titled "Limnaion".
    start "" wt new-tab --title "Limnaion" -- cmd /k "limnaion"
) else (
    REM  Plain-cmd fallback: run limnaion in this window, then pause
    REM  so the console stays open if it was launched by double-click.
    limnaion
    pause
)
