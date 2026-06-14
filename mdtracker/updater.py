"""
자동 업데이트 모듈

GitHub Releases API를 통해 새 버전을 확인하고,
사용자에게 다운로드/설치를 안내한다.

사용 예시 (main.py에서):
    from mdtracker.updater import check_update_async
    check_update_async(parent_widget=win)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QMessageBox, QProgressDialog, QWidget

from mdtracker import __version__

# ── 설정 ──────────────────────────────────────────────────────────────────────
# GitHub 저장소 정보
GITHUB_OWNER = "maroofloor"
GITHUB_REPO  = "mdtracker"
API_URL      = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# 업데이트 확인을 건너뛸 환경 (개발 중 실행 등)
_SKIP_UPDATE = getattr(sys, "frozen", False) is False  # PyInstaller 빌드가 아닐 때 건너뜀


# ── 버전 비교 ─────────────────────────────────────────────────────────────────
def _parse_version(v: str) -> tuple[int, ...]:
    """'v1.2.3' 또는 '1.2.3' → (1, 2, 3)"""
    v = v.lstrip("vV")
    parts = re.split(r"[.\-]", v)
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            break
    return tuple(result)


def _is_newer(remote: str, local: str) -> bool:
    return _parse_version(remote) > _parse_version(local)


# ── GitHub API 조회 ───────────────────────────────────────────────────────────
def _fetch_latest_release(timeout: int = 8) -> Optional[dict]:
    """최신 릴리스 정보를 반환. 실패 시 None."""
    req = urllib.request.Request(
        API_URL,
        headers={"User-Agent": f"MDTracker/{__version__}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return None


def _find_installer_asset(assets: list[dict]) -> Optional[dict]:
    """릴리스 에셋 중 Windows 인스톨러(.exe) 를 찾아 반환."""
    for asset in assets:
        name: str = asset.get("name", "")
        if name.endswith(".exe") and "setup" in name.lower():
            return asset
    # fallback: 아무 .exe
    for asset in assets:
        if asset.get("name", "").endswith(".exe"):
            return asset
    return None


# ── 다운로드 스레드 ───────────────────────────────────────────────────────────
class _DownloadThread(QThread):
    progress = Signal(int)   # 0-100
    finished = Signal(str)   # 저장 경로
    failed   = Signal(str)   # 오류 메시지

    def __init__(self, url: str, dest: Path):
        super().__init__()
        self._url  = url
        self._dest = dest

    def run(self) -> None:
        try:
            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": f"MDTracker/{__version__}"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk = 8192
                with open(self._dest, "wb") as f:
                    while True:
                        data = resp.read(chunk)
                        if not data:
                            break
                        f.write(data)
                        downloaded += len(data)
                        if total:
                            self.progress.emit(int(downloaded * 100 / total))
            self.finished.emit(str(self._dest))
        except Exception as e:
            self.failed.emit(str(e))


# ── UI 헬퍼 ──────────────────────────────────────────────────────────────────
def _show_update_dialog(parent: Optional[QWidget], tag: str, body: str) -> bool:
    """새 버전 알림 다이얼로그. '지금 업데이트' → True, '나중에' → False."""
    msg = QMessageBox(parent)
    msg.setWindowTitle("업데이트 알림")
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setText(f"<b>새 버전 {tag}</b> 이(가) 출시되었습니다.<br>현재 버전: {__version__}")
    if body:
        short_body = body[:400] + ("…" if len(body) > 400 else "")
        msg.setInformativeText(short_body)
    msg.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    msg.setDefaultButton(QMessageBox.StandardButton.Yes)
    msg.button(QMessageBox.StandardButton.Yes).setText("지금 업데이트")
    msg.button(QMessageBox.StandardButton.No).setText("나중에")
    return msg.exec() == QMessageBox.StandardButton.Yes


def _download_and_install(
    parent: Optional[QWidget],
    asset: dict,
    tag: str,
) -> None:
    """인스톨러를 임시 폴더에 다운로드 후 실행."""
    url  = asset["browser_download_url"]
    name = asset["name"]
    dest = Path(tempfile.gettempdir()) / name

    # 진행 다이얼로그
    progress = QProgressDialog(
        f"MDTracker {tag} 다운로드 중…", "취소", 0, 100, parent
    )
    progress.setWindowTitle("업데이트 다운로드")
    progress.setMinimumDuration(0)
    progress.setValue(0)

    thread = _DownloadThread(url, dest)
    thread.progress.connect(progress.setValue)

    def on_finished(path: str) -> None:
        progress.close()
        reply = QMessageBox.question(
            parent,
            "다운로드 완료",
            f"인스톨러를 실행하여 업데이트를 완료하시겠습니까?\n({path})",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # 인스톨러 실행 후 앱 종료
            subprocess.Popen([path], shell=True)  # noqa: S603
            sys.exit(0)

    def on_failed(err: str) -> None:
        progress.close()
        QMessageBox.warning(
            parent,
            "다운로드 실패",
            f"업데이트 파일을 내려받지 못했습니다.\n오류: {err}\n\n"
            f"수동으로 다운로드: https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases",
        )

    def on_cancel() -> None:
        thread.terminate()

    thread.finished.connect(on_finished)
    thread.failed.connect(on_failed)
    progress.canceled.connect(on_cancel)
    thread.start()
    progress.exec()


# ── 공개 API ─────────────────────────────────────────────────────────────────
class _CheckThread(QThread):
    """백그라운드에서 업데이트 확인 후 필요 시 UI를 띄운다."""
    update_available = Signal(dict)   # release dict

    def run(self) -> None:
        release = _fetch_latest_release()
        if not release:
            return
        tag = release.get("tag_name", "")
        if tag and _is_newer(tag, __version__):
            self.update_available.emit(release)


def check_update_async(parent: Optional[QWidget] = None) -> None:
    """
    앱 시작 직후 비동기로 업데이트를 확인한다.
    네트워크 오류 시 조용히 무시.
    PyInstaller 빌드가 아닌 경우(개발 환경) 건너뛴다.
    """
    if _SKIP_UPDATE:
        return

    thread = _CheckThread()
    thread.setParent(parent)  # 부모 위젯이 살아있는 동안 스레드 유지

    def _on_update(release: dict) -> None:
        tag    = release.get("tag_name", "")
        body   = release.get("body", "")
        assets = release.get("assets", [])
        if not _show_update_dialog(parent, tag, body):
            return
        asset = _find_installer_asset(assets)
        if asset:
            _download_and_install(parent, asset, tag)
        else:
            QMessageBox.information(
                parent,
                "업데이트",
                f"인스톨러 파일을 찾지 못했습니다.\n"
                f"수동 다운로드: https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/tag/{tag}",
            )

    thread.update_available.connect(_on_update)
    thread.start()

    # 가비지 컬렉션 방지 — 부모 없을 때 모듈 변수로 보관
    _CheckThread._instance = thread  # type: ignore[attr-defined]
