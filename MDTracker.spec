# -*- mode: python ; coding: utf-8 -*-
"""
MDTracker PyInstaller 스펙 파일
빌드: pyinstaller MDTracker.spec
출력: dist/MDTracker/
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
    excludes=[
        "tkinter",
        "unittest",
        "xmlrpc",
        "email",
        "html",
        "http",
        "urllib",   # updater.py가 직접 import하므로 제외하지 않음 — 아래 주석 참고
        "pydoc",
        "doctest",
        "difflib",
        "calendar",
        "ftplib",
        "imaplib",
        "smtplib",
        "poplib",
        "telnetlib",
        "socketserver",
        "xmlrpc.server",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# urllib은 자동 업데이터에서 사용 — excludes에서 복원
if "urllib" in a.excludes:
    a.excludes.remove("urllib")

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
    icon="assets/icon.png",  # .ico 변환 후 교체 권장
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
