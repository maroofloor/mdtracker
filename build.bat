@echo off
REM ============================================================
REM  MDTracker 빌드 스크립트
REM  - exe 빌드(PyInstaller) -> 인스톨러 빌드(Inno Setup)
REM  사용법: 프로젝트 루트에서 build.bat 실행
REM ============================================================
setlocal
cd /d "%~dp0"

echo [1/3] PyInstaller exe 빌드...
if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)
"%PY%" -m PyInstaller --noconfirm MDTracker.spec
if errorlevel 1 (
    echo [오류] exe 빌드 실패. 중단합니다.
    exit /b 1
)
echo     -> dist\MDTracker\ 생성 완료

echo [2/3] 인스톨러 빌드(Inno Setup)...
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if defined ISCC (
    "%ISCC%" installer\MDTracker_Setup.iss
    if errorlevel 1 (
        echo [오류] 인스톨러 빌드 실패.
        exit /b 1
    )
    echo     -> installer\Output\ 생성 완료
) else (
    echo     -> Inno Setup 미설치: 인스톨러 단계 건너뜀
)

echo [3/3] Windows 아이콘 캐시 갱신...
ie4uinit.exe -show

echo.
echo 완료. exe: dist\MDTracker\MDTracker.exe
endlocal
