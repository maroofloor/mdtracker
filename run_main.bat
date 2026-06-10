@echo off
chcp 65001 > nul
set PYTHONUTF8=1
setlocal enabledelayedexpansion

:: --- Python 확인 ---
where python > nul 2>&1
if errorlevel 1 (
    echo [^!] Python이 설치되지 않았습니다.
    echo     Python 3.12 설치: https://www.python.org/downloads/release/python-3120/
    pause & exit /b 1
)

:: --- .venv 생성 (없으면) ---
if not exist ".venv\Scripts\python.exe" (
    echo [*] 가상 환경 생성 중...
    python -m venv .venv
    if errorlevel 1 ( echo [^!] 가상 환경 생성 실패. & pause & exit /b 1 )
    echo [+] .venv 생성 완료
)

:: --- 패키지 설치 (requirements.txt 변경 시에만) ---
set HASH_FILE=.venv\req_hash.txt
for /f "skip=1 delims=" %%H in ('certutil -hashfile requirements.txt SHA256 2^>nul') do (
    if not defined REQ_HASH set REQ_HASH=%%H
)
set NEEDS_INSTALL=1
if exist "%HASH_FILE%" (
    set /p SAVED_HASH=<"%HASH_FILE%"
    if "!REQ_HASH!"=="!SAVED_HASH!" set NEEDS_INSTALL=0
)
if "!NEEDS_INSTALL!"=="1" (
    echo [*] 패키지 설치 중...
    .venv\Scripts\pip install -r requirements.txt --quiet
    if errorlevel 1 ( echo [^!] 패키지 설치 실패. & pause & exit /b 1 )
    echo !REQ_HASH!> "%HASH_FILE%"
    echo [+] 패키지 설치 완료
) else (
    echo [*] 패키지 최신 상태 - 설치 생략
)

:: --- Tesseract 확인 (OCR 기능용) ---
set TESS_OK=0
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" set TESS_OK=1
if "!TESS_OK!"=="0" (
    where tesseract > nul 2>&1
    if not errorlevel 1 set TESS_OK=1
)
if "!TESS_OK!"=="0" (
    echo.
    echo [^!] Tesseract 미설치 -- OCR 자동 기록 기능을 사용할 수 없습니다.
    echo     설치: https://github.com/UB-Mannheim/tesseract/wiki
    echo     설치 시 "Additional language data" 에서 Korean 항목 체크 필수
    echo     설치 후 ocr_config.json 의 tesseract_cmd 경로를 확인하세요.
    echo.
)

:: --- 실행 ---
echo.
echo [*] MDTracker 시작 중...

:: 구성 검증 (실패 시 오류 표시 후 대기)
set QT_QPA_PLATFORM=offscreen
.venv\Scripts\python.exe main.py --check > "%TEMP%\mdtracker_check.log" 2>&1
if errorlevel 1 (
    echo [^!] 실행 실패 -- 오류 내용:
    type "%TEMP%\mdtracker_check.log"
    pause
    exit /b 1
)
set QT_QPA_PLATFORM=

:: 검증 통과 -- 콘솔 없는 pythonw로 GUI 실행, cmd창은 즉시 종료
start "" ".venv\Scripts\pythonw.exe" main.py
exit /b 0
