@echo off
REM ============================================================
REM  MDTracker git diagnostics (read-only, safe)
REM  Cleans stale lock files, then prints repo state.
REM  Run in project root, then paste the full output back.
REM ============================================================
cd /d "%~dp0"

echo === [1] Remove stale lock files ===
if exist ".git\HEAD.lock"            del /f /q ".git\HEAD.lock"            && echo removed HEAD.lock
if exist ".git\index.lock"           del /f /q ".git\index.lock"           && echo removed index.lock
if exist ".git\refs\heads\main.lock" del /f /q ".git\refs\heads\main.lock" && echo removed main.lock
echo done.

echo.
echo === [2] Local commits (HEAD) ===
git log --oneline -6

echo.
echo === [3] Fetch remote (no merge) ===
git fetch origin

echo.
echo === [4] Remote main commits ===
git log --oneline -6 origin/main

echo.
echo === [5] Working tree status ===
git status

echo.
echo === [6] Do my new files exist on disk? ===
dir /b MDTracker.spec mdtracker\updater.py ".github\workflows\release.yml" main.py version_info.txt installer\MDTracker_Setup.iss 2>nul

echo.
echo === [7] Local tags ===
git tag

echo.
echo === [8] Remote tags ===
git ls-remote --tags origin

echo.
echo === [9] What commit does tag v0.2.0 point to? ===
git rev-list -n 1 v0.2.0 2>nul

echo.
echo ============================================================
echo  Diagnostics complete. Copy ALL the text above and paste back.
echo ============================================================
pause
