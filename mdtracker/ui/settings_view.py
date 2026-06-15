"""설정 뷰 — 창 크기 프리셋, UI 스케일, OCR 설정, 피드백 채널."""

from __future__ import annotations

import shutil
import webbrowser

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..ocr.config import OcrConfig, default_config_path
from ..styles.theme import (
    BORDER, TEXT, TEXT2,
    available_themes, get_active_theme, set_theme,
)


def _open_feedback_url(parent=None) -> None:
    """피드백 URL을 브라우저로 열거나, URL이 없으면 안내 메시지를 표시한다."""
    cfg = OcrConfig.load_or_default(default_config_path())
    url = cfg.feedback_form_url.strip()

    if not url:
        QMessageBox.information(
            parent, "피드백",
            "현재 피드백 폼이 준비 중입니다.\n"
            "GitHub Issues 페이지에서 버그 신고 및 기능 건의를 해주세요:\n"
            "https://github.com/maroofloor/mdtracker/issues"
        )
        return

    # WebEngine 시도 → 실패 시 기본 브라우저 폴백
    try:
        from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
        dlg = _FeedbackDialog(parent, url)
        dlg.exec()
    except Exception:
        webbrowser.open(url)


class _FeedbackDialog(QDialog):
    """Google Form 피드백 팝업 다이얼로그 (WebEngine 사용 가능 시)."""

    def __init__(self, parent=None, url: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("피드백 / 건의")
        self.resize(820, 680)
        self._vbox = QVBoxLayout(self)
        self._vbox.setContentsMargins(0, 0, 0, 0)
        self._url = url

        from PySide6.QtWebEngineWidgets import QWebEngineView
        self._web = QWebEngineView()
        self._web.load(QUrl(url))
        self._web.loadFinished.connect(self._on_load_finished)
        self._vbox.addWidget(self._web)

    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            if hasattr(self, "_web"):
                self._web.hide()
            lbl = QLabel("연결할 수 없습니다. 인터넷 연결을 확인하거나\n"
                         "브라우저에서 직접 열어주세요.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {TEXT2}; font-size: 13px; padding: 24px;")
            self._vbox.addWidget(lbl)
            open_btn = QPushButton("브라우저에서 열기")
            open_btn.clicked.connect(lambda: webbrowser.open(self._url))
            self._vbox.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignCenter)


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

        # ── 테마 ────────────────────────────────────────────────────
        root.addWidget(self._section_label("테마"))
        self._build_theme_section(root)

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

        # ── OCR 설정 ────────────────────────────────────────────────
        root.addWidget(self._section_label("OCR 설정"))

        # Tesseract 경로
        tess_row = QHBoxLayout()
        tess_row.setSpacing(6)
        tess_lbl = QLabel("Tesseract 경로")
        tess_lbl.setFixedWidth(100)
        tess_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        self.tess_path_edit = QLineEdit()
        self.tess_path_edit.setPlaceholderText("비어 있으면 PATH에서 자동 탐색")
        self.tess_path_edit.setStyleSheet(
            f"background: #0f172a; color: {TEXT}; border: 1px solid {BORDER};"
            "border-radius: 4px; padding: 3px 8px;")
        tess_browse_btn = QPushButton("찾아보기")
        tess_browse_btn.setFixedWidth(72)
        tess_browse_btn.clicked.connect(self._browse_tesseract)
        tess_test_btn = QPushButton("연결 테스트")
        tess_test_btn.setFixedWidth(84)
        tess_test_btn.clicked.connect(self._test_tesseract)
        tess_row.addWidget(tess_lbl)
        tess_row.addWidget(self.tess_path_edit, 1)
        tess_row.addWidget(tess_browse_btn)
        tess_row.addWidget(tess_test_btn)
        root.addLayout(tess_row)

        # 캡처 모니터
        mon_row = QHBoxLayout()
        mon_row.setSpacing(6)
        mon_lbl = QLabel("캡처 모니터")
        mon_lbl.setFixedWidth(100)
        mon_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        from PySide6.QtWidgets import QComboBox
        self.monitor_combo = QComboBox()
        self.monitor_combo.setFixedWidth(160)
        self._populate_monitors()
        self.monitor_combo.currentIndexChanged.connect(self._on_monitor_changed)
        mon_row.addWidget(mon_lbl)
        mon_row.addWidget(self.monitor_combo)
        mon_row.addStretch()
        root.addLayout(mon_row)

        # 설정 로드
        self._load_ocr_settings()

        # ── 버전 정보 ──────────────────────────────────────────────
        root.addWidget(self._section_label("버전 정보"))
        ver_row = QHBoxLayout()
        ver_row.setSpacing(10)
        from mdtracker import __version__
        ver_lbl = QLabel(f"현재 버전: <b>v{__version__}</b>")
        ver_lbl.setTextFormat(Qt.TextFormat.RichText)
        ver_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        self._update_status_lbl = QLabel("")
        self._update_status_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 11px;")
        check_btn = QPushButton("업데이트 확인")
        check_btn.setFixedWidth(110)
        check_btn.clicked.connect(self._check_update_manual)
        ver_row.addWidget(ver_lbl)
        ver_row.addWidget(self._update_status_lbl, 1)
        ver_row.addWidget(check_btn)
        root.addLayout(ver_row)

        # ── 데이터 관리 (백업 / 복원) ────────────────────────────
        root.addWidget(self._section_label("데이터 관리"))
        backup_row = QHBoxLayout()
        backup_row.setSpacing(8)
        backup_btn = QPushButton("데이터 백업")
        backup_btn.setFixedWidth(110)
        backup_btn.clicked.connect(self._backup_db)
        restore_btn = QPushButton("데이터 복원")
        restore_btn.setFixedWidth(110)
        restore_btn.clicked.connect(self._restore_db)
        backup_lbl = QLabel("DB 파일을 복사하여 백업·복원합니다. 복원 후 앱을 재시작하세요.")
        backup_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 11px;")
        backup_row.addWidget(backup_btn)
        backup_row.addWidget(restore_btn)
        backup_row.addWidget(backup_lbl)
        backup_row.addStretch()
        root.addLayout(backup_row)

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

    # ── 테마 선택 ────────────────────────────────────────────────────

    def _build_theme_section(self, root) -> None:
        row = QHBoxLayout()
        row.setSpacing(8)
        self._theme_group = QButtonGroup(self)
        self._theme_group.setExclusive(True)
        self._theme_buttons: dict[str, QPushButton] = {}
        active_id = get_active_theme().id
        for t in available_themes():
            btn = QPushButton(t.name)
            btn.setCheckable(True)
            btn.setMinimumWidth(120)
            btn.setToolTip(t.description)
            btn.setChecked(t.id == active_id)
            btn.clicked.connect(
                lambda _checked=False, tid=t.id: self._on_theme_selected(tid))
            self._theme_group.addButton(btn)
            self._theme_buttons[t.id] = btn
            row.addWidget(btn)
        row.addStretch()
        root.addLayout(row)

        hint = QLabel(
            "선택 즉시 적용됩니다. 일부 화면(기록 표 등)은 앱을 재시작하면 "
            "완전히 반영됩니다.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {TEXT2}; font-size: 11px;")
        root.addWidget(hint)

    def _on_theme_selected(self, theme_id: str) -> None:
        set_theme(QApplication.instance(), theme_id)
        # 활성 테마 기준으로 체크 상태 재동기화
        current = get_active_theme().id
        for tid, btn in getattr(self, "_theme_buttons", {}).items():
            btn.setChecked(tid == current)

    # ── OCR 설정 헬퍼 ────────────────────────────────────────────────

    def _populate_monitors(self) -> None:
        self.monitor_combo.blockSignals(True)
        self.monitor_combo.clear()
        try:
            import mss
            with mss.mss() as sct:
                for i, mon in enumerate(sct.monitors[1:], start=1):
                    self.monitor_combo.addItem(
                        f"모니터 {i}  ({mon['width']}×{mon['height']})", userData=i)
        except Exception:
            self.monitor_combo.addItem("모니터 1", userData=1)
        self.monitor_combo.blockSignals(False)

    def _load_ocr_settings(self) -> None:
        cfg = OcrConfig.load_or_default(default_config_path())
        self.tess_path_edit.setText(cfg.tesseract_cmd or "")
        # 모니터 콤보박스에서 저장된 index 선택
        for i in range(self.monitor_combo.count()):
            if self.monitor_combo.itemData(i) == cfg.monitor:
                self.monitor_combo.setCurrentIndex(i)
                break

    def _save_ocr_settings(self) -> None:
        cfg = OcrConfig.load_or_default(default_config_path())
        cfg.tesseract_cmd = self.tess_path_edit.text().strip()
        mon_data = self.monitor_combo.currentData()
        if mon_data is not None:
            cfg.monitor = int(mon_data)
        cfg.to_json(default_config_path())

    def _browse_tesseract(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Tesseract 실행 파일 선택", "",
            "실행 파일 (*.exe);;모든 파일 (*)"
        )
        if path:
            self.tess_path_edit.setText(path)
            self._save_ocr_settings()

    def _test_tesseract(self) -> None:
        path = self.tess_path_edit.text().strip()
        try:
            import pytesseract
            from pathlib import Path
            if path and Path(path).is_file():
                pytesseract.pytesseract.tesseract_cmd = path
            ver = pytesseract.get_tesseract_version()
            self._save_ocr_settings()
            QMessageBox.information(
                self, "연결 테스트 성공",
                f"Tesseract {ver} 정상 연결됨.\n설정이 저장되었습니다."
            )
        except Exception as e:
            QMessageBox.warning(
                self, "연결 테스트 실패",
                f"Tesseract를 찾을 수 없습니다.\n\n{e}\n\n"
                "경로를 확인하거나 Tesseract를 설치해주세요."
            )

    def _on_monitor_changed(self, _index: int) -> None:
        self._save_ocr_settings()

    # ── 섹션 라벨 ────────────────────────────────────────────────────

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {TEXT2}; font-size: 11px; font-weight: 600;"
            f"border-bottom: 1px solid {BORDER}; padding-bottom: 4px;")
        return lbl

    # ── UI 스케일 ─────────────────────────────────────────────────────

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

    def _check_update_manual(self) -> None:
        """버튼 클릭 시 업데이트를 동기로 확인한다."""
        from mdtracker.updater import _fetch_latest_release, _is_newer, _show_update_dialog, _find_installer_asset, _download_and_install
        from mdtracker import __version__
        self._update_status_lbl.setText("확인 중…")
        release = _fetch_latest_release()
        if not release:
            self._update_status_lbl.setText("확인 실패 (네트워크 오류)")
            return
        tag = release.get("tag_name", "")
        if tag and _is_newer(tag, __version__):
            self._update_status_lbl.setText(f"새 버전 {tag} 있음!")
            if _show_update_dialog(self, tag, release.get("body", "")):
                asset = _find_installer_asset(release.get("assets", []))
                if asset:
                    _download_and_install(self, asset, tag)
        else:
            self._update_status_lbl.setText("최신 버전입니다 ✓")

    def _backup_db(self) -> None:
        from ..app_paths import default_db_path
        db_src = default_db_path()
        path, _ = QFileDialog.getSaveFileName(
            self, "데이터 백업 저장", "mdtracker_backup.db",
            "SQLite DB (*.db *.sqlite);;모든 파일 (*)")
        if not path:
            return
        try:
            shutil.copy2(str(db_src), path)
            QMessageBox.information(self, "백업 완료",
                f"백업 파일이 저장되었습니다:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "백업 실패", f"백업 중 오류가 발생했습니다:\n{e}")

    def _restore_db(self) -> None:
        from ..app_paths import default_db_path
        db_dst = default_db_path()
        yes = QMessageBox.StandardButton.Yes
        if QMessageBox.warning(
            self, "데이터 복원",
            "기존 데이터를 모두 덮어씁니다.\n복원 후 앱을 재시작해야 합니다.\n\n계속할까요?",
            yes | QMessageBox.StandardButton.No,
        ) != yes:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "복원할 백업 파일 선택", "",
            "SQLite DB (*.db *.sqlite);;모든 파일 (*)")
        if not path:
            return
        try:
            shutil.copy2(path, str(db_dst))
            QMessageBox.information(self, "복원 완료",
                "복원이 완료되었습니다.\n앱을 재시작하면 복원된 데이터가 적용됩니다.")
        except Exception as e:
            QMessageBox.warning(self, "복원 실패", f"복원 중 오류가 발생했습니다:\n{e}")

    def _open_feedback(self) -> None:
        _open_feedback_url(self)
