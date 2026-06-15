"""pyqtgraph 차트의 테마 연동 헬퍼 — theme.active() 기준으로 색을 적용한다.

각 뷰는 테마 전환 시 refresh()에서 style_plot()을 다시 호출해 색을 갱신한다.
"""

from __future__ import annotations

import pyqtgraph as pg

from ..styles import theme


def style_plot(plot) -> None:
    """플롯 배경/축 색을 활성 테마로 맞춘다."""
    t = theme.active()
    plot.setBackground(t.bg)
    for axis in ("left", "bottom"):
        ax = plot.getAxis(axis)
        ax.setPen(pg.mkPen(t.border))
        ax.setTextPen(pg.mkPen(t.text2))


def baseline_pen():
    """50% 기준선 펜(점선)."""
    t = theme.active()
    return pg.mkPen(t.text2, width=1, style=pg.QtCore.Qt.DashLine)


def series_pens() -> tuple:
    """추세 라인용 (주, 보조) 색 — 테마 강조색 기반."""
    t = theme.active()
    return t.accent, t.second


def distribution_palette() -> list[str]:
    """상대 덱 분포 도넛/막대용 다색 팔레트(앞쪽 항목은 테마색)."""
    t = theme.active()
    return [t.accent, t.second, t.win, "#eab308", "#a855f7",
            "#06b6d4", "#ec4899", "#84cc16", t.lose, "#14b8a6"]
