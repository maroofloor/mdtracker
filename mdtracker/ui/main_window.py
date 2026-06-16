"""메인 윈도우 — 좌측 사이드바 네비게이션 (기록 / 대시보드 / 덱관리 / 설정)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from PySide6.QtCore import (
    QEasingCurve, QPropertyAnimation, QRectF, QSize, QSettings, Qt, QTimer,
)
from PySide6.QtGui import QFont, QIcon, QPainterPath, QRegion
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QMainWindow,
    QSizeGrip,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

_ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"
# 작업표시줄용 작은 크기를 담은 .ico 우선, 없으면 png 폴백
_ICON_PATH = _ASSETS_DIR / "icon.ico"
if not _ICON_PATH.exists():
    _ICON_PATH = _ASSETS_DIR / "icon.png"

from ..styles.theme import set_ui_scale
from .dashboard_view import DashboardView
from .deck_view import DeckView
from .record_view import RecordView
from .settings_view import SettingsView
from .sidebar import Sidebar
from .title_bar import TitleBar

_CORNER_RADIUS = 10


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
        self.settings_view.size_changed.connect(lambda w, h: self.resize(w, h))
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

        # 앱 시작 3초 후 백그라운드 업데이트 확인 (네트워크 오류 시 조용히 무시)
        QTimer.singleShot(3000, self._bg_update_check)

    def _bg_update_check(self) -> None:
        try:
            from ..updater import check_update_async
            check_update_async(parent=self)
        except Exception:
            pass

    # ── 네비게이션 ───────────────────────────────────────────────────

    def _on_nav_changed(self, index: int) -> None:
        prev = self.stack.currentIndex()
        # 기록(0) ↔ 대시보드(1) 탭 전환 시 필터바 상태 동기화
        if prev != index:
            try:
                if prev == 0 and index == 1:
                    state = self.record_view.filter_bar.get_state()
                    self.dashboard_view.filter_bar.apply_state(state)
                elif prev == 1 and index == 0:
                    state = self.dashboard_view.filter_bar.get_state()
                    self.record_view.filter_bar.apply_state(state)
            except Exception:
                pass
        self.stack.setCurrentIndex(index)
        widget = self.stack.currentWidget()
        self._fade_in(widget)
        if isinstance(widget, _Refreshable):
            widget.refresh()

    def _fade_in(self, widget) -> None:
        """탭 전환 시 가벼운 페이드 인 (완료 후 효과 제거)."""
        try:
            eff = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(eff)
            anim = QPropertyAnimation(eff, b"opacity", self)
            anim.setDuration(200)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.finished.connect(lambda: widget.setGraphicsEffect(None))
            anim.start()
            self._nav_anim = anim
        except Exception:
            pass

    # ── 라운드 모서리 + 리사이즈 ────────────────────────────────────

    def resizeEvent(self, event) -> None:
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

    # ── 종료 ─────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._save_settings()
        self.record_view.shutdown()
        super().closeEvent(event)
