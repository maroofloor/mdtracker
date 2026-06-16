"""매치업 — 내 덱 드롭다운 + 상대 덱별 카드 그리드 / 전체 히트맵.

stats.matchup_matrix()를 소비. UI는 계산하지 않고 표시·정렬만 한다.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QColor, QLinearGradient, QPainter, QPainterPath, QPixmap,
)
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from .. import stats
from ..cardart.service import CardArtService
from ..styles import theme
from ..styles.theme import LOSE, TEXT, TEXT2
from .advanced_bar import AdvancedBar
from .art_fetch import ArtFetcher
from .deck_avatar import _hue_for
from .labels import fmt_pct

_COLS = 4
_CARD_W = 160
_CARD_H = 120

# 주의 매치업 판정 최소 표본 / 표본 부족 숨김 기준
CAUTION_MIN_N = 5
SMALL_SAMPLE_N = 3


def _heat(win_rate) -> QColor:
    if win_rate is None:
        return QColor(48, 54, 61)
    if win_rate < 0.5:
        t = win_rate / 0.5
        return QColor(200, int(60 + 108 * t), 60)
    t = (win_rate - 0.5) / 0.5
    return QColor(int(200 - 140 * t), int(168 + 32 * t), 60)


def _coin_line(label: str, c: dict) -> str:
    if not c["n"]:
        return f"{label} —"
    return f"{label} {fmt_pct(c['win_rate'])} ({c['wins']}승{c['losses']}패·{c['n']}전)"


def _cell_tooltip(opp: str, cell: dict) -> str:
    """전체 + 선/후공 분리 승률 (호버 시 펼쳐 표시)."""
    return (f"{opp}\n"
            + _coin_line("전체", cell) + "\n"
            + _coin_line("선공", cell["first"]) + "\n"
            + _coin_line("후공", cell["second"]))


class _MatchupCard(QFrame):
    """상대 덱 승률 카드 — 대표 카드 아트 배경 + 어두운 오버레이 + 텍스트.

    아트가 가독성을 해치지 않도록 반투명 검정 오버레이를 깔고, 승률은
    좌측 색 띠 + % 글씨 색(승/패)으로 표시한다. 호버 시 선/후공 분리(tooltip).
    """

    def __init__(self, opp_deck: str, cell: dict, art_path=None,
                 parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(_CARD_W, _CARD_H)
        self.setToolTip(_cell_tooltip(opp_deck, cell))
        self._opp = opp_deck
        self._wr = cell["win_rate"]
        self._pix = None
        if art_path:
            pix = QPixmap(art_path)
            if not pix.isNull():
                self._pix = pix

        text_color = "#f5f5f5"
        t = theme.active()
        if cell["win_rate"] is None:
            rate_color = "#cbd5e1"
        else:
            rate_color = t.win if cell["win_rate"] >= 0.5 else t.lose

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        layout.addStretch()

        name_lbl = QLabel(opp_deck)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet(
            f"color: {text_color}; font-size: 11px; font-weight: 700; "
            "background: transparent; border: none;")

        rate_lbl = QLabel(fmt_pct(cell["win_rate"]))
        rate_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rate_lbl.setStyleSheet(
            f"color: {rate_color}; font-size: 22px; font-weight: 800; "
            "background: transparent; border: none;")

        detail_lbl = QLabel(f"{cell['wins']}승 {cell['losses']}패 · {cell['n']}전")
        detail_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_lbl.setStyleSheet(
            f"color: {text_color}; font-size: 10px; "
            "background: transparent; border: none;")

        layout.addWidget(name_lbl)
        layout.addWidget(rate_lbl)
        layout.addWidget(detail_lbl)

        # 선/후공 미니 분리 (표본 있을 때만)
        f, s = cell["first"], cell["second"]
        if f["n"] or s["n"]:
            coin_lbl = QLabel(
                f"선 {fmt_pct(f['win_rate']) if f['n'] else '—'} · "
                f"후 {fmt_pct(s['win_rate']) if s['n'] else '—'}")
            coin_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            coin_lbl.setStyleSheet(
                f"color: {text_color}; font-size: 9px; "
                "background: transparent; border: none;")
            layout.addWidget(coin_lbl)

        if cell["n"] < SMALL_SAMPLE_N:
            warn_lbl = QLabel(f"⚠ 표본 {cell['n']}건")
            warn_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            warn_lbl.setStyleSheet(
                "color: #fbbf24; font-size: 9px; font-weight: 700; "
                "background: transparent; border: none;")
            layout.addWidget(warn_lbl)
        layout.addStretch()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), 8, 8)
        p.setClipPath(path)

        # 배경: 카드 아트(cover) 또는 해시 그라디언트 폴백
        if self._pix is not None:
            scaled = self._pix.scaled(
                w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation)
            x = (scaled.width() - w) // 2
            y = (scaled.height() - h) // 2
            p.drawPixmap(0, 0, scaled, x, y, w, h)
        else:
            hue = _hue_for(self._opp)
            g = QLinearGradient(0, 0, w, h)
            g.setColorAt(0.0, QColor.fromHsl(hue, 120, 72))
            g.setColorAt(1.0, QColor.fromHsl((hue + 28) % 360, 130, 46))
            p.fillRect(QRectF(0, 0, w, h), g)

        # 가독성용 어두운 오버레이 (기본 + 하단 진한 그라디언트)
        p.fillRect(QRectF(0, 0, w, h), QColor(0, 0, 0, 115))
        og = QLinearGradient(0, 0, 0, h)
        og.setColorAt(0.0, QColor(0, 0, 0, 40))
        og.setColorAt(1.0, QColor(0, 0, 0, 175))
        p.fillRect(QRectF(0, 0, w, h), og)

        # 좌측 승률 색 띠
        p.fillRect(QRectF(0, 0, 4, h), _heat(self._wr))
        p.end()


class MatchupView(QWidget):
    def __init__(self, db, matches_provider=None) -> None:
        super().__init__()
        self.db = db
        self._matches = matches_provider or db.matches.all
        self.art = CardArtService(db.decks)
        self._fetcher = ArtFetcher(self.art, self)
        self._fetcher.fetched.connect(lambda *_: self._render())
        theme.theme_notifier.changed.connect(lambda *_: self._render())
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── 상단 바 ───────────────────────────────────────────────
        bar = QHBoxLayout()
        lbl = QLabel("내 덱")
        lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        bar.addWidget(lbl)
        self._deck_combo = QComboBox()
        self._deck_combo.setMinimumWidth(160)
        self._deck_combo.currentTextChanged.connect(self._render)
        bar.addWidget(self._deck_combo)
        bar.addStretch()

        # 부차 컨트롤은 '고급'으로 접는다(삭제 아님): 정렬·소표본 숨김
        self._adv = AdvancedBar()
        self._adv.add_label("정렬")
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(["표본순", "승률 낮은순", "승률 높은순"])
        self._sort_combo.currentIndexChanged.connect(self._render)
        self._adv.add_widget(self._sort_combo)

        self._hide_small = QCheckBox("표본 3건 미만 숨기기")
        self._hide_small.stateChanged.connect(self._render)
        self._adv.add_widget(self._hide_small)
        bar.addWidget(self._adv)
        root.addLayout(bar)

        # ── 카드 스크롤 영역 ──────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._cvbox = QVBoxLayout(self._content)
        self._cvbox.setContentsMargins(0, 0, 0, 0)
        self._cvbox.setSpacing(8)
        self._cvbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._content)
        root.addWidget(self._scroll, 1)

        # ── 빈 상태 안내 ──────────────────────────────────────────
        self._empty_lbl = QLabel()
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 13px;")
        self._empty_lbl.hide()
        root.addWidget(self._empty_lbl, 1)

    def _clear_box(self) -> None:
        while self._cvbox.count():
            item = self._cvbox.takeAt(0)
            if w := item.widget():
                w.deleteLater()

    def _show_empty(self, msg: str) -> None:
        self._clear_box()
        self._scroll.hide()
        self._empty_lbl.setText(msg)
        self._empty_lbl.show()

    def _cols(self) -> int:
        vp_w = self._scroll.viewport().width()
        return max(1, vp_w // (_CARD_W + 10))

    def _sorted_entries(self, entries: list) -> list:
        mode = self._sort_combo.currentIndex()
        if mode == 0:                                   # 표본순
            entries.sort(key=lambda x: x[1]["n"], reverse=True)
        elif mode == 1:                                 # 승률 낮은순 (None 뒤로)
            entries.sort(key=lambda x: (x[1]["win_rate"] is None,
                                        x[1]["win_rate"] if x[1]["win_rate"]
                                        is not None else 1.0))
        else:                                           # 승률 높은순 (None 뒤로)
            entries.sort(key=lambda x: (x[1]["win_rate"] is None,
                                        -(x[1]["win_rate"] or 0.0)))
        return entries

    def _add_grid_section(self, title: str, entries: list, color: str) -> None:
        if not entries:
            return
        header = QLabel(title)
        header.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: 700; "
            "padding: 2px 0;")
        self._cvbox.addWidget(header)
        grid_w = QWidget()
        grid_w.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_w)
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        cols = self._cols()
        for idx, (opp, cell) in enumerate(entries):
            self._fetcher.request(opp)
            card = _MatchupCard(opp, cell, self.art.local_path(opp))
            grid.addWidget(card, idx // cols, idx % cols)
        self._cvbox.addWidget(grid_w)

    # ── 렌더 ─────────────────────────────────────────────────────
    def _render(self, *_) -> None:
        self._render_cards()

    def _render_cards(self) -> None:
        my_deck = self._deck_combo.currentText()
        if not my_deck:
            self._show_empty("덱 관리 탭에서 '내 덱'으로 등록된 덱이 없습니다.")
            return
        mm = stats.matchup_matrix(self._matches())
        if my_deck not in mm["my_decks"]:
            self._show_empty(f"'{my_deck}'으로 기록된 매치업이 없습니다.")
            return
        row = mm["cells"][mm["my_decks"].index(my_deck)]
        opp_decks = mm["opp_decks"]
        entries = [(opp_decks[j], row[j]) for j in range(len(opp_decks))
                   if row[j]["n"] > 0]
        if self._hide_small.isChecked():
            entries = [e for e in entries if e[1]["n"] >= SMALL_SAMPLE_N]
        if not entries:
            self._show_empty(f"'{my_deck}'으로 표시할 매치업이 없습니다.")
            return

        # 주의 매치업: 표본 충분 + 승률 50% 미만, 승률 낮은 순
        caution = sorted(
            [e for e in entries
             if e[1]["n"] >= CAUTION_MIN_N and (e[1]["win_rate"] or 0) < 0.5],
            key=lambda x: x[1]["win_rate"] or 0.0)

        self._empty_lbl.hide()
        self._scroll.show()
        self._clear_box()
        self._add_grid_section(
            f"⚠ 주의 매치업 (표본 {CAUTION_MIN_N}+ · 승률 50% 미만)",
            caution, LOSE)
        self._add_grid_section("전체 매치업", self._sorted_entries(entries), TEXT)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._render_cards()

    def refresh(self) -> None:
        cur = self._deck_combo.currentText()
        self._deck_combo.blockSignals(True)
        self._deck_combo.clear()
        mine = self.db.decks.list_mine_names() if self.db else []
        if not mine:
            mine = stats.matchup_matrix(self._matches())["my_decks"]
        self._deck_combo.addItems(mine)
        idx = self._deck_combo.findText(cur)
        self._deck_combo.setCurrentIndex(max(idx, 0))
        self._deck_combo.blockSignals(False)
        self._render()
