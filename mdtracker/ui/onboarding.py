"""첫 실행 온보딩 — 3개 테마를 미리보기로 보여주고 선택하게 한다.

선택 시 theme.set_theme()으로 적용·영속화한다(이후 실행에선 뜨지 않음).
각 카드는 해당 테마의 토큰으로 직접 칠해 실제 색을 미리 보여준다.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ..styles import theme


class _ThemeCard(QFrame):
    clicked = Signal()

    def __init__(self, th, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(196, 168)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"QFrame {{ background: {th.bg}; border: 2px solid {th.border};"
            "border-radius: 12px; }}")

        v = QVBoxLayout(self)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)

        name = QLabel(th.name)
        name.setStyleSheet(
            f"color: {th.text}; font-size: 15px; font-weight: 800;"
            "border: none; background: transparent;")
        v.addWidget(name)

        desc = QLabel(th.description)
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color: {th.text2}; font-size: 11px; border: none;"
            "background: transparent;")
        v.addWidget(desc)

        v.addStretch()

        swatches = QHBoxLayout()
        swatches.setSpacing(6)
        for color in (th.accent, th.win, th.lose, th.second):
            chip = QLabel()
            chip.setFixedSize(26, 26)
            chip.setStyleSheet(
                f"background: {color}; border-radius: 7px; border: none;")
            swatches.addWidget(chip)
        swatches.addStretch()
        v.addLayout(swatches)

    def mousePressEvent(self, _event) -> None:
        self.clicked.emit()


class OnboardingDialog(QDialog):
    """3개 테마 미리보기 선택 다이얼로그."""

    def __init__(self, app, parent=None) -> None:
        super().__init__(parent)
        self._app = app
        self.chosen: str | None = None
        self.setWindowTitle("MDTracker 시작하기")
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(6)

        title = QLabel("테마를 선택하세요")
        title.setStyleSheet("font-size: 18px; font-weight: 800; border: none;")
        root.addWidget(title)

        sub = QLabel("나중에 설정에서 언제든 바꿀 수 있어요.")
        sub.setStyleSheet("font-size: 12px; color: #94a3b8; border: none;")
        root.addWidget(sub)
        root.addSpacing(8)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        for th in theme.available_themes():
            card = _ThemeCard(th)
            card.clicked.connect(lambda _=False, tid=th.id: self._choose(tid))
            cards.addWidget(card)
        root.addLayout(cards)

        root.addSpacing(10)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        skip = QPushButton("기본값으로 시작")
        skip.clicked.connect(lambda: self._choose(theme.DEFAULT_THEME))
        btn_row.addWidget(skip)
        root.addLayout(btn_row)

    def _choose(self, theme_id: str) -> None:
        self.chosen = theme_id
        try:
            theme.set_theme(self._app, theme_id)
        except Exception:
            pass
        self.accept()
