@echo off
REM ============================================================
REM  MDTracker recovery - PART 1 (local commit only, NO push)
REM  Stages ONLY the deployment files, commits locally, stops.
REM  After running, paste the full output back for verification.
REM ============================================================
cd /d "%~dp0"

echo === [1] Remove stale lock files ===
if exist ".git\HEAD.lock"            del /f /q ".git\HEAD.lock"
if exist ".git\index.lock"           del /f /q ".git\index.lock"
if exist ".git\refs\heads\main.lock" del /f /q ".git\refs\heads\main.lock"
echo done.

echo.
echo === [2] Stage deployment files explicitly (force per-path) ===
git add -f main.py
git add -f mdtracker/__init__.py
git add -f mdtracker/updater.py
git add -f MDTracker.spec
git add -f version_info.txt
git add -f installer/MDTracker_Setup.iss
git add -f ".github/workflows/release.yml"
git add -f .gitignore
git add -f release_v0.2.0.bat
git add -f commit_msg.txt
git add -f diagnose.bat
git add -f fix_part1_commit.bat

echo.
echo === [3] What is staged? (verify all deployment files are here) ===
git diff --cached --name-only

echo.
echo === [4] Confirm critical files are staged ===
git diff --cached --name-only | findstr /C:"MDTracker.spec"            >nul && echo OK MDTracker.spec            || echo MISSING MDTracker.spec
git diff --cached --name-only | findstr /C:"mdtracker/updater.py"      >nul && echo OK updater.py                || echo MISSING updater.py
git diff --cached --name-only | findstr /C:".github/workflows/release.yml" >nul && echo OK release.yml          || echo MISSING release.yml
git diff --cached --name-only | findstr /C:"main.py"                   >nul && echo OK main.py                   || echo MISSING main.py

echo.
echo === [5] Commit locally (message from commit_msg.txt, UTF-8) ===
git commit -F commit_msg.txt

echo.
echo === [6] New local HEAD ===
git log --oneline -4

echo.
echo ============================================================
echo  PART 1 done. NOTHING was pushed.
echo  Copy ALL output above and paste it back before running PART 2.
echo  In step [4], every line must say "OK". If any says MISSING,
echo  do NOT proceed - report it.
echo ============================================================
pause
