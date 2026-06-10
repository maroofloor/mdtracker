"""추세 — 일별·누적 승률 시계열 + 현재 스트릭.

stats.trend_series()를 소비. pyqtgraph로 선 그래프를 그린다.
"""

from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from .. import stats
from ..styles.theme import BG, BORDER, TEXT2


class TrendView(QWidget):
    def __init__(self, db, matches_provider=None):
        super().__init__()
        self.db = db
        # 대시보드 공통 필터를 거친 list[Match] 공급자 (기본: 전체)
        self._matches = matches_provider or db.matches.all
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        self.streak_lbl = QLabel()
        self.streak_lbl.setStyleSheet("font-weight:bold;")
        layout.addWidget(self.streak_lbl)

        self.plot = pg.PlotWidget()
        self.plot.setBackground(BG)
        self.plot.setYRange(0, 100)
        self.plot.addLegend()
        self.plot.setLabel("left", "승률 (%)")
        self.plot.setLabel("bottom", "날짜")
        self.plot.showGrid(x=False, y=True, alpha=0.3)
        for axis in ("left", "bottom"):
            ax = self.plot.getAxis(axis)
            ax.setPen(pg.mkPen(BORDER))
            ax.setTextPen(pg.mkPen(TEXT2))
        layout.addWidget(self.plot)

    def refresh(self) -> None:
        t = stats.trend_series(self._matches())
        points = t["points"]
        self.plot.clear()
        if points:
            xs = list(range(len(points)))
            cumulative = [(p["cumulative_win_rate"] or 0) * 100 for p in points]
            daily = [(p["win_rate"] or 0) * 100 for p in points]
            self.plot.plot(xs, cumulative, name="누적 승률",
                           pen=pg.mkPen("#1565c0", width=2.5))
            self.plot.plot(xs, daily, name="일별 승률",
                           pen=pg.mkPen("#cccccc", width=1.5),
                           symbol="o", symbolSize=5, symbolBrush="#e57373")
            self.plot.getAxis("bottom").setTicks(
                [[(i, points[i]["date"][5:]) for i in xs]])

        streak = t["current_streak"]
        if streak["type"] == "win":
            self.streak_lbl.setText(f"🔥 현재 {streak['count']}연승")
        elif streak["type"] == "loss":
            self.streak_lbl.setText(f"❄ 현재 {streak['count']}연패")
        else:
            self.streak_lbl.setText("기록 없음")
