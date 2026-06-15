"""대전 기록 뷰 — 상태바 + 전체높이 테이블 + OCR 슬라이드인 패널.

흐름:
  1) 상태바에서 '내 덱' 선택 → 세션 동안 유지
  2) [● OCR] 토글 → 듀얼 종료 시 자동 저장 + OcrPanel 피드백
  3) 테이블에서 상대 덱 더블클릭 입력
  4) [+] 버튼 → ManualDialog 모달로 수동 추가/교정
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping
from datetime import date as _date, datetime as _dt, timezone as _tz, timedelta as _td

from PySide6.QtCore import Qt, QDateTime, QRectF, QSize, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models import Match
from ..ocr import OcrEngine, to_match_fields
from ..ocr.config import OcrConfig, default_config_path
from ..styles.theme import BG, BORDER, PANEL, TEXT2
from .labels import (
    COIN_LABELS,
    COIN_TOSS_LABELS,
    EVENT_LABELS,
    RESULT_LABELS,
    WCS_OPP_DECK,
    combo_value,
    fill_combo,
    select_value,
)
from .filter_bar import FilterBar
from .manual_dialog import ManualDialog
from .ocr_panel import OcrPanel

PLACEHOLDER_OPP = "미정"

# ── 행 스타일 ─────────────────────────────────────────────────────
_ROW_H     = 48
_ROW_EVEN  = QColor(26, 34, 53)
_ROW_ALT   = QColor(31, 42, 63)
_ROW_SEL   = QColor(31, 51, 86)
_REVIEW_BG = QColor(35, 28, 10)

# ── 뱃지 (text → (bg, fg)) ───────────────────────────────────────
_BADGE: dict[str, tuple[str, str]] = {
    "승":   ("#22c55e", "#052e16"),
    "패":   ("#ef4444", "#fff1f2"),
    "무":   ("#6b7280", "#f9fafb"),
    "미상": ("#eab308", "#422006"),
    "선공": ("#60a5fa", "#172554"),
    "후공": ("#f97316", "#431407"),
}

# ── 결과 → 좌측 인디케이터 색 ────────────────────────────────────
_RESULT_BAR: dict[str, str] = {
    "win":  "#22c55e",
    "loss": "#ef4444",
    "draw": "#6b7280",
    "unknown": "#eab308",
}

_C_TEXT  = "#e2e8f0"
_C_TEXT2 = "#94a3b8"
_C_TEXT3 = "#475569"

_ROLE_MATCH_ID = int(Qt.ItemDataRole.UserRole)
_ROLE_NEEDS_REVIEW = _ROLE_MATCH_ID + 1
_ROLE_RESULT_BAR = _ROLE_MATCH_ID + 2
_OCR_IDLE_DETAIL = "코인토스 화면 대기 중…"


def _command_has_process(command: list[str], needle: str) -> bool:
    completed = _run_process_lookup(command)
    if completed is None:
        return False
    stdout = completed.stdout or b""
    return needle.casefold().encode("ascii") in stdout.lower()


def _command_succeeds(command: list[str]) -> bool:
    completed = _run_process_lookup(command)
    return completed is not None and completed.returncode == 0


# Windows: 콘솔 없는 pythonw로 실행 시 subprocess가 새 콘솔창을 띄우지 않도록 억제
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _run_process_lookup(
    command: list[str],
) -> subprocess.CompletedProcess[bytes] | None:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            check=False,
            timeout=2,
            creationflags=_NO_WINDOW,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None


def _is_game_running() -> bool:
    return (
        _command_has_process(
            ["tasklist.exe", "/FI", "IMAGENAME eq masterduel.exe"],
            "masterduel.exe",
        )
        or _command_succeeds(["pgrep", "-f", "masterduel.exe"])
    )


class _MiniKpiCard(QWidget):
    """기록 탭용 컴팩트 승률 카드."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: {BG}; border-bottom: 1px solid {BORDER};"
            "border-radius: 8px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        tl = QLabel(title)
        tl.setStyleSheet(
            f"color: {_C_TEXT2}; font-size: 10px; font-weight: 600; border: none;")
        layout.addWidget(tl)

        self._rate = QLabel("—")
        self._rate.setStyleSheet(
            f"color: {_C_TEXT}; font-size: 22px; font-weight: 700; border: none;")
        layout.addWidget(self._rate)

        self._bar = QWidget()
        self._bar.setFixedHeight(4)
        self._bar.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #ef4444, stop:0.5 #eab308, stop:1 #22c55e);"
            "border-radius: 2px;")
        layout.addWidget(self._bar)

        self._detail = QLabel("—")
        self._detail.setStyleSheet(
            f"color: {_C_TEXT2}; font-size: 10px; border: none;")
        layout.addWidget(self._detail)

    def update_data(self, ov: Mapping[str, int | float | None]) -> None:
        win_rate = ov["win_rate"]
        wr = float(win_rate) if isinstance(win_rate, (int, float)) else 0.0
        color = "#22c55e" if wr >= 0.5 else "#ef4444"
        self._rate.setText(f"{wr * 100:.1f}%")
        self._rate.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: 700; border: none;")
        fill = int(wr * 100)
        self._bar.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 #ef4444, stop:0.5 #eab308, stop:{fill/100:.2f} #22c55e,"
            f"stop:{min(fill/100 + 0.01, 1):.2f} #2a3349, stop:1 #2a3349);"
            "border-radius: 2px;")
        self._detail.setText(
            f"{ov['wins']}승  {ov['losses']}패 · {ov['n']}전")


