from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

APP_DIR_NAME = "MDTracker"


def _environ(environ: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if environ is None else environ


def _windows_root(environ: Mapping[str, str] | None = None) -> Path:
    env = _environ(environ)
    local_appdata = env.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / APP_DIR_NAME
    user_profile = env.get("USERPROFILE")
    if user_profile:
        return Path(user_profile) / "AppData" / "Local" / APP_DIR_NAME
    return Path.home() / "AppData" / "Local" / APP_DIR_NAME


def default_db_path(
    *,
    platform: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    current_platform = sys.platform if platform is None else platform
    if current_platform == "win32":
        return _windows_root(environ) / "data" / "mdtracker.db"
    env = _environ(environ)
    base = Path(env.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_DIR_NAME / "mdtracker.db"


def default_ocr_config_path(
    *,
    platform: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    current_platform = sys.platform if platform is None else platform
    if current_platform == "win32":
        return _windows_root(environ) / "config" / "ocr_config.json"
    env = _environ(environ)
    base = Path(env.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_DIR_NAME / "ocr_config.json"


def application_root(
    *,
    frozen: bool | None = None,
    executable: str | Path | None = None,
) -> Path:
    current_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    if current_frozen:
        exe_path = Path(sys.executable if executable is None else executable)
        return exe_path.resolve().parent
    return Path(__file__).resolve().parents[1]


def runtime_asset_path(
    relative_path: str | Path,
    *,
    frozen: bool | None = None,
    executable: str | Path | None = None,
) -> Path:
    return application_root(frozen=frozen, executable=executable) / relative_path


# ── Tesseract 자동 탐색 ─────────────────────────────────────────────

_TESSERACT_WIN_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\{username}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
]

_TESSERACT_DOWNLOAD_URL = (
    "https://github.com/UB-Mannheim/tesseract/wiki"
)


def find_tesseract_exe() -> str | None:
    """Tesseract 실행 파일 경로를 자동으로 찾는다.

    탐색 순서:
    1. PyInstaller 번들 내 tesseract/tesseract.exe
    2. Windows 일반 설치 경로
    3. PATH (shutil.which)
    """
    import shutil

    # 1. PyInstaller 번들
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundled = Path(meipass) / "tesseract" / "tesseract.exe"
        if bundled.is_file():
            return str(bundled)

    # 2. Windows 표준 경로
    if sys.platform == "win32":
        for candidate in _TESSERACT_WIN_CANDIDATES:
            expanded = os.path.expandvars(candidate)
            if Path(expanded).is_file():
                return expanded

    # 3. PATH
    found = shutil.which("tesseract")
    return found or None
