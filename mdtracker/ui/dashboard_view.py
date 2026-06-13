"""대시보드 — 공통 필터바 + 서브탭 4개: 요약(KPI) / 매치업 / 메타 / 추세.

상단 FilterBar의 조건이 서브탭 4개에 동시에 적용된다.
각 서브탭은 matches_provider(필터 통과한 list[Match])만 소비한다.
"""

from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from ..models import Match
from .filter_bar import FilterBar
from .kpi_view import KpiView
from .matchup_view import MatchupView
from .meta_view import MetaView
from .trend_view import TrendView


class DashboardView(QWidget):
    def __init__(self, db) -> None:
        super().__init__()
        self.db = db

        self.filter_bar = FilterBar()

        self.kpi      = KpiView(db, matches_provider=self._filtered)
        self._matchup = MatchupView(db, matches_provider=self._filtered)
        self._meta    = MetaView(db, matches_provider=self._filtered)
        self._trend   = TrendView(db, matches_provider=self._filtered)

        self.subtabs = QTabWidget()
        self.subtabs.addTab(self.kpi,      "요약")
        self.subtabs.addTab(self._matchup, "매치업")
        self.subtabs.addTab(self._meta,    "메타")
        self.subtabs.addTab(self._trend,   "추세")
        self.subtabs.currentChanged.connect(self._on_subtab_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.filter_bar)
        layout.addWidget(self.subtabs)

        self.filter_bar.changed.connect(self._on_filter_changed)
        self._update_filter_options()

    def _filtered(self) -> list[Match]:
        """공통 필터를 거친 전체 매치 — 서브탭의 matches_provider."""
        return self.filter_bar.apply(self.db.matches.all())

    def _update_filter_options(self) -> None:
        self.filter_bar.set_deck_options_from(self.db.matches.all())

    def refresh(self) -> None:
        """모든 서브탭을 갱신한다 (data_changed 수신 시 호출)."""
        self._update_filter_options()
        for i in range(self.subtabs.count()):
            widget = self.subtabs.widget(i)
            if hasattr(widget, "refresh"):
                widget.refresh()

    def _on_filter_changed(self) -> None:
        """필터 조건 변경 — 보이는 서브탭만 즉시 갱신 (나머지는 탭 전환 시)."""
        widget = self.subtabs.currentWidget()
        if hasattr(widget, "refresh"):
            widget.refresh()

    def _on_subtab_changed(self, index: int) -> None:
        widget = self.subtabs.widget(index)
        if hasattr(widget, "refresh"):
            widget.refresh()
