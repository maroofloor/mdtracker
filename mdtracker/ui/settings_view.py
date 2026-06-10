"""설정 뷰 — 창 크기 프리셋, UI 스케일, 피드백 채널."""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..ocr.config import OcrConfig, default_config_path
from ..styles.theme import BORDER, TEXT, TEXT2


class FeedbackDialog(QDialog):
    """Google Form 피드백 팝업 다이얼로그."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("피드백 / 건의")
        self.resize(820, 680)
        self._vbox = QVBoxLayout(self)
        self._vbox.setContentsMargins(0, 0, 0, 0)

        cfg = OcrConfig.load_or_default(default_config_path())
        url = cfg.feedback_form_url.strip()

        if not url:
            self._show_error(
                "피드백 URL이 설정되지 않았습니다.\n"
                "ocr_config.json 의 feedback_form_url 을 입력해주세요."
            )
            return

        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self._web = QWebEngineView()
            self._web.load(QUrl(url))
            self._web.loadFinished.connect(self._on_load_finished)
            self._vbox.addWidget(self._web)
        except Exception:
            self._show_error("WebEngine 모듈을 불러올 수 없습니다.")

    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            if hasattr(self, "_web"):
                self._web.hide()
            self._show_error("연결할 수 없습니다. 인터넷 연결을 확인해주세요.")

    def _show_error(self, msg: str) -> None:
        lbl = QLabel(msg)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {TEXT2}; font-size: 13px; padding: 24px;")
        self._vbox.addWidget(lbl)

_SIZE_PRESETS = [
    ("900 × 600",   900, 600),
    ("1200 × 800",  1200, 800),
    ("1440 × 960",  1440, 960),
    ("1680 × 1120", 1680, 1120),
]

_SCALE_MIN = 50
_SCALE_MAX = 150
_SCALE_DEFAULT = 100
_SCALE_STEP = 10


class SettingsView(QWidget):
    size_changed  = Signal(int, int)  # width, height
    scale_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(24)

        title = QLabel("설정")
        title.setStyleSheet(
            f"color: {TEXT}; font-size: 18px; font-weight: 700;")
        root.addWidget(title)

        # ── 창 크기 프리셋 ──────────────────────────────────────────
        root.addWidget(self._section_label("창 크기 프리셋"))
        size_row = QHBoxLayout()
        size_row.setSpacing(8)
        for label, w, h in _SIZE_PRESETS:
            btn = QPushButton(label)
            btn.setMinimumWidth(110)
            btn.clicked.connect(lambda _, ww=w, hh=h: self.size_changed.emit(ww, hh))
            size_row.addWidget(btn)
        size_row.addStretch()
        root.addLayout(size_row)

        # ── UI 크기 ─────────────────────────────────────────────────
        root.addWidget(self._section_label("UI 크기"))
        scale_row = QHBoxLayout()
        scale_row.setSpacing(12)
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(_SCALE_MIN, _SCALE_MAX)
        self.scale_slider.setValue(_SCALE_DEFAULT)
        self.scale_slider.setTickInterval(_SCALE_STEP)
        self.scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.scale_value = QLabel("100%")
        self.scale_value.setMinimumWidth(44)
        self.scale_value.setStyleSheet(f"color: {TEXT}; font-weight: 700;")
        self.scale_step_check = QCheckBox("10% 단위")
        self.scale_step_check.setStyleSheet(f"color: {TEXT2};")
        scale_row.addWidget(QLabel("50%"))
        scale_row.addWidget(self.scale_slider, 1)
        scale_row.addWidget(QLabel("150%"))
        scale_row.addWidget(self.scale_value)
        scale_row.addWidget(self.scale_step_check)
        root.addLayout(scale_row)

        self.scale_slider.valueChanged.connect(self._on_scale_slider_changed)
        self.scale_step_check.toggled.connect(self._on_scale_step_toggled)

        # ── 피드백 / 건의 ────────────────────────────────────────────
        root.addWidget(self._section_label("피드백 / 건의"))
        feedback_row = QHBoxLayout()
        feedback_row.setSpacing(8)
        feedback_btn = QPushButton("피드백 보내기")
        feedback_btn.setFixedWidth(140)
        feedback_btn.clicked.connect(self._open_feedback)
        feedback_row.addWidget(feedback_btn)
        feedback_lbl = QLabel("버그 신고·기능 건의를 개발자에게 전달합니다.")
        feedback_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 11px;")
        feedback_row.addWidget(feedback_lbl)
        feedback_row.addStretch()
        root.addLayout(feedback_row)

        root.addStretch()

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {TEXT2}; font-size: 11px; font-weight: 600;"
            f"border-bottom: 1px solid {BORDER}; padding-bottom: 4px;")
        return lbl

    def set_current_scale(self, scale: float) -> None:
        value = self._clamp_percent(round(scale * 100))
        self.scale_slider.blockSignals(True)
        self.scale_slider.setValue(value)
        self.scale_slider.blockSignals(False)
        self._set_scale_value(value)

    def _on_scale_slider_changed(self, value: int) -> None:
        if self.scale_step_check.isChecked():
            value = self._snap_percent(value)
        self._set_scale_value(value)
        self.scale_changed.emit(value / 100)

    def _on_scale_step_toggled(self, checked: bool) -> None:
        if not checked:
            return
        value = self._snap_percent(self.scale_slider.value())
        self._set_scale_value(value)
        self.scale_changed.emit(value / 100)

    def _set_scale_value(self, value: int) -> None:
        self.scale_slider.blockSignals(True)
        self.scale_slider.setValue(value)
        self.scale_slider.blockSignals(False)
        self.scale_value.setText(f"{value}%")

    @staticmethod
    def _clamp_percent(value: int) -> int:
        return min(max(value, _SCALE_MIN), _SCALE_MAX)

    def _snap_percent(self, value: int) -> int:
        snapped = round(value / _SCALE_STEP) * _SCALE_STEP
        return self._clamp_percent(snapped)

    def _open_feedback(self) -> None:
        dlg = FeedbackDialog(self)
        dlg.exec()
