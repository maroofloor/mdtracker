"""상대 메타 — 마주친 상대 덱 분포 (테이블 + 막대/도넛).

stats.opponent_meta() / stats.meta_delta()를 소비. UI는 계산하지 않는다.
- 빈도순 / 위협 지수순 정렬 토글
- 시즌이 2개 이상이면 직전 시즌 대비 점유율 Δ 표기
- 막대 / 도넛 차트 토글, 누적 점유율로 Tier1/Tier2/기타 자동 구분
- 총 표본 < 30 이면 신뢰도 배너
"""

from __future__ import annotations

import math

import pyqtgraph as pg
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .. import stats
from ..styles.theme import (
    ACCENT, BG, BORDER, LOSE, PANEL, TEXT, TEXT2, WIN,
)
from .labels import fmt_pct

MIN_RELIABLE_N = 30
TIER1_CUM = 0.50
TIER2_CUM = 0.80

# 도넛 색 팔레트
_PALETTE = ["#4361ee", "#f97316", "#22c55e", "#eab308", "#a855f7",
            "#06b6d4", "#ec4899", "#84cc16", "#f43f5e", "#14b8a6"]


def _wr_color(win_rate) -> str:
    if win_rate is None:
        return TEXT2
    return WIN if win_rate >= 0.5 else LOSE


def _tier_of(cum_share: float) -> str:
    if cum_share <= TIER1_CUM:
        return "Tier1"
    if cum_share <= TIER2_CUM:
        return "Tier2"
    return "기타"


def _with_tiers(dist: list) -> list:
    """share 내림차순 분포에 누적 share 기반 티어 라벨을 붙인다."""
    out = []
    cum = 0.0
    for d in dist:
        cum += d["share"]
        out.append({**d, "tier": _tier_of(cum)})
    return out


