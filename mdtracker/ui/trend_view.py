"""추세 — 일/주별·누적·롤링 승률 + 랭크 진척(별도 트랙).

stats.trend_series()를 소비. pyqtgraph로 그린다. UI는 계산하지 않는다.
- X축 토글: 날짜 / 게임(누적+롤링 이동평균)
- 50% 기준선(점선)
- 점 호버 시 그 구간 전적 툴팁
- 집계 단위 토글: 일 / 주(ISO)
- 랭크 변화는 수직선 대신 별도 계단형 미니 플롯
"""

from __future__ import annotations

from datetime import date as _date

import pyqtgraph as pg
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from .. import stats
from ..styles import theme
from ..styles.theme import BG, BORDER, TEXT2
from .advanced_bar import AdvancedBar
from .chart_theme import baseline_pen, series_pens, style_plot

ROLL_WINDOW = 20


class TrendView(QWidget):
    def __init__(self, db, matches_provider=None):
        super().__init__()
        self.db = db
        self._matches = matches_provider or db.matches.all
        theme.theme_notifier.changed.connect(lambda *_: self.refresh())
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)

        # ── 상단 바 ───────────────────────────────────────────────
        bar = QHBoxLayout()
        self.streak_lbl = QLabel()
        self.streak_lbl.setStyleSheet("font-weight:bold;")
        bar.addWidget(self.streak_lbl)
        bar.addStretch()

        # 부차 컨트롤은 '고급'으로 접는다(삭제 아님): 집계(일/주)·게임 축
        self._adv = AdvancedBar()
        self._adv.add_label("집계")
        self._bucket_combo = QComboBox()
        self._bucket_combo.addItems(["일", "주"])
        self._bucket_combo.currentIndexChanged.connect(self.refresh)
        self._adv.add_widget(self._bucket_combo)
        self._axis_toggle = QPushButton("게임 축")
        self._axis_toggle.setCheckable(True)
        self._axis_toggle.toggled.connect(self._on_axis_toggled)
        self._adv.add_widget(self._axis_toggle)
        bar.addWidget(self._adv)
        layout.addLayout(bar)

        # ── 승률 플롯 ─────────────────────────────────────────────
        self.plot = pg.PlotWidget()
        self.plot.setBackground(BG)
        self.plot.setYRange(0, 100)
        self.plot.addLegend()
        self.plot.setLabel("left", "승률 (%)")
        self.plot.setLabel("bottom", "날짜")
        self.plot.showGrid(x=False, y=True, alpha=0.3)
        self._style_axes(self.plot)
        layout.addWidget(self.plot)

        # 50% 기준선 (한 번만 생성, clear와 무관하게 유지)
        self._baseline = pg.InfiniteLine(
            pos=50, angle=0,
            pen=pg.mkPen("#94a3b8", width=1, style=pg.QtCore.Qt.DashLine))
        self.plot.addItem(self._baseline)

        # ── 랭크 진척(계단형) 미니 플롯 ───────────────────────────
        self.rank_plot = pg.PlotWidget()
        self.rank_plot.setBackground(BG)
        self.rank_plot.setMaximumHeight(90)
        self.rank_plot.setLabel("left", "랭크")
        self.rank_plot.showGrid(x=False, y=True, alpha=0.2)
        self._style_axes(self.rank_plot)
        self.rank_plot.getAxis("bottom").hide()
        self.rank_plot.setXLink(self.plot)
        layout.addWidget(self.rank_plot)

        # ── 게임 수 바 (날짜 모드) ────────────────────────────────
        self.count_plot = pg.PlotWidget()
        self.count_plot.setBackground(BG)
        self.count_plot.setMaximumHeight(90)
        self.count_plot.setLabel("left", "게임 수")
        self.count_plot.showGrid(x=False, y=True, alpha=0.3)
        self._style_axes(self.count_plot)
        self.count_plot.getAxis("bottom").hide()
        self.count_plot.setXLink(self.plot)
        layout.addWidget(self.count_plot)

    @staticmethod
    def _style_axes(plot) -> None:
        for axis in ("left", "bottom"):
            ax = plot.getAxis(axis)
            ax.setPen(pg.mkPen(BORDER))
            ax.setTextPen(pg.mkPen(TEXT2))

    def _on_axis_toggled(self, game: bool) -> None:
        self._axis_toggle.setText("날짜 축" if game else "게임 축")
        self._bucket_combo.setEnabled(not game)
        self.refresh()

    # ── 렌더 ─────────────────────────────────────────────────────
    def refresh(self) -> None:
        game_mode = self._axis_toggle.isChecked()
        bucket = "week" if self._bucket_combo.currentIndex() == 1 else "day"
        t = stats.trend_series(self._matches(), window=ROLL_WINDOW, bucket=bucket)

        self.plot.clear()
        self.plot.addItem(self._baseline)          # 기준선 재부착
        self.rank_plot.clear()
        self.count_plot.clear()

        # 테마 색 재적용 (테마 전환 시 갱신)
        for pl in (self.plot, self.rank_plot, self.count_plot):
            style_plot(pl)
        self._baseline.setPen(baseline_pen())

        if game_mode:
            self._render_game(t)
        else:
            self._render_date(t)

        self._render_rank(t, visible=not game_mode)
        self.count_plot.setVisible(not game_mode)
        self._set_streak(t["current_streak"])

    def _render_date(self, t: dict) -> None:
        self.plot.setLabel("bottom", "날짜")
        points = t["points"]
        if not points:
            return

        def _ord(p) -> int:
            try:
                return _date.fromisoformat(p["date"]).toordinal()
            except Exception:
                return 0

        xs = [_ord(p) for p in points]
        cumulative = [(p["cumulative_win_rate"] or 0) * 100 for p in points]
        daily = [(p["win_rate"] or 0) * 100 for p in points]
        main_c, _sec = series_pens()
        self.plot.plot(xs, cumulative, name="누적 승률",
                       pen=pg.mkPen(main_c, width=2.5))
        self.plot.plot(xs, daily, name="구간 승률",
                       pen=pg.mkPen(theme.active().text2, width=1.5))

        tips = []
        for p in points:
            tips.append(
                f"{p['date']}\n{p['wins']}승 {p['losses']}패 · {p['n']}전\n"
                f"승률 {self._pct(p['win_rate'])} / 누적 "
                f"{self._pct(p['cumulative_win_rate'])}")
        self._add_hover_points(xs, daily, tips, "#e57373")

        ticks = [(x, points[i]["date"][5:]) for i, x in enumerate(xs)]
        self.plot.getAxis("bottom").setTicks([ticks])

        counts = [p["n"] for p in points]
        self.count_plot.addItem(pg.BarGraphItem(
            x=xs, height=counts, width=0.7, brush=main_c, pen=pg.mkPen(None)))

    def _render_game(self, t: dict) -> None:
        self.plot.setLabel("bottom", "게임 수")
        gp = t["game_points"]
        if not gp:
            return
        xs = [g["index"] for g in gp]
        cumulative = [g["cumulative_win_rate"] * 100 for g in gp]
        rolling = [g["rolling_win_rate"] * 100 for g in gp]
        main_c, sec = series_pens()
        self.plot.plot(xs, cumulative, name="누적 승률",
                       pen=pg.mkPen(main_c, width=2.5))
        self.plot.plot(xs, rolling, name=f"롤링 {ROLL_WINDOW}전",
                       pen=pg.mkPen(sec, width=2))
        tips = [
            f"#{g['index']} {g['result']}\n누적 {self._pct(g['cumulative_win_rate'])}"
            f" / 롤링 {self._pct(g['rolling_win_rate'])}"
            for g in gp]
        self._add_hover_points(xs, rolling, tips, sec)
        self.plot.getAxis("bottom").setTicks([])     # 자동 정수 틱

    def _render_rank(self, t: dict, *, visible: bool) -> None:
        self.rank_plot.setVisible(visible)
        if not visible:
            return
        history = t.get("rank_history", [])
        # 날짜별 마지막 랭크만 유지(중복 제거), 등장 순서로 y 레벨 부여
        seen_dates: dict = {}
        for e in history:
            if e["rank_label"]:
                seen_dates[e["date"]] = e["rank_label"]
        if not seen_dates:
            return
        order: list = []
        for label in seen_dates.values():
            if label not in order:
                order.append(label)
        level = {label: i for i, label in enumerate(order)}
        xs, ys = [], []
        for d, label in sorted(seen_dates.items()):
            try:
                xs.append(_date.fromisoformat(d).toordinal())
            except Exception:
                continue
            ys.append(level[label])
        if not xs:
            return
        sec = theme.active().second
        self.rank_plot.plot(xs, ys, stepMode=False,
                            pen=pg.mkPen(sec, width=2),
                            symbol="o", symbolSize=6, symbolBrush=sec)
        self.rank_plot.getAxis("left").setTicks(
            [[(lvl, lbl) for lbl, lvl in level.items()]])

    def _add_hover_points(self, xs, ys, tips, color) -> None:
        spots = [{"pos": (x, y), "data": tip}
                 for x, y, tip in zip(xs, ys, tips)]
        scatter = pg.ScatterPlotItem(
            size=7, brush=pg.mkBrush(color), pen=pg.mkPen(None),
            hoverable=True, hoverSize=10,
            tip=lambda x, y, data: data)
        scatter.addPoints(spots)
        self.plot.addItem(scatter)

    @staticmethod
    def _pct(rate) -> str:
        return "—" if rate is None else f"{rate * 100:.1f}%"

    def _set_streak(self, streak: dict) -> None:
        if streak["type"] == "win":
            self.streak_lbl.setText(f"\U0001f525 현재 {streak['count']}연승")
        elif streak["type"] == "loss":
            self.streak_lbl.setText(f"❅ 현재 {streak['count']}연패")
        else:
            self.streak_lbl.setText("기록 없음")