class MatchTableDelegate(QStyledItemDelegate):
    """매치 테이블 전체 셀 커스텀 페인터.

    col 0 : 날짜 + 좌측 결과 컬러 바
    col 3-5: 뱃지 필
    col 6 : 타입 아웃라인 태그
    """

    _BADGE_COLS = frozenset({3, 4, 5})

    def _row_bg(self, index, selected: bool):
        if selected:
            return _ROW_SEL
        review = index.data(_ROLE_NEEDS_REVIEW)
        if review:
            return _REVIEW_BG
        return _ROW_ALT if index.row() % 2 else _ROW_EVEN

    def paint(self, painter: QPainter, option, index) -> None:
        col  = index.column()
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        sel  = bool(option.state & QStyle.StateFlag.State_Selected)

        painter.save()
        painter.fillRect(option.rect, self._row_bg(index, sel))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        if col == 0:
            # ── 좌측 결과 바 ────────────────────────────────────
            bar_color = index.data(_ROLE_RESULT_BAR)
            if bar_color:
                bar = QRectF(option.rect.left(), option.rect.top() + 6,
                             3, option.rect.height() - 12)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(bar_color))
                painter.drawRoundedRect(bar, 1.5, 1.5)

            # ── 날짜 텍스트 ─────────────────────────────────────
            font = painter.font()
            font.setPointSize(10)
            painter.setFont(font)
            painter.setPen(QColor("#94a3b8"))
            text_rect = option.rect.adjusted(10, 0, -4, 0)
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                text,
            )

        elif col in self._BADGE_COLS:
            colors = _BADGE.get(text)
            if colors:
                bw, bh = 56, 22
                cx = option.rect.center().x()
                cy = option.rect.center().y()
                rect = QRectF(cx - bw / 2, cy - bh / 2, bw, bh)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(colors[0]))
                painter.drawRoundedRect(rect, bh / 2, bh / 2)
                painter.setPen(QColor(colors[1]))
                font = painter.font()
                font.setBold(True)
                font.setPointSize(9)
                painter.setFont(font)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            else:
                painter.setPen(QColor("#94a3b8"))
                painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, text)

        elif col == 6 and text:
            # ── 타입 태그 (아웃라인 스타일) ──────────────────────
            tw, th = 42, 20
            cx = option.rect.center().x()
            cy = option.rect.center().y()
            rect = QRectF(cx - tw / 2, cy - th / 2, tw, th)
            painter.setPen(QColor("#2a3349"))
            painter.setBrush(QColor(26, 34, 53))
            painter.drawRoundedRect(rect, 4, 4)
            painter.setPen(QColor("#94a3b8"))
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        return QSize(60, _ROW_H)


def _attach_autocomplete(combo: QComboBox) -> None:
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    comp = QCompleter(combo.model(), combo)
    comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    comp.setFilterMode(Qt.MatchFlag.MatchContains)
    combo.setCompleter(comp)


class DeckComboDelegate(QStyledItemDelegate):
    def __init__(self, names_provider: Callable[[], list[str]], parent=None):
        super().__init__(parent)
        self._names = names_provider

    def paint(self, painter: QPainter, option, index) -> None:
        from PySide6.QtWidgets import QStyle
        sel = bool(option.state & QStyle.StateFlag.State_Selected)
        review = index.data(_ROLE_NEEDS_REVIEW)
        if sel:
            bg = _ROW_SEL
        elif review:
            bg = _REVIEW_BG
        else:
            bg = _ROW_ALT if index.row() % 2 else _ROW_EVEN
        painter.fillRect(option.rect, bg)
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setPen(QColor(_C_TEXT))
        painter.drawText(
            option.rect.adjusted(8, 0, -8, 0),
            Qt.AlignmentFlag.AlignVCenter,
            text,
        )
        painter.restore()

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.setEditable(True)
        combo.addItems(self._names())
        _attach_autocomplete(combo)
        return combo

    def setEditorData(self, editor, index):
        value = index.data() or ""
        editor.setCurrentText("" if value == PLACEHOLDER_OPP else value)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText().strip(), Qt.ItemDataRole.EditRole)


