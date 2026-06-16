"""일시적 알림 토스트 — 부모 위젯 위에 잠깐 떠서 페이드 인/아웃 후 사라진다.

마우스 이벤트를 통과시켜 아래 위젯 조작을 막지 않는다.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve, QPropertyAnimation, Qt, QTimer,
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget,
)


class Toast(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 8)
        self._lbl = QLabel("", self)
        lay.addWidget(self._lbl)

        self._eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._eff)
        self._fade = QPropertyAnimation(self._eff, b"opacity", self)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self.hide()

    def show_message(self, text: str, color: str = "#22c55e",
                     fg: str = "#052e16", ms: int = 2200) -> None:
        self._lbl.setText(text)
        self.setStyleSheet(f"background: {color}; border-radius: 9px;")
        self._lbl.setStyleSheet(
            f"color: {fg}; font-size: 12px; font-weight: 800;"
            "background: transparent; border: none;")
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        try:
            self._fade.finished.disconnect()
        except (RuntimeError, TypeError):
            pass
        self._fade.stop()
        self._fade.setDuration(170)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()
        self._timer.start(ms)

    def _fade_out(self) -> None:
        try:
            self._fade.finished.disconnect()
        except (RuntimeError, TypeError):
            pass
        self._fade.stop()
        self._fade.setDuration(320)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self.hide)
        self._fade.start()

    def _reposition(self) -> None:
        p = self.parent()
        if isinstance(p, QWidget):
            self.move((p.width() - self.width()) // 2,
                      p.height() - self.height() - 26)

    def shutdown(self) -> None:
        self._timer.stop()
        self._fade.stop()
