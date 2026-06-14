@echo off
REM ============================================================
REM  MDTracker v0.2.0 release script (run on Windows)
REM  Usage: double-click in project root (F:\AI\mdtracker)
REM         or run "release_v0.2.0.bat" from a cmd window
REM ============================================================
cd /d "%~dp0"

echo.
echo === [1/6] Repair corrupt git index / stale lock ===
if exist ".git\index.lock" del /f /q ".git\index.lock"
if exist ".git\index"      del /f /q ".git\index"
git read-tree HEAD
if errorlevel 1 (
  echo [ERROR] index repair failed. Check manually.
  pause
  exit /b 1
)
echo index repaired.

echo.
echo === [2/6] Show changes ===
git status --short

echo.
echo === [3/6] Stage files ===
git add main.py mdtracker/__init__.py mdtracker/updater.py
git add MDTracker.spec version_info.txt
git add installer/MDTracker_Setup.iss
git add .github/workflows/release.yml
git add docs/build_guide.md
git add .gitignore release_v0.2.0.bat commit_msg.txt

echo.
echo === [4/6] Commit (message from commit_msg.txt, UTF-8) ===
git commit -F commit_msg.txt
if errorlevel 1 (
  echo [NOTE] Nothing to commit or commit error. Check message above.
)

echo.
echo === [5/6] Create version tag v0.2.0 ===
git tag -a v0.2.0 -m "Release v0.2.0"

echo.
echo === [6/6] Push branch + tag ===
git push origin main
git push origin v0.2.0

echo.
echo ============================================================
echo  Done. GitHub Actions will start the build.
echo  Progress: https://github.com/maroofloor/mdtracker/actions
echo  Releases: https://github.com/maroofloor/mdtracker/releases
echo ============================================================
pause
