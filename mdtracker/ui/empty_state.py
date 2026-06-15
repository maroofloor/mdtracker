"""빈 상태 위젯 — 데이터가 없을 때 보여주는 안내(아이콘 + 제목 + 부제 + 선택 액션).

테마 토큰을 따르며 theme_notifier.changed 시 색을 갱신한다.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ..styles import theme


class EmptyState(QWidget):
    def __init__(self, icon: str = "🗂", title: str = "", subtitle: str = "",
                 action_text: Optional[str] = None,
                 on_action: Optional[Callable[[], None]] = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._btn: Optional[QPushButton] = None

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(10)
        lay.addStretch()

        self._icon = QLabel(icon)
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._icon)

        self._title = QLabel(title)
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._title)

        self._subtitle = QLabel(subtitle)
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setWordWrap(True)
        lay.addWidget(self._subtitle)

        if action_text:
            self._btn = QPushButton(action_text)
            if on_action is not None:
                self._btn.clicked.connect(lambda: on_action())
            lay.addWidget(self._btn, alignment=Qt.AlignmentFlag.AlignCenter)

        lay.addStretch()

        self._restyle()
        try:
            theme.theme_notifier.changed.connect(lambda *_: self._restyle())
        except Exception:
            pass

    def set_text(self, title: Optional[str] = None,
                 subtitle: Optional[str] = None,
                 icon: Optional[str] = None) -> None:
        if icon is not None:
            self._icon.setText(icon)
        if title is not None:
            self._title.setText(title)
        if subtitle is not None:
            self._subtitle.setText(subtitle)

    def _restyle(self) -> None:
        t = theme.active()
        self._icon.setStyleSheet(
            "font-size: 46px; border: none; background: transparent;")
        self._title.setStyleSheet(
            f"color: {t.text}; font-size: 16px; font-weight: 700;"
            "border: none; background: transparent;")
        self._subtitle.setStyleSheet(
            f"color: {t.text2}; font-size: 12px; border: none;"
            "background: transparent;")
        if self._btn is not None:
            self._btn.setStyleSheet(
                f"background: {t.accent}; color: #ffffff; border: none;"
                "border-radius: 6px; padding: 7px 18px; font-weight: 700;")
