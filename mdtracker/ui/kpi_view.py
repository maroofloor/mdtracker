"""KPI 요약 뷰 — 승률 카드 그리드 + 그라디언트 바 + 내 덱별 승률 테이블."""

from __future__ import annotations

from datetime import date, datetime, timezone

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import stats
from ..styles.theme import (
    ACCENT, BG, BORDER, LOSE, PANEL, SURFACE, SURFACE2, TEXT, TEXT2, WIN,
)
from .labels import fmt_pct


def _line(t: dict) -> str:
    return f"{fmt_pct(t['win_rate'])}  ({t['wins']}승 {t['losses']}패 · {t['n']}전)"


def _streak_text(streak: dict) -> str:
    if not streak["type"]:
        return "—"
    icon = "🔥" if streak["type"] == "win" else "❄"
    label = "연승" if streak["type"] == "win" else "연패"
    return f"{icon} {streak['count']}{label}"


class WinRateBar(QWidget):
    """그라디언트 승률 바 — 빨강(0%) → 노랑(50%) → 초록(100%)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rate: float = 0.0
        self.setFixedHeight(6)

    def set_rate(self, rate: float) -> None:
        self._rate = max(0.0, min(1.0, rate))
        self.update()

    def paintEvent(self, _) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()

        # 배경
        painter.setBrush(QColor(SURFACE2))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)

        # 그라디언트 채움
        fill_w = w * self._rate
        if fill_w > 0:
            grad = QLinearGradient(0, 0, fill_w, 0)
            grad.setColorAt(0.0, QColor("#ef4444"))
            grad.setColorAt(0.5, QColor("#eab308"))
            grad.setColorAt(1.0, QColor("#22c55e"))
            painter.setBrush(grad)
            painter.drawRoundedRect(QRectF(0, 0, fill_w, h), h / 2, h / 2)


class KpiCard(QWidget):
    """단일 기간 승률 카드."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: {BG}; border-bottom: 1px solid {BORDER};"
            "border-radius: 8px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        self._title = QLabel(title)
        self._title.setStyleSheet(
            f"color: {TEXT2}; font-size: 11px; font-weight: 600; border: none;")
        layout.addWidget(self._title)

        self._rate_lbl = QLabel("—")
        self._rate_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 28px; font-weight: 700; border: none;")
        layout.addWidget(self._rate_lbl)

        self._bar = WinRateBar()
        layout.addWidget(self._bar)

        self._detail = QLabel("—")
        self._detail.setStyleSheet(
            f"color: {TEXT2}; font-size: 11px; border: none;")
        layout.addWidget(self._detail)

        self._streak = QLabel("—")
        self._streak.setStyleSheet(
            f"color: {TEXT2}; font-size: 11px; border: none;")
        layout.addWidget(self._streak)

    def update_data(self, s: dict, streak: dict) -> None:
        ov = s["overall"]
        wr = ov["win_rate"] or 0.0
        color = WIN if wr >= 0.5 else LOSE
        self._rate_lbl.setText(fmt_pct(wr))
        self._rate_lbl.setStyleSheet(
            f"color: {color}; font-size: 28px; font-weight: 700; border: none;")
        self._bar.set_rate(wr)
        self._detail.setText(
            f"{ov['wins']}승  {ov['losses']}패  ·  {ov['n']}전")
        self._streak.setText(_streak_text(streak))