class _UndoToast(QWidget):
    """전체 삭제 후 5초간 표시되는 Undo 토스트 위젯."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._backup: list = []
        self._db = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._expire)
        self._countdown = QTimer(self)
        self._countdown.setInterval(1000)
        self._countdown.timeout.connect(self._tick)
        self._remaining = 5

        self.setStyleSheet(
            "background: #1e293b; border: 1px solid #334155; border-radius: 6px;")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(10)
        self._lbl = QLabel()
        self._lbl.setStyleSheet(
            "color: #e2e8f0; font-size: 12px; background: transparent;")
        undo_btn = QPushButton("되돌리기")
        undo_btn.setFixedHeight(24)
        undo_btn.setStyleSheet(
            "background: #4361ee; color: #fff; border: none; border-radius: 4px;"
            "padding: 2px 10px; font-size: 11px;")
        undo_btn.clicked.connect(self._undo)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            "background: transparent; color: #64748b; border: none; font-size: 11px;")
        close_btn.clicked.connect(self._expire)
        lay.addWidget(self._lbl, 1)
        lay.addWidget(undo_btn)
        lay.addWidget(close_btn)
        self.setFixedHeight(44)

    def show_undo(self, count: int, backup: list) -> None:
        self._backup = backup
        self._db = self.parent().db  # type: ignore[union-attr]
        self._remaining = 5
        self._lbl.setText(f"{count}건이 삭제되었습니다  (5초 후 자동 종료)")
        self.show()
        self._reposition()
        self._timer.start(5000)
        self._countdown.start()

    def _tick(self) -> None:
        self._remaining -= 1
        if self._remaining > 0:
            self._lbl.setText(
                self._lbl.text().split("(")[0].strip()
                + f"  ({self._remaining}초 후 자동 종료)")

    def _undo(self) -> None:
        self._timer.stop()
        self._countdown.stop()
        if self._db and self._backup:
            self._db.matches.delete_all()
            for m in reversed(self._backup):
                m.id = None  # type: ignore[assignment]
                self._db.matches.add(m)
            rv = self.parent()
            if hasattr(rv, "refresh"):
                rv.refresh()  # type: ignore[union-attr]
            if hasattr(rv, "data_changed"):
                rv.data_changed.emit()  # type: ignore[union-attr]
        self.hide()

    def _expire(self) -> None:
        self._timer.stop()
        self._countdown.stop()
        self.hide()

    def _reposition(self) -> None:
        p = self.parent()
        if p:
            w = min(p.width() - 40, 420)
            self.setFixedWidth(w)
            self.move((p.width() - w) // 2, p.height() - self.height() - 16)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reposition()


class RecordView(QWidget):
    data_changed = Signal()
    MY_DECK_COL  = 1
    OPP_DECK_COL = 2

    def __init__(self, db) -> None:
        super().__init__()
        self.db = db
        self._loading_table = False
        self._restoring = False
        self._engine = OcrEngine(OcrConfig.load_or_default(default_config_path()))
        self._poller = None
        self._last_ocr_id: int | None = None
        self._game_polling = False
        self._ocr_should_run = True
        self._ocr_state_detail = _OCR_IDLE_DETAIL
        self._build()
        self._init_ocr_availability()
        self.refresh()
        self._restore_session()
        self.my_deck.currentTextChanged.connect(self._save_session)
        self.event_combo.currentIndexChanged.connect(self._save_session)
        self.event_combo.currentIndexChanged.connect(self._sync_wcs_opp_deck)
        self._sync_wcs_opp_deck()  # 복원된 타입이 WCS면 상대 덱 고정 반영
        self._game_watch_timer = QTimer(self)
        self._game_watch_timer.setInterval(2000)
        self._game_watch_timer.timeout.connect(self._sync_game_process_status)
        self._game_watch_timer.start()
        # tesseract 설치 시 앱 시작과 함께 자동 감지 시작
        QTimer.singleShot(200, self._auto_start_ocr)

    # ── 레이아웃 ─────────────────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 상태바 ────────────────────────────────────────────────
        self.status_bar = QWidget()
        self.status_bar.setFixedHeight(76)
        self.status_bar.setStyleSheet(
            f"background-color: {PANEL}; border-bottom: 1px solid {BORDER};")
        sb = QVBoxLayout(self.status_bar)
        sb.setContentsMargins(8, 4, 8, 4)
        sb.setSpacing(4)

        self.ocr_row = QWidget()
        ocr_layout = QHBoxLayout(self.ocr_row)
        ocr_layout.setContentsMargins(0, 0, 0, 0)
        ocr_layout.setSpacing(8)

        self.session_row = QWidget()
        session_layout = QHBoxLayout(self.session_row)
        session_layout.setContentsMargins(0, 0, 0, 0)
        session_layout.setSpacing(8)

        self.ocr_btn = QPushButton("● 자동 기록")
        self.ocr_btn.setToolTip("마스터듀얼 화면을 자동으로 인식해 대전 결과를 기록합니다\n게임이 실행되면 자동으로 시작됩니다")
        self.ocr_btn.setCheckable(True)
        self.ocr_btn.setFixedWidth(76)
        self.ocr_status = QLabel("준비됨")
        self.ocr_status.setStyleSheet(f"color: {TEXT2}; background: transparent;")
        self.today_lbl = QLabel("")
        self.today_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.today_lbl.setStyleSheet(
            "color: #94a3b8; background: transparent; font-size: 12px;")
        self.tess_install_btn = QPushButton("⬇ Tesseract 설치 안내")
        self.tess_install_btn.setFixedWidth(160)
        self.tess_install_btn.setStyleSheet(
            "background: #7f1d1d; color: #fca5a5; border: none; border-radius: 4px;"
            "font-size: 11px; padding: 2px 6px;")
        self.tess_install_btn.setToolTip(
            "Tesseract OCR이 설치되지 않았습니다.\n클릭하면 설치 안내 페이지가 열립니다.")
        self.tess_install_btn.clicked.connect(self._show_tesseract_install_guide)
        self.tess_install_btn.hide()
        ocr_layout.addWidget(self.ocr_btn)
        ocr_layout.addWidget(self.ocr_status)
        ocr_layout.addWidget(self.tess_install_btn)
        ocr_layout.addWidget(self.today_lbl, 1)

        session_layout.addWidget(QLabel("내 덱"))
        self.my_deck = QComboBox()
        self.my_deck.setEditable(True)
        self.my_deck.setFixedWidth(140)
        _attach_autocomplete(self.my_deck)
        session_layout.addWidget(self.my_deck)

        session_layout.addWidget(QLabel("상대 덱"))
        self.sess_opp_deck = QComboBox()
        self.sess_opp_deck.setEditable(True)
        self.sess_opp_deck.setFixedWidth(140)
        self.sess_opp_deck.setPlaceholderText("미정")
        _attach_autocomplete(self.sess_opp_deck)
        session_layout.addWidget(self.sess_opp_deck)

        session_layout.addWidget(QLabel("타입"))
        self.event_combo = QComboBox()
        self.event_combo.setFixedWidth(80)
        fill_combo(self.event_combo, EVENT_LABELS)
        session_layout.addWidget(self.event_combo)

        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(32, 28)
        self.add_btn.setToolTip("수동 기록 추가")
        session_layout.addWidget(self.add_btn)
        session_layout.addStretch()

        sb.addWidget(self.ocr_row)
        sb.addWidget(self.session_row)
        root.addWidget(self.status_bar)

        # ── 액션 바 ───────────────────────────────────────────────
        action_bar = QWidget()
        action_bar.setFixedHeight(38)
        ab = QHBoxLayout(action_bar)
        ab.setContentsMargins(8, 4, 8, 4)
        ab.setSpacing(4)
        ab.addStretch()
        self.delete_btn = QPushButton("선택 삭제")
        self.delete_btn.setEnabled(False)
        self.delete_btn.setFixedHeight(28)
        self.delete_all_btn = QPushButton("전체 삭제")
        self.delete_all_btn.setFixedHeight(28)
        self.export_btn = QPushButton("CSV 내보내기")
        self.export_btn.setFixedHeight(28)
        ab.addWidget(self.delete_btn)
        ab.addWidget(self.delete_all_btn)
        ab.addWidget(self.export_btn)
        root.addWidget(action_bar)

        # ── 필터바 ───────────────────────────────────────────────
        self.filter_bar = FilterBar()
        root.addWidget(self.filter_bar)

        # ── 미니 KPI 카드 (전체/오늘/세션) ───────────────────────
        kpi_bar = QWidget()
        kpi_bar.setFixedHeight(82)
        kl = QHBoxLayout(kpi_bar)
        kl.setContentsMargins(8, 4, 8, 4)
        kl.setSpacing(8)
        self._mini_cards: list[_MiniKpiCard] = []
        for title in ["전체", "오늘"]:
            card = _MiniKpiCard(title)
            kl.addWidget(card)
            self._mini_cards.append(card)
        root.addWidget(kpi_bar)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["일시", "내 덱", "상대 덱", "토스", "선/후공", "결과", "타입"])
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(_ROW_H)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        deck_delegate = DeckComboDelegate(
            lambda: self.db.decks.list_names(), self.table)
        self.table.setItemDelegateForColumn(self.MY_DECK_COL, deck_delegate)
        self.table.setItemDelegateForColumn(self.OPP_DECK_COL, deck_delegate)
        match_delegate = MatchTableDelegate(self.table)
        for col in (0, 3, 4, 5, 6):
            self.table.setItemDelegateForColumn(col, match_delegate)

        self.ocr_panel = OcrPanel()
        self.ocr_panel.hide()

        # 미확정 행 안내 배너 (미확정 행이 있을 때만 표시)
        self._review_banner = QLabel(
            "⚠  노란색 행은 상대 덱 또는 결과가 미확정입니다. "
            "더블클릭하여 수정하거나 셀을 직접 편집하세요.")
        self._review_banner.setStyleSheet(
            "background: #422006; color: #fbbf24; font-size: 11px; "
            "padding: 5px 12px; border-radius: 4px;")
        self._review_banner.setWordWrap(False)
        self._review_banner.hide()
        root.addWidget(self._review_banner)

        root.addWidget(self.table, 1)

        # ── 시그널 연결 ───────────────────────────────────────────
        self.ocr_btn.toggled.connect(self._on_ocr_toggle)
        self.add_btn.clicked.connect(self._on_add_manual)
        self.delete_btn.clicked.connect(self._on_delete)
        self.delete_all_btn.clicked.connect(self._on_delete_all)
        self.export_btn.clicked.connect(self._on_export_csv)
        self.table.itemSelectionChanged.connect(self._on_select)
        self.table.itemChanged.connect(self._on_cell_edited)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.ocr_panel.confirmed.connect(self._on_panel_confirmed)
        self.ocr_panel.dismissed.connect(self.ocr_panel.hide)
        self.filter_bar.changed.connect(self._on_filter_changed)

    # ── 데이터 갱신 ──────────────────────────────────────────────

    def refresh(self) -> None:
        self._reload_deck_combos()
        self.filter_bar.set_deck_options_from(self.db.matches.all())
        self.filter_bar.set_season_options_from(self.db.matches.all())
        self._reload_table()
        self._update_today_lbl()
        self._update_mini_kpi()

    def _on_filter_changed(self) -> None:
        """필터 조건 변경 — 테이블·미니 KPI만 다시 그린다 (데이터 불변)."""
        self._reload_table()
        self._update_mini_kpi()

    def _update_mini_kpi(self) -> None:
        from .. import stats as _stats
        all_m = self.filter_bar.apply(self.db.matches.all())
        today  = _date.today().isoformat()
        today_m = [m for m in all_m if m.played_at.startswith(today)]
        for card, ms in zip(self._mini_cards,
                            [all_m, today_m]):
            s = _stats.win_rate_summary(ms)
            card.update_data(s["overall"])

    def _reload_deck_combos(self) -> None:
        self._restoring = True
        try:
            mine_names = self.db.decks.list_mine_names()   # is_mine=True만
            all_names  = self.db.decks.list_names()        # 전체

            from .completer import make_deck_completer
            catalog = self._catalog_names()
            for combo, names in (
                (self.my_deck,       mine_names or all_names),  # 내 덱 없으면 전체 폴백
                (self.sess_opp_deck, all_names),
            ):
                cur = combo.currentText()
                combo.clear()
                combo.addItems(names)
                combo.setCurrentText(cur)
                # 드롭다운은 사용자 덱만, 자동완성 후보에만 카탈로그 추가
                combo.setCompleter(
                    make_deck_completer(list(names) + catalog, combo))
        finally:
            self._restoring = False

    # ── 세션 영속 ────────────────────────────────────────────────

    def _restore_session(self) -> None:
        self._restoring = True
        try:
            deck = self.db.get_setting("session_my_deck", "")
            if deck:
                self.my_deck.setCurrentText(deck)
            ev = self.db.get_setting("session_event", "")
            if ev:
                select_value(self.event_combo, ev)
        finally:
            self._restoring = False

    def _save_session(self, *_) -> None:
        if self._restoring:
            return
        self.db.set_setting("session_my_deck", self.my_deck.currentText().strip())
        self.db.set_setting("session_event", combo_value(self.event_combo) or "")

    def _is_wcs(self) -> bool:
        return combo_value(self.event_combo) == "wcs"

    def _sync_wcs_opp_deck(self, *_) -> None:
        """타입이 WCS면 상대 덱을 'WCS'로 고정 (WCS는 상대 덱 확인 불가)."""
        if self._is_wcs():
            self.sess_opp_deck.setCurrentText(WCS_OPP_DECK)
            self.sess_opp_deck.setEnabled(False)
        else:
            if self.sess_opp_deck.currentText().strip() == WCS_OPP_DECK:
                self.sess_opp_deck.setCurrentText("")
            self.sess_opp_deck.setEnabled(True)

    def _reset_session_opp(self) -> None:
        """기록 후 상대 덱 입력 초기화 — WCS 모드면 'WCS' 유지."""
        self.sess_opp_deck.setCurrentText(WCS_OPP_DECK if self._is_wcs() else "")

    @staticmethod
    def _fmt_date(played_at: str) -> str:
        try:
            d = _date.fromisoformat(played_at[:10])
            t = played_at[11:16]
            today = _date.today()
            if d == today:
                return f"오늘 {t}"
            if d == today - _td(days=1):
                return f"어제 {t}"
            return f"{d.month:02d}/{d.day:02d} {t}"
        except Exception:
            return played_at[:16]

    def _reload_table(self) -> None:
        self._loading_table = True
        try:
            matches = list(reversed(self.filter_bar.apply(self.db.matches.list())))
            self.table.setRowCount(len(matches))
            for row, m in enumerate(matches):
                # 미확정(confirmed=False)도 교정 대상 — 통계에서 제외되므로
                # 하이라이트로 노출해 사용자 확정을 유도한다
                needs_review = (m.opponent_deck == PLACEHOLDER_OPP
                                or m.my_deck == PLACEHOLDER_OPP
                                or m.result == "unknown"
                                or m.coin_result == "unknown"
                                or not m.confirmed)
                bar_color = _RESULT_BAR.get(m.result, "")
                row_bg = _REVIEW_BG if needs_review else (
                    _ROW_ALT if row % 2 else _ROW_EVEN)
                cells: list[str] = [
                    self._fmt_date(m.played_at),
                    m.my_deck, m.opponent_deck,
                    COIN_TOSS_LABELS.get(m.coin_toss, "") if m.coin_toss else "",
                    COIN_LABELS.get(m.coin_result, m.coin_result) or "",
                    RESULT_LABELS.get(m.result, m.result) or "",
                    EVENT_LABELS.get(m.event_type, m.event_type) or "",
                ]
                for col, text in enumerate(cells):
                    item = QTableWidgetItem(text)
                    if col == 0:
                        item.setData(_ROLE_MATCH_ID, m.id)
                        item.setData(_ROLE_NEEDS_REVIEW, needs_review)
                        item.setData(_ROLE_RESULT_BAR, bar_color)
                    elif col in (3, 4, 5):
                        item.setData(_ROLE_NEEDS_REVIEW, needs_review)
                    if col in (self.MY_DECK_COL, self.OPP_DECK_COL):
                        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                        item.setBackground(row_bg)
                        item.setForeground(QColor(_C_TEXT))
                    elif col not in (0, 3, 4, 5, 6):
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        item.setBackground(row_bg)
                    else:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row, col, item)
        finally:
            self._loading_table = False
        # 미확정 행이 하나라도 있으면 배너 표시
        has_review = any(
            self.table.item(r, 0) and self.table.item(r, 0).data(_ROLE_NEEDS_REVIEW)
            for r in range(self.table.rowCount())
        )
        self._review_banner.setVisible(has_review)

    def _update_today_lbl(self) -> None:
        today = _date.today().isoformat()
        matches = [m for m in self.db.matches.all()
                   if m.played_at.startswith(today)]
        wins   = sum(1 for m in matches if m.result == "win")
        losses = sum(1 for m in matches if m.result == "loss")
        total  = len(matches)
        if total == 0:
            self.today_lbl.setText("오늘 기록 없음")
            return
        pct = f"{wins / total * 100:.0f}%"
        self.today_lbl.setText(
            f"오늘  "
            f"<span style='color:#22c55e;font-weight:bold'>{wins}승</span> "
            f"<span style='color:#ef4444;font-weight:bold'>{losses}패</span> "
            f"<span style='color:#94a3b8'>({pct})</span>"
        )

    # ── OCR ──────────────────────────────────────────────────────

    def _show_tesseract_install_guide(self) -> None:
        """Tesseract 설치 안내 탭(settings_view)을 열거나 설치 URL을 연다."""
        try:
            from ..ui.main_window import MainWindow as _MW
            parent = self.parent()
            while parent and not isinstance(parent, _MW):
                parent = parent.parent()
            if parent:
                # 설정 탭으로 이동 (index 2)
                parent._nav.setCurrentRow(2)
                return
        except Exception:
            pass
        import webbrowser
        webbrowser.open("https://github.com/UB-Mannheim/tesseract/wiki")

    def _init_ocr_availability(self) -> None:
        try:
            from pathlib import Path
            import pytesseract
            from ..app_paths import find_tesseract_exe

            cfg_cmd = self._engine.cfg.tesseract_cmd

            # 1) 설정 경로가 실제 존재하면 사용
            if cfg_cmd and Path(cfg_cmd).is_file():
                pytesseract.pytesseract.tesseract_cmd = cfg_cmd
            else:
                # 2) 자동 탐색 (번들 경로 → 표준 설치 경로 → PATH)
                auto_path = find_tesseract_exe()
                if auto_path:
                    pytesseract.pytesseract.tesseract_cmd = auto_path
                    # 발견된 경로를 설정에 저장
                    self._engine.cfg.tesseract_cmd = auto_path

            pytesseract.get_tesseract_version()
            self._ocr_available = True
            self.ocr_status.setText("OCR 준비됨 — masterduel.exe 확인 대기")
        except Exception:
            self._ocr_available = False
            self.ocr_btn.setEnabled(False)
            self.tess_install_btn.show()
            self.ocr_status.setText("자동 기록 비활성 — Tesseract 미설치")
            self.ocr_btn.setToolTip(
                "Tesseract OCR이 설치되지 않아 자동 기록을 사용할 수 없습니다.\n"
                "오른쪽 버튼을 클릭하여 설치 안내를 확인하세요."
            )

    def _auto_start_ocr(self) -> None:
        if not getattr(self, "_ocr_available", False):
            return
        self._ocr_should_run = True
        self._sync_game_process_status()

    def _poll_game_start(self) -> None:
        """게임 실행을 대기하다가 감지되면 OCR을 자동 시작한다."""
        self._sync_game_process_status()

    def _sync_game_process_status(self) -> None:
        if not getattr(self, "_ocr_available", False):
            return
        if _is_game_running():
            self._game_polling = False
            if self._ocr_should_run and not self.ocr_btn.isChecked():
                self._set_running_status("OCR 시작 중")
                self.ocr_btn.setChecked(True)
            elif self.ocr_btn.isChecked() and "미실행" in self.ocr_status.text():
                self._set_running_status(self._ocr_state_detail)
            return

        self._game_polling = True
        if self._poller and self._poller.isRunning():
            self._poller.stop()
        self._reset_ocr_button("masterduel.exe 미실행")

    def _reset_ocr_button(self, status_text: str) -> None:
        self.ocr_btn.blockSignals(True)
        self.ocr_btn.setChecked(False)
        self.ocr_btn.blockSignals(False)
        self.ocr_btn.setText("● 자동 기록")
        self.ocr_btn.setStyleSheet("")
        self.ocr_status.setText(status_text)

    def _set_running_status(self, detail: str) -> None:
        self._ocr_state_detail = detail
        self.ocr_status.setText(f"작동중 - {detail}")

    def _on_ocr_toggle(self, checked: bool) -> None:
        if checked:
            self._ocr_should_run = True
            if not _is_game_running():
                self._reset_ocr_button("masterduel.exe 미실행")
                return
            if self._poller is None:
                from ..ocr import OcrPoller
                self._poller = OcrPoller(self._engine)
                self._poller.match_detected.connect(self._on_ocr_detected)
                self._poller.state_changed.connect(self._on_poller_state_changed)
                self._poller.error.connect(self._on_ocr_error)
            if not self._poller.isRunning():
                self._poller.start()
            self.ocr_btn.setText("⏹ 기록 중")
            self.ocr_btn.setStyleSheet(
                "background-color: #22c55e; color: #052e16; border: none;"
                "border-radius: 6px; padding: 5px 10px; font-weight: bold;")
            self._set_running_status(_OCR_IDLE_DETAIL)
        else:
            self._ocr_should_run = False
            if self._poller:
                self._poller.stop()
            self.ocr_btn.setText("● 자동 기록")
            self.ocr_btn.setStyleSheet("")
            self.ocr_status.setText("OCR 감지 중지")

    def _on_ocr_detected(self, res) -> None:
        f = to_match_fields(res)
        my  = self.my_deck.currentText().strip() or PLACEHOLDER_OPP
        opp = self.sess_opp_deck.currentText().strip() or PLACEHOLDER_OPP
        played = QDateTime.currentDateTime().toString(Qt.DateFormat.ISODate)
        # 미감지 신호는 'unknown'으로 저장 — 'first' 등으로 추정하지 않는다 (설계 §6)
        coin   = res.coin_result or "unknown"
        result = res.result or "unknown"
        m = Match(
            played_at=played, my_deck=my, opponent_deck=opp,
            coin_result=coin,
            coin_toss=res.coin_toss,
            result=result,
            event_type=combo_value(self.event_combo),
            season=played[:7],
            source="ocr", ocr_confidence=f["ocr_confidence"],
            confirmed=(f["confirmed"]
                       and my != PLACEHOLDER_OPP
                       and opp != PLACEHOLDER_OPP
                       and result != "unknown"
                       and coin != "unknown"),
        )
        self._register_deck(my, is_mine=True)
        self._register_deck(opp, is_mine=False)
        self.db.matches.add(m)
        self._last_ocr_id = m.id
        self._reset_session_opp()
        self.refresh()
        self.data_changed.emit()

        rl = RESULT_LABELS.get(m.result, m.result)
        # 미확정이면 패널 표시 (사용자 교정·확정) — 상대 덱 미입력,
        # 결과/선후공 미상, 낮은 OCR 신뢰도(예: WCS 배너)를 모두 포괄한다
        if not m.confirmed:
            self.ocr_panel.populate(
                result=m.result,
                coin=COIN_TOSS_LABELS.get(m.coin_toss, "—") if m.coin_toss else "—",
                turn=COIN_LABELS.get(m.coin_result, m.coin_result),
                deck_names=self.db.decks.list_names(),
            )
            self.ocr_panel.show()

        if m.confirmed:
            self.ocr_status.setText(f"✅ {rl} 기록됨")
        else:
            self.ocr_status.setText(f"⚠ {rl} 기록됨 (미확정)")
        # 3초 후 다시 "감지 중" 상태로 복귀
        QTimer.singleShot(3000, self._restore_ocr_status)

    def _restore_ocr_status(self) -> None:
        if self.ocr_btn.isChecked():
            self._set_running_status(_OCR_IDLE_DETAIL)

    _OCR_STATE_TEXTS = {
        "COIN": "선공 / 후공 선택 대기",
        "PLAYING": "게임 결과 대기",
    }

    def _on_poller_state_changed(self, state_name: str) -> None:
        text = self._OCR_STATE_TEXTS.get(state_name)
        if text and self.ocr_btn.isChecked():
            self._set_running_status(text)

    def _on_panel_confirmed(self) -> None:
        m = (self.db.matches.get(self._last_ocr_id)
             if self._last_ocr_id is not None else None)
        if m is None:
            self.ocr_panel.hide()
            return
        changed = False
        opp = self.ocr_panel.opp_deck_text
        if opp and opp != PLACEHOLDER_OPP and opp != m.opponent_deck:
            m.opponent_deck = opp
            self._register_deck(opp, is_mine=False)
            changed = True
        # 결과 미상 교정: 패널에서 고른 승/패/무 반영 (설계 §6)
        rv = self.ocr_panel.result_value
        if rv and rv != m.result:
            m.result = rv
            changed = True
        confirmed = (m.my_deck != PLACEHOLDER_OPP
                     and m.opponent_deck != PLACEHOLDER_OPP
                     and m.result != "unknown")
        if confirmed != m.confirmed:
            m.confirmed = confirmed
            changed = True
        if changed:
            self.db.matches.update(m)
            self.refresh()
            self.data_changed.emit()
        self.ocr_panel.hide()

    def _on_ocr_error(self, msg: str) -> None:
        self.ocr_status.setText(f"⚠ 오류: {msg}")

    def shutdown(self) -> None:
        if hasattr(self, "_game_watch_timer"):
            self._game_watch_timer.stop()
        if self._poller and self._poller.isRunning():
            self._poller.stop()
        if getattr(self, "_artfetcher", None) is not None:
            self._artfetcher.shutdown()

    # ── 수동 추가 / 교정 ─────────────────────────────────────────

    def _collect(self) -> Match:
        """기본 Match 객체 반환 — 세션 덱 + 현재 시각 + 기본값."""
        played = QDateTime.currentDateTime().toString(Qt.DateFormat.ISODate)
        my  = self.my_deck.currentText().strip() or PLACEHOLDER_OPP
        opp = self.sess_opp_deck.currentText().strip() or PLACEHOLDER_OPP
        return Match(
            played_at=played, my_deck=my, opponent_deck=opp,
            coin_result="first", coin_toss=None, result="win",
            event_type=combo_value(self.event_combo),
            season=played[:7], source="manual", confirmed=True,
        )

    def _on_add_manual(self) -> None:
        dlg = ManualDialog(
            self, self.db,
            my_deck=self.my_deck.currentText().strip(),
            opp_deck=self.sess_opp_deck.currentText().strip(),
            event_type=combo_value(self.event_combo),
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        d = dlg.get_data()
        my  = d["my_deck"]  or PLACEHOLDER_OPP
        opp = d["opponent_deck"] or PLACEHOLDER_OPP
        m = Match(
            played_at=d["played_at"], my_deck=my, opponent_deck=opp,
            coin_result=d["coin_result"], coin_toss=d["coin_toss"],
            result=d["result"], event_type=d["event_type"],
            rank_label=d["rank_label"], notes=d["notes"],
            season=d["season"], source="manual", confirmed=True,
        )
        self._register_deck(my, is_mine=True)
        self._register_deck(opp, is_mine=False)
        self.db.matches.add(m)
        self._reset_session_opp()
        self.refresh()
        self.data_changed.emit()

    # ── 표 인라인 편집 ────────────────────────────────────────────

    def _on_cell_edited(self, item) -> None:
        if self._loading_table:
            return
        col = item.column()
        if col not in (self.MY_DECK_COL, self.OPP_DECK_COL):
            return
        id_item = self.table.item(item.row(), 0)
        mid = id_item.data(_ROLE_MATCH_ID) if id_item else None
        m = self.db.matches.get(mid) if mid is not None else None
        if m is None:
            return
        text = item.text().strip()
        if col == self.MY_DECK_COL:
            m.my_deck = text or m.my_deck
            self._register_deck(m.my_deck, is_mine=True)
        else:
            m.opponent_deck = text or PLACEHOLDER_OPP
            self._register_deck(m.opponent_deck, is_mine=False)
        if (m.my_deck != PLACEHOLDER_OPP and m.opponent_deck != PLACEHOLDER_OPP
                and m.result != "unknown"):
            m.confirmed = True
        self.db.matches.update(m)
        QTimer.singleShot(0, self._post_edit_refresh)

    def _post_edit_refresh(self) -> None:
        self._reload_table()
        self._reload_deck_combos()
        self.data_changed.emit()

    def _on_cell_double_clicked(self, row: int, col: int) -> None:
        if col in (self.MY_DECK_COL, self.OPP_DECK_COL):
            return
        mid = self._selected_id()
        if mid is None:
            return
        m = self.db.matches.get(mid)
        if m is None:
            return
        dlg = ManualDialog(self, self.db, match=m)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        d = dlg.get_data()
        m.played_at     = d["played_at"]
        m.my_deck       = d["my_deck"]       or m.my_deck
        m.opponent_deck = d["opponent_deck"] or PLACEHOLDER_OPP
        m.coin_result   = d["coin_result"]   or m.coin_result
        m.coin_toss     = d["coin_toss"]
        m.result        = d["result"]        or m.result
        m.event_type    = d["event_type"]    or m.event_type
        m.rank_label    = d["rank_label"]
        m.notes         = d["notes"]
        m.season        = d["season"]
        m.confirmed     = True
        self.db.matches.update(m)
        self.refresh()
        self.data_changed.emit()

    # ── 선택 / 삭제 ──────────────────────────────────────────────

    def _selected_id(self):
        items = self.table.selectedItems()
        if not items:
            return None
        id_item = self.table.item(items[0].row(), 0)
        return id_item.data(_ROLE_MATCH_ID) if id_item else None

    def _on_select(self) -> None:
        self.delete_btn.setEnabled(self._selected_id() is not None)

    def _on_delete(self) -> None:
        mid = self._selected_id()
        if mid is None:
            return
        yes = QMessageBox.StandardButton.Yes
        if QMessageBox.question(self, "삭제", "선택한 기록을 삭제할까요?",
                                yes | QMessageBox.StandardButton.No) == yes:
            self.db.matches.delete(mid)
            self.refresh()
            self.data_changed.emit()

    def _on_delete_all(self) -> None:
        count = len(self.db.matches.all())
        if count == 0:
            return
        yes = QMessageBox.StandardButton.Yes
        if QMessageBox.question(
            self, "전체 삭제",
            f"기록 {count}건을 전부 삭제할까요?",
            yes | QMessageBox.StandardButton.No,
        ) != yes:
            return
        backup = list(self.db.matches.all())
        self.db.matches.delete_all()
        self.refresh()
        self.data_changed.emit()
        self._undo_toast.show_undo(count, backup)

    def _on_export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "CSV 수출", "mdtracker_export.csv", "CSV 파일 (*.csv)")
        if not path:
            return
        count = self.db.matches.export_csv(path)
        QMessageBox.information(self, "내보내기 완료", f"{count}건을 저장했습니다:\n{path}")

    def _register_deck(self, name: str, is_mine: bool) -> None:
        # 'WCS'는 실제 덱이 아닌 sentinel — 덱 목록에 등록하지 않는다
        if not name or name in (PLACEHOLDER_OPP, WCS_OPP_DECK):
            return
        if name not in set(self.db.decks.list_names()):
            self.db.decks.add(name, is_mine=is_mine)
        # 덱 입력 시 대표 카드 아트를 백그라운드로 자동 로드
        self._request_art(name)

    # ── 카드 아트 (지연 초기화) ──────────────────────────────────────

    def _art_service(self):
        if getattr(self, "_art", None) is None:
            from ..cardart.service import CardArtService
            self._art = CardArtService(self.db.decks)
        return self._art

    def _art_fetcher(self):
        if getattr(self, "_artfetcher", None) is None:
            from .art_fetch import ArtFetcher
            self._artfetcher = ArtFetcher(self._art_service(), self)
        return self._artfetcher

    def _catalog_names(self) -> list[str]:
        if getattr(self, "_catalog", None) is None:
            try:
                self._catalog = self._art_service().db.all_display_names()
            except Exception:
                self._catalog = []
        return self._catalog

    def _request_art(self, name: str) -> None:
        if not name or name in (PLACEHOLDER_OPP, WCS_OPP_DECK):
            return
        try:
            self._art_fetcher().request(name)
        except Exception:
            pass
