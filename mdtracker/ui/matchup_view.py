"""매치업 — 내 덱 드롭다운 + 상대 덱별 카드 그리드.

stats.matchup_matrix()에서 선택한 내 덱 행만 추출해
표본 내림차순(자주 만난 상대 먼저)으로 카드를 배치한다.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QScrollArea, QVBoxLayout, QWidget,
)

from .. import stats
from ..styles.theme import BORDER, PANEL, TEXT2
from .labels import fmt_pct

_COLS = 4
_CARD_W = 160
_CARD_H = 96


def _heat(win_rate) -> QColor:
    if win_rate is None:
        return QColor(48, 54, 61)
    if win_rate < 0.5:
        t = win_rate / 0.5
        return QColor(200, int(60 + 108 * t), 60)
    t = (win_rate - 0.5) / 0.5
    return QColor(int(200 - 140 * t), int(168 + 32 * t), 60)


class _MatchupCard(QFrame):
    """상대 덱 하나의 승률 카드."""

    def __init__(self, opp_deck: str, cell: dict, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(_CARD_W, _CARD_H)
        bg = _heat(cell["win_rate"]).name()
        self.setStyleSheet(
            f"QFrame {{ background-color: {bg}; border-radius: 8px; border: none; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        text_color = "#111111"

        name_lbl = QLabel(opp_deck)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet(
            f"color: {text_color}; font-size: 11px; font-weight: 600; "
            "background: transparent; border: none;"
        )

        rate_lbl = QLabel(fmt_pct(cell["win_rate"]))
        rate_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rate_lbl.setStyleSheet(
            f"color: {text_color}; font-size: 20px; font-weight: 700; "
            "background: transparent; border: none;"
        )

        detail_lbl = QLabel(f"{cell['wins']}승 {cell['losses']}패 · {cell['n']}전")
        detail_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_lbl.setStyleSheet(
            f"color: {text_color}; font-size: 10px; "
            "background: transparent; border: none;"
        )

        layout.addWidget(name_lbl)
        layout.addWidget(rate_lbl)
        layout.addWidget(detail_lbl)


class MatchupView(QWidget):
    def __init__(self, db, matches_provider=None) -> None:
        super().__init__()
        self.db = db
        # 대시보드 공통 필터를 거친 list[Match] 공급자 (기본: 전체)
        self._matches = matches_provider or db.matches.all
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── 상단 바: 내 덱 선택 ──────────────────────────────────────
        bar = QHBoxLayout()
        lbl = QLabel("내 덱")
        lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        bar.addWidget(lbl)
        self._deck_combo = QComboBox()
        self._deck_combo.setMinimumWidth(180)
        self._deck_combo.currentTextChanged.connect(self._render_cards)
        bar.addWidget(self._deck_combo)
        bar.addStretch()
        root.addLayout(bar)

        # ── 스크롤 카드 그리드 ──────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setSpacing(10)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._scroll.setWidget(self._grid_widget)

        # ── 안내 문구 (데이터 없을 때) ──────────────────────────────
        self._empty_lbl = QLabel()
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 13px;")
        self._empty_lbl.hide()

        root.addWidget(self._scroll, 1)
        root.addWidget(self._empty_lbl, 1)

    def _clear_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if w := item.widget():
                w.deleteLater()

    def _show_empty(self, msg: str) -> None:
        self._clear_grid()
        self._scroll.hide()
        self._empty_lbl.setText(msg)
        self._empty_lbl.show()

    def _render_cards(self, _: str = "") -> None:
        my_deck = self._deck_combo.currentText()
        if not my_deck:
            self._show_empty("덱 관리 탭에서 '내 덱'으로 등록된 덱이 없습니다.")
            return

        mm = stats.matchup_matrix(self._matches())
        my_decks = mm["my_decks"]

        if my_deck not in my_decks:
            self._show_empty(f"'{my_deck}'으로 기록된 매치업이 없습니다.")
            return

        row_idx = my_decks.index(my_deck)
        opp_decks = mm["opp_decks"]
        row_cells = mm["cells"][row_idx]

        entries = [
            (opp_decks[j], row_cells[j])
            for j in range(len(opp_decks))
            if row_cells[j]["n"] > 0
        ]
        entries.sort(key=lambda x: x[1]["n"], reverse=True)

        if not entries:
            self._show_empty(f"'{my_deck}'으로 기록된 매치업이 없습니다.")
            return

        self._clear_grid()
        self._empty_lbl.hide()
        self._scroll.show()

        cols = self._cols_for_width()
        for idx, (opp, cell) in enumerate(entries):
            card = _MatchupCard(opp, cell)
            self._grid.addWidget(card, idx // cols, idx % cols)

    def _cols_for_width(self) -> int:
        vp_w = self._scroll.viewport().width()
        cols = max(1, vp_w // (_CARD_W + 10))
        return cols

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._render_cards()

    def refresh(self) -> None:
        cur = self._deck_combo.currentText()
        self._deck_combo.blockSignals(True)
        self._deck_combo.clear()

        mine = self.db.decks.list_mine_names()
        if not mine:
            mm = stats.matchup_matrix(self._matches())
            mine = mm["my_decks"]
        self._deck_combo.addItems(mine)

        idx = self._deck_combo.findText(cur)
        self._deck_combo.setCurrentIndex(max(idx, 0))
        self._deck_combo.blockSignals(False)

        self._render_cards()
