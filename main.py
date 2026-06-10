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

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
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

    app = QApplication(sys.argv)
    _icon_path = Path(__file__).parent / "assets" / "icon.png"
    if _icon_path.exists():
        app.setWindowIcon(QIcon(str(_icon_path)))
    from mdtracker.styles.theme import apply_theme
    apply_theme(app)
    win = MainWindow(db)
    win.show()

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
