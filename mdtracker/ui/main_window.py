"""메인 윈도우 — 좌측 사이드바 네비게이션 (기록 / 대시보드 / 덱관리 / 설정)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, overload, runtime_checkable

from PySide6.QtCore import QRectF, QSize, QSettings, Qt
from PySide6.QtGui import QFont, QIcon, QPainterPath, QRegion
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QSizeGrip,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

_ICON_PATH = Path(__file__).parent.parent.parent / "assets" / "icon.png"

from ..styles.theme import set_ui_scale
from .dashboard_view import DashboardView
from .deck_view import DeckView
from .record_view import RecordView
from .settings_view import SettingsView
from .sidebar import Sidebar
from .title_bar import TitleBar

_CORNER_RADIUS = 10
_ASPECT_WIDTH = 3
_ASPECT_HEIGHT = 2


@runtime_checkable
class _Refreshable(Protocol):
    def refresh(self) -> None: ...


def _setting_float(settings: QSettings, key: str, default: float) -> float:
    raw = settings.value(key, default)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return default
    if isinstance(raw, (int, float)):
        return float(raw)
    return default


def _setting_int(settings: QSettings, key: str, default: int) -> int:
    raw = settings.value(key, default)
    if isinstance(raw, str):
        try:
            return int(raw)
        except ValueError:
            return default
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)
    return default


class MainWindow(QMainWindow):
    def __init__(self, db) -> None:
        super().__init__()
        self.db = db
        self.setWindowTitle("Master Duel 승률 트래커")
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        if _ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(_ICON_PATH)))
        self.setMinimumSize(900, 600)

        self._current_scale: float = 1.0
        self._aspect_resize_pending = False

        self.record_view    = RecordView(db)
        self.dashboard_view = DashboardView(db)
        self.deck_view      = DeckView(db)
        self.settings_view  = SettingsView()

        self.title_bar = TitleBar()
        self.sidebar   = Sidebar()
        self.stack     = QStackedWidget()
        self.stack.addWidget(self.record_view)     # 0
        self.stack.addWidget(self.dashboard_view)  # 1
        self.stack.addWidget(self.deck_view)        # 2
        self.stack.addWidget(self.settings_view)    # 3

        self.sidebar.nav_changed.connect(self._on_nav_changed)
        self.record_view.data_changed.connect(self.dashboard_view.refresh)
        self.settings_view.size_changed.connect(self._resize_preserving_aspect)
        self.settings_view.scale_changed.connect(self._apply_ui_scale)

        # 콘텐츠 영역 (사이드바 + 스택)
        content = QWidget()
        self.content_layout = QHBoxLayout(content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_layout.addWidget(self.sidebar)
        self.content_layout.addWidget(self.stack, 1)
        self.content_layout.addWidget(self.record_view.ocr_panel)

        # 루트: 타이틀바 (상단) + 콘텐츠 (하단)
        container = QWidget()
        container.setObjectName("mainContainer")
        container.setStyleSheet(
            f"#mainContainer {{ background-color: transparent; }}")
        self.root_layout = QVBoxLayout(container)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)
        self.root_layout.addWidget(self.title_bar)
        self.root_layout.addWidget(self.record_view.status_bar)
        self.root_layout.addWidget(content, 1)
        self.setCentralWidget(container)
        self.resize_grip = QSizeGrip(container)
        self.resize_grip.setFixedSize(18, 18)
        self.resize_grip.setStyleSheet("background: transparent;")
        self.resize_grip.raise_()

        self.stack.setCurrentIndex(0)
        self._load_settings()

    # ── 네비게이션 ───────────────────────────────────────────────────

    def _on_nav_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        widget = self.stack.currentWidget()
        if isinstance(widget, _Refreshable):
            widget.refresh()

    # ── 라운드 모서리 + 리사이즈 ────────────────────────────────────

    @overload
    def resize(self, width: QSize) -> None: ...

    @overload
    def resize(self, width: int, height: int) -> None: ...

    def resize(self, width: int | QSize, height: int | None = None) -> None:
        if isinstance(width, QSize):
            size = self._aspect_size(width.width(), width.height())
        elif height is not None:
            size = self._aspect_size(width, height)
        else:
            return
        super().resize(size)

    def resizeEvent(self, event) -> None:
        corrected = self._aspect_size(
            event.size().width(),
            event.size().height(),
            event.oldSize().width(),
            event.oldSize().height(),
        )
        if not self._aspect_resize_pending and corrected != event.size():
            self._aspect_resize_pending = True
            self.resize(corrected)
            self._aspect_resize_pending = False
            return

        super().resizeEvent(event)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), _CORNER_RADIUS, _CORNER_RADIUS)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))
        resize_grip = getattr(self, "resize_grip", None)
        if isinstance(resize_grip, QSizeGrip):
            resize_grip.move(
                self.width() - resize_grip.width() - 3,
                self.height() - resize_grip.height() - 3,
            )

    def _aspect_size(
        self,
        width: int,
        height: int,
        old_width: int = -1,
        old_height: int = -1,
    ) -> QSize:
        min_size = self.minimumSize()
        width = max(width, min_size.width())
        height = max(height, min_size.height())
        if width * _ASPECT_HEIGHT == height * _ASPECT_WIDTH:
            return QSize(width, height)

        width_changed = (
            old_width < 0
            or abs(width - old_width) >= abs(height - old_height)
        )
        if width_changed:
            height = max(min_size.height(), round(width * _ASPECT_HEIGHT / _ASPECT_WIDTH))
        else:
            height = max(height, min_size.height())
        if height % _ASPECT_HEIGHT:
            height += _ASPECT_HEIGHT - (height % _ASPECT_HEIGHT)
        width = height * _ASPECT_WIDTH // _ASPECT_HEIGHT
        return QSize(width, height)

    def _resize_preserving_aspect(self, width: int, height: int) -> None:
        self.resize(self._aspect_size(width, height))

    # ── UI 스케일 ────────────────────────────────────────────────────

    def _apply_ui_scale(self, scale: float) -> None:
        set_ui_scale(scale)
        self._current_scale = scale
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            return
        font = app.font()
        font.setPointSizeF(10.0 * scale)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        app.setFont(font)
        self.sidebar.apply_scale(scale)
        self.settings_view.set_current_scale(scale)
        self._save_settings()

    # ── QSettings 영속화 ─────────────────────────────────────────────

    def _load_settings(self) -> None:
        s = QSettings("MDTracker", "MDTracker")
        scale = _setting_float(s, "ui_scale", 1.0)
        w = _setting_int(s, "window_width", 1200)
        h = _setting_int(s, "window_height", 800)
        self.resize(w, h)
        self._apply_ui_scale(scale)

    def _save_settings(self) -> None:
        s = QSettings("MDTracker", "MDTracker")
        s.setValue("ui_scale",      self._current_scale)
        s.setValue("window_width",  self.width())
        s.setValue("window_height", self.height())

    # ── 종료 ─────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._save_settings()
        self.record_view.shutdown()
        super().closeEvent(event)
