"""상대 메타 — 마주친 상대 덱 분포 (테이블 + 가로 막대).

stats.opponent_meta()를 소비.
"""

from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
)

from .. import stats
from ..styles.theme import ACCENT, BG, BORDER, TEXT2


class MetaView(QWidget):
    def __init__(self, db, matches_provider=None):
        super().__init__()
        self.db = db
        # 대시보드 공통 필터를 거친 list[Match] 공급자 (기본: 전체)
        self._matches = matches_provider or db.matches.all
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        title = QLabel("상대 덱 분포")
        title.setStyleSheet(f"color: {TEXT2}; font-size: 15px; font-weight: 600;")
        left.addWidget(title)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["상대 덱", "횟수", "비율"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        left.addWidget(self.table)
        layout.addLayout(left, 1)

        self.plot = pg.PlotWidget()
        self.plot.setBackground(BG)
        self.plot.setLabel("bottom", "횟수")
        for axis in ("left", "bottom"):
            ax = self.plot.getAxis(axis)
            ax.setPen(pg.mkPen(BORDER))
            ax.setTextPen(pg.mkPen(TEXT2))
        layout.addWidget(self.plot, 1)

    def refresh(self) -> None:
        dist = stats.opponent_meta(self._matches())["distribution"]
        self.table.setRowCount(len(dist))
        for row, d in enumerate(dist):
            values = [d["deck"], str(d["count"]), f"{d['share'] * 100:.1f}%"]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                if col > 0:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

        self.plot.clear()
        if dist:
            ys = list(range(len(dist)))
            counts = [d["count"] for d in dist]
            bars = pg.BarGraphItem(x0=0, y=ys, height=0.6, width=counts,
                                   brush=ACCENT)
            self.plot.addItem(bars)
            self.plot.getAxis("left").setTicks(
                [[(i, dist[i]["deck"]) for i in ys]])
            self.plot.setXRange(0, max(counts))