class _DonutWidget(QWidget):
    """점유율 도넛 — QPainter로 직접 그린다(상위 항목 + 기타 묶음)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._segments: list[tuple] = []   # (label, share, color)
        self.setMinimumSize(220, 220)

    def set_data(self, dist: list) -> None:
        segs = []
        for i, d in enumerate(dist[:len(_PALETTE) - 1]):
            segs.append((d["deck"], d["share"], _PALETTE[i % len(_PALETTE)]))
        rest = sum(d["share"] for d in dist[len(_PALETTE) - 1:])
        if rest > 0:
            segs.append(("기타", rest, "#475569"))
        self._segments = segs
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        size = min(w, h) - 20
        if size <= 0 or not self._segments:
            return
        rect = QRectF((w - size) / 2, (h - size) / 2, size, size)
        start = 90 * 16                       # 12시 방향에서 시작
        for _label, share, color in self._segments:
            span = -int(round(share * 360 * 16))
            p.setBrush(QColor(color))
            p.setPen(Qt.NoPen)
            p.drawPie(rect, start, span)
            start += span
        # 가운데 구멍
        hole = size * 0.55
        p.setBrush(QColor(BG))
        p.drawEllipse(QRectF((w - hole) / 2, (h - hole) / 2, hole, hole))


class MetaView(QWidget):
    def __init__(self, db, matches_provider=None):
        super().__init__()
        self.db = db
        self._matches = matches_provider or db.matches.all
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # ── 상단 바 ───────────────────────────────────────────────
        bar = QHBoxLayout()
        title = QLabel("상대 덱 분포")
        title.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 600;")
        bar.addWidget(title)
        bar.addStretch()
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(["빈도순", "위협 지수순"])
        self._sort_combo.currentIndexChanged.connect(self.refresh)
        bar.addWidget(self._sort_combo)
        self._chart_toggle = QPushButton("도넛 보기")
        self._chart_toggle.setCheckable(True)
        self._chart_toggle.toggled.connect(self._on_chart_toggled)
        bar.addWidget(self._chart_toggle)
        root.addLayout(bar)

        # ── 표본 부족 배너 ────────────────────────────────────────
        self._banner = QLabel("⚠ 표본 부족 — 분포 신뢰도 낮음")
        self._banner.setStyleSheet(
            "color: #fbbf24; font-size: 12px; font-weight: 600; "
            f"background: {PANEL}; border: 1px solid {BORDER}; "
            "border-radius: 6px; padding: 6px 10px;")
        self._banner.hide()
        root.addWidget(self._banner)

        body = QHBoxLayout()
        # 표
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["상대 덱", "횟수", "비율", "내 승률", "Δ점유율"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        body.addWidget(self.table, 1)

        # 막대 (pyqtgraph)
        self.plot = pg.PlotWidget()
        self.plot.setBackground(BG)
        for axis in ("left", "bottom"):
            ax = self.plot.getAxis(axis)
            ax.setPen(pg.mkPen(BORDER))
            ax.setTextPen(pg.mkPen(TEXT2))
        body.addWidget(self.plot, 1)

        # 도넛
        self.donut = _DonutWidget()
        self.donut.hide()
        body.addWidget(self.donut, 1)
        root.addLayout(body, 1)

    def _on_chart_toggled(self, donut: bool) -> None:
        self._chart_toggle.setText("막대 보기" if donut else "도넛 보기")
        self.plot.setVisible(not donut)
        self.donut.setVisible(donut)
        self.refresh()

    def _seasons(self) -> list:
        return sorted({m.season for m in self._matches() if m.season})

    def refresh(self) -> None:
        meta = stats.opponent_meta(self._matches())
        dist = list(meta["distribution"])          # 기본 share/count 내림차순
        total = meta["total"]
        self._banner.setVisible(0 < total < MIN_RELIABLE_N)

        # 시즌 델타 (시즌 2개 이상일 때만)
        seasons = self._seasons()
        delta_map: dict = {}
        if len(seasons) >= 2:
            delta_map = stats.meta_delta(
                self._matches(), season=seasons[-1], prev_season=seasons[-2])
        self.table.setColumnHidden(4, not delta_map)

        threat_sort = self._sort_combo.currentIndex() == 1
        tiered = _with_tiers(dist)                  # 티어는 빈도(=share) 기준
        if threat_sort:
            tiered.sort(key=lambda d: d["threat"], reverse=True)

        # ── 표 ────────────────────────────────────────────────────
        self.table.setRowCount(len(tiered))
        for row, d in enumerate(tiered):
            dm = delta_map.get(d["deck"])
            if dm:
                dv = dm["delta"] * 100
                arrow = "▲" if dv >= 0 else "▼"
                delta_str = f"{arrow} {abs(dv):.1f}%p"
            else:
                delta_str = "—"
            wr_str = fmt_pct(d["win_rate"]) if (d["wins"] + d["losses"]) else "—"
            values = [f"{d['deck']}  ·{d['tier']}", str(d["count"]),
                      f"{d['share'] * 100:.1f}%", wr_str, delta_str]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                if col == 3:
                    item.setForeground(QColor(_wr_color(d["win_rate"])))
                if col > 0:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

        # ── 차트 ──────────────────────────────────────────────────
        if self._chart_toggle.isChecked():
            self.donut.set_data(dist)
            return

        self.plot.clear()
        if not tiered:
            return
        ys = list(range(len(tiered)))
        if threat_sort:
            widths = [d["threat"] for d in tiered]
            brushes = [QColor(_wr_color(d["win_rate"])) for d in tiered]
            self.plot.setLabel("bottom", "위협 지수")
            tick_labels = [
                (i, f"{tiered[i]['deck']}  {tiered[i]['share']*100:.0f}% 출현 · "
                    f"승 {fmt_pct(tiered[i]['win_rate'])}")
                for i in ys]
        else:
            widths = [d["count"] for d in tiered]
            brushes = [QColor(ACCENT) for _ in tiered]
            self.plot.setLabel("bottom", "횟수")
            tick_labels = [(i, tiered[i]["deck"]) for i in ys]
        bars = pg.BarGraphItem(x0=0, y=ys, height=0.6, width=widths,
                               brushes=brushes)
        self.plot.addItem(bars)
        self.plot.getAxis("left").setTicks([tick_labels])
        if widths and max(widths) > 0:
            self.plot.setXRange(0, max(widths))
