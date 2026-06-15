"""OCR 감지 결과 확인 패널 — RecordView 우측에 오버레이.

인식 결과를 결과 색 배너 + 상대 덱 카드 아트 미리보기로 보여주고,
사용자가 1클릭으로 확인하거나 상대 덱/결과를 교정한다.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mdtracker.styles import theme
from mdtracker.styles.theme import ACCENT, BORDER, PANEL, SURFACE, TEXT, TEXT2

from .completer import make_deck_completer
from .deck_avatar import DeckAvatar
from .labels import RESULT_LABELS, combo_value, fill_combo, select_value


class OcrPanel(QWidget):
    """OCR 감지 매치를 보여주고 사용자가 확인/취소할 수 있는 패널.

    결과 미상('unknown') 발행 시 승/패/무 선택 콤보로 사용자가 결과를 교정한다 (설계 §6).
    """

    confirmed = Signal()   # 확인 → RecordView가 상대 덱·결과 업데이트 처리
    dismissed = Signal()   # 취소

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(300)
        self.setStyleSheet(
            f"background-color: {PANEL}; border-left: 2px solid {ACCENT};"
        )
        self._art_resolver: Optional[Callable[[str], Optional[str]]] = None
        self._art_request: Optional[Callable[[str], None]] = None
        self.hide()
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("OCR 감지됨")
        title.setStyleSheet("font-weight: bold; font-size: 13px; border: none;")
        layout.addWidget(title)

        # ── 결과 색 배너 ──────────────────────────────────────────
        self._result_banner = QLabel("—")
        self._result_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_banner.setMinimumHeight(40)
        layout.addWidget(self._result_banner)

        # ── 상대 덱 카드 아트 미리보기 ────────────────────────────
        avatar_row = QHBoxLayout()
        avatar_row.addStretch()
        self._opp_avatar = DeckAvatar("", None, size=72)
        avatar_row.addWidget(self._opp_avatar)
        avatar_row.addStretch()
        layout.addLayout(avatar_row)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        self._lbl_coin   = QLabel("—")
        self._lbl_turn   = QLabel("—")

        combo_style = (
            f"QComboBox {{ background: {SURFACE}; color: {TEXT};"
            f"border: 1px solid {BORDER}; border-radius: 4px; padding: 3px 6px; }}"
            f"QComboBox QAbstractItemView {{ background: {PANEL}; color: {TEXT};"
            f"border: 1px solid {BORDER}; }}")
        self._result_combo = QComboBox()
        fill_combo(self._result_combo, RESULT_LABELS)
        self._result_combo.setStyleSheet(combo_style)
        self._result_combo.currentIndexChanged.connect(
            self._update_result_banner)
        result_lbl = QLabel("결과")
        result_lbl.setStyleSheet(f"color: {TEXT2}; border: none;")
        form.addRow(result_lbl, self._result_combo)

        for label, widget in [
            ("코인",    self._lbl_coin),
            ("선/후공", self._lbl_turn),
        ]:
            row_lbl = QLabel(label)
            row_lbl.setStyleSheet(f"color: {TEXT2}; border: none;")
            widget.setStyleSheet("border: none;")
            form.addRow(row_lbl, widget)

        # 상대 덱 입력 콤보박스
        opp_lbl = QLabel("상대 덱")
        opp_lbl.setStyleSheet(f"color: {TEXT2}; border: none;")
        self._opp_combo = QComboBox()
        self._opp_combo.setEditable(True)
        self._opp_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._opp_combo.lineEdit().setPlaceholderText("덱 이름 입력...")
        self._opp_combo.setStyleSheet(
            f"QComboBox {{ background: {SURFACE}; color: {TEXT};"
            f"border: 1px solid {BORDER}; border-radius: 4px; padding: 3px 6px; }}"
            f"QComboBox QAbstractItemView {{ background: {PANEL}; color: {TEXT};"
            f"border: 1px solid {BORDER}; }}")
        self._opp_combo.currentTextChanged.connect(self._update_opp_art)
        form.addRow(opp_lbl, self._opp_combo)

        layout.addLayout(form)
        layout.addStretch()

        btn_row = QHBoxLayout()
        self._btn_confirm = QPushButton("확인")
        self._btn_dismiss = QPushButton("취소")
        self._btn_confirm.setStyleSheet(
            f"background-color: {ACCENT}; color: #fff; border: none;"
            "padding: 6px 14px; border-radius: 4px;"
        )
        btn_row.addWidget(self._btn_confirm)
        btn_row.addWidget(self._btn_dismiss)
        layout.addLayout(btn_row)

        self._btn_confirm.clicked.connect(self._on_confirm)
        self._btn_dismiss.clicked.connect(self._on_dismiss)
        self._update_result_banner()

    # ── 아트 지원 주입 (RecordView가 1회 설정) ────────────────────────
    def set_art_support(self, resolver, request=None,
                        catalog: list[str] | None = None) -> None:
        self._art_resolver = resolver
        self._art_request = request
        if catalog:
            self._opp_combo.setCompleter(make_deck_completer(catalog, self))

    def _update_result_banner(self, *_) -> None:
        val = combo_value(self._result_combo) or "unknown"
        t = theme.active()
        colors = {"win": t.win, "loss": t.lose, "draw": t.draw,
                  "unknown": "#eab308"}
        bg = colors.get(val, "#eab308")
        text = RESULT_LABELS.get(val, "미상")
        self._result_banner.setText(text)
        self._result_banner.setStyleSheet(
            f"background-color: {bg}; color: #0b0f19; border-radius: 8px;"
            "font-size: 18px; font-weight: 800; border: none;")

    def _update_opp_art(self, text: str) -> None:
        name = (text or "").strip()
        self._opp_avatar.set_name(name)
        path = (self._art_resolver(name)
                if (self._art_resolver and name) else None)
        self._opp_avatar.set_image(path)
        if name and not path and self._art_request:
            self._art_request(name)

    def populate(self, result: str, coin: str, turn: str,
                 deck_names: list[str] | None = None) -> None:
        """result는 canonical 값('win'|'loss'|'draw'|'unknown')."""
        select_value(self._result_combo, result or "unknown")
        self._update_result_banner()
        self._lbl_coin.setText(coin or "—")
        self._lbl_turn.setText(turn or "—")
        self._opp_combo.clear()
        self._opp_combo.addItem("")
        if deck_names:
            self._opp_combo.addItems(deck_names)
        self._opp_combo.setCurrentIndex(0)
        self._update_opp_art("")

    @property
    def opp_deck_text(self) -> str:
        return self._opp_combo.currentText().strip()

    @property
    def result_value(self) -> str | None:
        """사용자가 선택한 결과 canonical 값 ('win'|'loss'|'draw'|'unknown')."""
        return combo_value(self._result_combo)

    def _on_confirm(self) -> None:
        self.confirmed.emit()
        self.hide()

    def _on_dismiss(self) -> None:
        self.dismissed.emit()
        self.hide()
