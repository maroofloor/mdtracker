"""좌측 접을 수 있는 사이드바 네비게이션."""

from __future__ import annotations

from importlib import import_module
from typing import Final, Protocol, runtime_checkable

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Signal,
)
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from mdtracker.styles.theme import ACCENT, BG, BORDER, PANEL, TEXT, TEXT2

_NAV_ITEMS: Final = [
    (0, "fa5s.list",        "기록"),
    (1, "fa5s.chart-bar",   "대시보드"),
    (2, "fa5s.layer-group", "덱관리"),
]

_BTN_BASE = f"""
    QPushButton {{
        background-color: transparent;
        color: {TEXT};
        border: none;
        text-align: left;
        padding: 0 12px;
        font-size: 13px;
    }}
    QPushButton:hover {{ background-color: {PANEL}; }}
"""

_BTN_ACTIVE = f"""
    QPushButton {{
        background-color: {PANEL};
        color: {TEXT};
        border: none;
        border-left: 3px solid {ACCENT};
        text-align: left;
        padding: 0 12px;
        font-size: 13px;
        font-weight: bold;
    }}
"""

_TOGGLE_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {TEXT2};
        border: none;
        border-bottom: 1px solid {BORDER};
        text-align: center;
        padding: 0;
    }}
    QPushButton:hover {{ background-color: {PANEL}; }}
"""


@runtime_checkable
class _IconProvider(Protocol):
    def icon(self, name: str, *, color: str) -> QIcon: ...


def _load_icon_provider() -> _IconProvider:
    provider = import_module("qtawesome")
    if isinstance(provider, _IconProvider):
        return provider
    raise ImportError("qtawesome.icon is required")


_QTA: Final = _load_icon_provider()


class Sidebar(QWidget):
    """접기/펼치기 가능한 좌측 네비게이션 바."""

    nav_changed: Signal = Signal(int)  # 0=기록, 1=대시보드, 2=덱관리, 3=설정

    EXPANDED_W: Final = 180
    COLLAPSED_W: Final = 48
    ANIMATION_MS: Final = 180

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._expanded_width: int = self.EXPANDED_W
        self._collapsed_width: int = self.COLLAPSED_W
        self.setFixedWidth(self._expanded_width)
        self.setStyleSheet(f"background-color: {BG}; border-right: 1px solid {BORDER};")
        self._collapsed: bool = False
        self._current: int = 0
        self._nav_btns: list[QPushButton] = []
        self._nav_indices: dict[QPushButton, int] = {}
        self._nav_labels: dict[QPushButton, str] = {}
        self._width_animation: QParallelAnimationGroup | None = None
        self._target_width: int = self._expanded_width
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._toggle_btn: QPushButton = QPushButton(_QTA.icon("fa5s.bars", color=TEXT2), "")
        self._toggle_btn.setFixedHeight(48)
        self._toggle_btn.setStyleSheet(_TOGGLE_STYLE)
        _ = self._toggle_btn.clicked.connect(self.toggle_collapse)
        layout.addWidget(self._toggle_btn)

        for idx, icon_name, label in _NAV_ITEMS:
            btn = QPushButton(_QTA.icon(icon_name, color=TEXT), f"  {label}")
            btn.setFixedHeight(48)
            self._nav_indices[btn] = idx
            self._nav_labels[btn] = f"  {label}"
            _ = btn.clicked.connect(lambda _checked=False, i=idx: self.select(i))
            layout.addWidget(btn)
            self._nav_btns.append(btn)

        layout.addStretch()

        # 설정 버튼 — 하단 고정
        settings_btn = QPushButton(_QTA.icon("fa5s.cog", color=TEXT), "  설정")
        settings_btn.setFixedHeight(48)
        self._nav_indices[settings_btn] = 3
        self._nav_labels[settings_btn] = "  설정"
        _ = settings_btn.clicked.connect(lambda: self.select(3))
        layout.addWidget(settings_btn)
        self._nav_btns.append(settings_btn)

        self._highlight(0)

    def select(self, index: int) -> None:
        """지정 인덱스 항목을 활성화하고 nav_changed 시그널 발행."""
        self._current = index
        self._highlight(index)
        self.nav_changed.emit(index)

    def _highlight(self, index: int) -> None:
        for btn in self._nav_btns:
            active = self._nav_indices[btn] == index
            btn.setStyleSheet(_BTN_ACTIVE if active else _BTN_BASE)

    def toggle_collapse(self) -> None:
        """사이드바 접기/펼치기 전환."""
        self._collapsed = not self._collapsed
        width = self._collapsed_width if self._collapsed else self._expanded_width
        if not self._collapsed:
            self._set_nav_labels_visible(True)
        self._animate_width(width)

    def _animate_width(self, target_width: int) -> None:
        current_width = self.maximumWidth()
        if self._width_animation is not None:
            self._width_animation.stop()

        self._target_width = target_width
        group = QParallelAnimationGroup(self)
        for property_name in (b"minimumWidth", b"maximumWidth"):
            animation = QPropertyAnimation(self, property_name, group)
            animation.setDuration(self.ANIMATION_MS)
            animation.setStartValue(current_width)
            animation.setEndValue(target_width)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            group.addAnimation(animation)

        _ = group.finished.connect(
            lambda target=target_width: self._finish_width_animation(target)
        )
        self._width_animation = group
        group.start(QAbstractAnimation.DeletionPolicy.KeepWhenStopped)

    def _finish_width_animation(self, target_width: int) -> None:
        if target_width != self._target_width:
            return
        self.setFixedWidth(target_width)
        self._set_nav_labels_visible(not self._collapsed)

    def _set_nav_labels_visible(self, visible: bool) -> None:
        for btn in self._nav_btns:
            btn.setText(self._nav_labels[btn] if visible else "")

    def apply_scale(self, scale: float) -> None:
        """스케일에 따라 너비·버튼 높이 재조정."""
        self._expanded_width = max(140, round(180 * scale))
        self._collapsed_width = max(40, round(48 * scale))
        if self._width_animation is not None:
            self._width_animation.stop()
        self.setFixedWidth(
            self._collapsed_width if self._collapsed else self._expanded_width
        )
        self._target_width = self.width()
        self._set_nav_labels_visible(not self._collapsed)
        btn_h = max(36, round(48 * scale))
        self._toggle_btn.setFixedHeight(btn_h)
        for btn in self._nav_btns:
            btn.setFixedHeight(btn_h)

    @property
    def collapsed(self) -> bool:
        return self._collapsed
