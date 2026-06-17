"""앱 진입점 — PyQt 메인 윈도우 실행.

수동 입력 UI 단계. 통계·OCR 탭은 후속 단계에서 추가된다.
디스플레이가 없는 환경에서 구성만 검증하려면:
    QT_QPA_PLATFORM=offscreen .venv/bin/python main.py --check
"""

import sys
from pathlib import Path

# pandas → dateutil → six 임포트 체인이 PySide6 shiboken 훅과 충돌하므로
# PySide6 로드 전에 먼저 임포트해 sys.modules에 캐시해 둔다.
try:
    import pandas as _pd  # noqa: F401
    del _pd
except ImportError:
    pass

from PySide6.QtCore import Qt, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

if sys.platform == "win32":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "MDTracker.MDTracker.1"
    )


def _qt_msg_handler(msg_type: QtMsgType, _ctx, msg: str) -> None:
    # Qt QSS 파서 경고는 앱 동작에 무관하므로 억제
    if "Could not parse stylesheet" in msg:
        return
    if msg_type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg,
                    QtMsgType.QtFatalMsg):
        print(msg, file=sys.stderr)

from mdtracker.db import Database
from mdtracker.ui.main_window import MainWindow

DB_PATH = Path(__file__).parent / "data" / "mdtracker.db"


def main() -> None:
    qInstallMessageHandler(_qt_msg_handler)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = Database(DB_PATH)

    # 분수 배율(125%/150% 등)에서 Qt 기본 반올림이 레이아웃 어긋남·글자 잘림을
    # 유발할 수 있어 배율을 그대로 통과시킨다. QApplication 생성 전에 설정해야 한다.
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    # 작업표시줄은 작은 크기 아이콘을 요구하므로 다중 크기를 담은 .ico를 우선 사용한다.
    _assets = Path(__file__).parent / "assets"
    _icon_path = _assets / "icon.ico"
    if not _icon_path.exists():
        _icon_path = _assets / "icon.png"
    if _icon_path.exists():
        app.setWindowIcon(QIcon(str(_icon_path)))
    from mdtracker.styles.theme import apply_theme
    apply_theme(app)

    # 첫 실행: 테마 선택 온보딩 (저장된 테마가 없을 때만, --check 제외)
    if "--check" not in sys.argv:
        from PySide6.QtCore import QSettings
        _s = QSettings("MDTracker", "MDTracker")
        if not _s.contains("theme"):
            from mdtracker.ui.onboarding import OnboardingDialog
            OnboardingDialog(app).exec()
            if not _s.contains("theme"):
                _s.setValue("theme", "minimal")

    win = MainWindow(db)
    win.show()

    # 자동 업데이트 확인 (PyInstaller 빌드에서만 동작, 개발 환경에서는 무시)
    if "--no-update" not in sys.argv:
        from mdtracker.updater import check_update_async
        check_update_async(parent=win)

    # --check: 윈도우만 띄우고 즉시 종료 (헤드리스 구성 검증용)
    if "--check" in sys.argv:
        print("[mdtracker] 메인 윈도우 구성 성공")
        db.close()
        return

    exit_code = app.exec()
    db.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
