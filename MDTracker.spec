# -*- mode: python ; coding: utf-8 -*-
"""
MDTracker PyInstaller 스펙 파일
빌드 명령: pyinstaller MDTracker.spec
출력 경로: dist/MDTracker/
"""

import sys
from pathlib import Path

block_cipher = None

# Tesseract 번들 경로 (빌드 머신에 tesseract/ 폴더가 있을 때만 포함)
TESSERACT_BUNDLE = Path("tesseract")
tess_datas = []
if TESSERACT_BUNDLE.exists():
    tess_datas = [(str(TESSERACT_BUNDLE), "tesseract")]

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # 앱 리소스
        ("assets",                      "assets"),
        ("mdtracker/ocr/templates",     "mdtracker/ocr/templates"),
        ("mdtracker/styles",            "mdtracker/styles"),
        # 설정 예시 (실제 ocr_config.json은 인스톨러가 AppData에 복사)
        ("ocr_config.example.json",     "."),
        # Tesseract 바이너리 (존재할 때만)
        *tess_datas,
    ],
    hiddenimports=[
        # PySide6
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
        # pyqtgraph
        "pyqtgraph",
        "pyqtgraph.graphicsItems",
        "pyqtgraph.widgets",
        # mss
        "mss",
        "mss.windows",
        # pytesseract
        "pytesseract",
        # 기타
        "PIL._tkinter_finder",
        "win32api",
        "win32con",
        "win32gui",
        "pywintypes",
        # openpyxl
        "openpyxl",
        "openpyxl.styles",
        "openpyxl.utils",
        # qtawesome
        "qtawesome",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 표준 라이브러리는 상호 의존이 많아 함부로 제외하면 런타임 크래시가 난다.
    # (urllib/http/email → updater.py·pathlib, difflib → 덱 퍼지매칭 등)
    # tkinter만 안전하게 제외한다.
    excludes=[
        "tkinter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MDTracker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # GUI 앱 — 콘솔 창 없음
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",  # 다중 크기 .ico (작업표시줄/탐색기 아이콘)
    version="version_info.txt",  # 파일 존재 시 버전 리소스 삽입
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MDTracker",
)
