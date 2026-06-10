"""커스텀 타이틀바 — 프레임리스 윈도우의 드래그 이동 + 창 컨트롤."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from ..styles.theme import ACCENT, BG, BORDER, TEXT, TEXT2

_ICON_PATH = Path(__file__).parent.parent.parent / "assets" / "icon.png"

_H = 38   # 타이틀바 높이 (px)

_BTN_BASE = (
    f"QPushButton {{ color: {TEXT2}; background: transparent; border: none;"
    f"font-size: 13px; min-width: 36px; min-height: {_H}px; }}"
    f"QPushButton:hover {{ background: rgba(255,255,255,0.08); color: {TEXT}; }}"
)
_BTN_CLOSE = (
    f"QPushButton {{ color: {TEXT2}; background: transparent; border: none;"
    f"font-size: 13px; min-width: 36px; min-height: {_H}px; }}"
    "QPushButton:hover { background: #ef4444; color: #fff; }"
)


class TitleBar(QWidget):
    """FramelessWindowHint 윈도우 전용 커스텀 타이틀바."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(_H)
        self.setStyleSheet(
            f"background-color: {BG}; border-bottom: 1px solid {BORDER};")
        self._drag_pos = None
        self._build()

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 4, 0)
        layout.setSpacing(6)

        # 앱 로고 + 제목
        icon_lbl = QLabel()
        icon_lbl.setStyleSheet("border: none;")
        if _ICON_PATH.exists():
            icon_lbl.setPixmap(
                QPixmap(str(_ICON_PATH)).scaled(
                    22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            try:
                import qtawesome as qta
                icon_lbl.setPixmap(qta.icon("fa5s.dragon", color=ACCENT).pixmap(18, 18))
            except Exception:
                icon_lbl.setText("◆")
        layout.addWidget(icon_lbl)

        title = QLabel("Master Duel 트래커")
        title.setStyleSheet(
            f"color: {TEXT}; font-size: 12px; font-weight: 600; border: none;")
        layout.addWidget(title)
        layout.addStretch()

        # 창 컨트롤
        self._btn_min   = QPushButton("─")
        self._btn_max   = QPushButton("□")
        self._btn_close = QPushButton("✕")
        for btn, style in [(self._btn_min, _BTN_BASE),
                           (self._btn_max, _BTN_BASE),
                           (self._btn_close, _BTN_CLOSE)]:
            btn.setStyleSheet(style)
            btn.setFocusPolicy(Qt.NoFocus)
            layout.addWidget(btn)

        self._btn_min.clicked.connect(lambda: self.window().showMinimized())
        self._btn_max.clicked.connect(self._toggle_max)
        self._btn_close.clicked.connect(lambda: self.window().close())

    def _toggle_max(self) -> None:
        win = self.window()
        if win.isMaximized():
            win.showNormal()
            self._btn_max.setText("□")
        else:
            win.showMaximized()
            self._btn_max.setText("❐")

    # ── 드래그 이동 ─────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint()
                - self.window().frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            if self.window().isMaximized():
                self.window().showNormal()
                self._btn_max.setText("□")
            self.window().move(
                event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._toggle_max()
        super().mouseDoubleClickEvent(event)