class KpiView(QWidget):
    """대시보드 요약 탭 — KPI 카드 3개 + 선/후공 + 덱별 승률."""

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
        root.setSpacing(12)

        # ── KPI 카드 3열 ─────────────────────────────────────────
        card_row = QHBoxLayout()
        card_row.setSpacing(10)
        self._cards: list[KpiCard] = []
        for title in ["전체", "오늘"]:
            card = KpiCard(title)
            card_row.addWidget(card)
            self._cards.append(card)
        root.addLayout(card_row)

        # ── 전체 승률 요약 라인 ──────────────────────────────────
        self.overall_lbl = QLabel()
        self.overall_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 13px; font-weight: 600; padding: 4px 0;")
        root.addWidget(self.overall_lbl)

        # ── 선/후공 · 코인 행 ─────────────────────────────────────
        coin_row = QHBoxLayout()
        coin_row.setSpacing(8)
        self._coin_widgets: dict[str, QLabel] = {}
        for label, key in [("선공", "first"), ("후공", "second"),
                            ("토스 승", "toss_win"), ("토스 패", "toss_loss")]:
            box = QWidget()
            box.setStyleSheet(
                f"background:{SURFACE}; border:1px solid {BORDER};"
                f"border-radius:8px;")
            bl = QVBoxLayout(box)
            bl.setContentsMargins(12, 8, 12, 8)
            bl.setSpacing(2)
            title_lbl = QLabel(label)
            title_lbl.setStyleSheet(
                f"color:{TEXT2}; font-size:10px; border:none;")
            val_lbl = QLabel("—")
            val_lbl.setStyleSheet(
                f"color:{TEXT}; font-size:15px; font-weight:700; border:none;")
            bl.addWidget(title_lbl)
            bl.addWidget(val_lbl)
            coin_row.addWidget(box)
            self._coin_widgets[key] = val_lbl
        self.choice_lbl = QLabel()
        self.choice_lbl.setStyleSheet(
            f"color:{TEXT2}; font-size:11px; border:none;")
        root.addLayout(coin_row)
        root.addWidget(self.choice_lbl)

        # ── 내 덱별 승률 테이블 ──────────────────────────────────
        deck_title = QLabel("내 덱별 승률")
        deck_title.setStyleSheet(
            f"color:{TEXT2}; font-size:15px; font-weight:600;")
        root.addWidget(deck_title)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["덱", "승", "패", "승률", "표본"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet(
            f"QTableWidget {{ background: {PANEL}; }}"
            f"QTableWidget::item {{ padding: 6px 10px; }}"
            f"QHeaderView::section {{ background: {SURFACE}; color: {TEXT2};"
            f"font-size:10px; }}")
        root.addWidget(self.table, 1)

    # ── internal helpers ─────────────────────────────────────────

    def _period_matches(self) -> tuple[list, list]:
        all_matches = self._matches()
        today_prefix = date.today().isoformat()
        today = [m for m in all_matches if m.played_at.startswith(today_prefix)]
        return all_matches, today

    def refresh(self) -> None:
        all_matches, today = self._period_matches()

        for card, ms in zip(self._cards, [all_matches, today]):
            s = stats.win_rate_summary(ms)
            t = stats.trend_series(ms)
            card.update_data(s, t["current_streak"])
            if card is self._cards[0]:
                s_all = s

        self.overall_lbl.setText(f"전체  {_line(s_all['overall'])}")

        def _pct(d: dict) -> str:
            return fmt_pct(d["win_rate"]) if d["n"] else "—"

        self._coin_widgets["first"].setText(
            _pct(s_all["by_coin"]["first"]))
        self._coin_widgets["second"].setText(
            _pct(s_all["by_coin"]["second"]))
        self._coin_widgets["toss_win"].setText(
            _pct(s_all["by_coin_toss"]["win"]))
        self._coin_widgets["toss_loss"].setText(
            _pct(s_all["by_coin_toss"]["loss"]))

        c = s_all["toss_win_choice"]
        if c["n"]:
            self.choice_lbl.setText(
                f"토스 승리 시 선공 선택: {fmt_pct(c['first'] / c['n'])} "
                f"({c['first']}/{c['n']})")
        else:
            self.choice_lbl.setText("토스 승리 시 선공 선택: —")

        decks = sorted(s_all["by_my_deck"].items(),
                       key=lambda kv: kv[1]["n"], reverse=True)
        self.table.setRowCount(len(decks))
        for row, (deck, d) in enumerate(decks):
            wr = d["win_rate"] or 0.0
            wr_color = WIN if wr >= 0.5 else LOSE
            values = [deck, str(d["wins"]), str(d["losses"]),
                      fmt_pct(wr), str(d["n"])]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setForeground(
                    QColor(wr_color) if col == 3 else QColor(TEXT))
                item.setBackground(
                    QColor(SURFACE) if row % 2 else QColor(SURFACE2))
                if col > 0:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
