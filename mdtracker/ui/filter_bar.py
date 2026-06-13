"""공통 필터바 — 기간·덱·타입·결과·선후공·코인토스 조건 선택 위젯.

기록 탭과 대시보드가 공유한다. 실제 필터링은 stats.filter_matches()
순수 함수에 위임하고, 이 위젯은 조건 UI와 changed 시그널만 담당한다.
DB 접근 없음 — 덱 목록은 set_deck_options_from(list[Match])로 주입받는다.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from .. import stats
from ..models import Match
from ..styles.theme import BORDER, PANEL, TEXT2
from .labels import COIN_LABELS, COIN_TOSS_LABELS, EVENT_LABELS, RESULT_LABELS

# (표시 라벨, period 값) — stats.FILTER_PERIODS와 대응
_PERIOD_ITEMS = [
    ("전체", "all"),
    ("오늘", "today"),
    ("최근 7일", "7d"),
    ("최근 30일", "30d"),
    ("이번 달", "month"),
]

_ALL_LABEL = "전체"


class FilterBar(QWidget):
    """조건 콤보 7개 + 초기화 버튼. 조건 변경 시 changed 시그널 발행."""

    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            f"FilterBar {{ background-color: {PANEL};"
            f"border-bottom: 1px solid {BORDER}; }}")
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._combos: list[QComboBox] = []
        self.period = self._add_combo(
            layout, "기간", _PERIOD_ITEMS, width=90)
        self.my_deck = self._add_combo(
            layout, "내 덱", [(_ALL_LABEL, None)], width=120)
        self.opp_deck = self._add_combo(
            layout, "상대 덱", [(_ALL_LABEL, None)], width=120)
        self.event = self._add_combo(
            layout, "타입", self._with_all(EVENT_LABELS), width=80)
        self.result = self._add_combo(
            layout, "결과", self._with_all(RESULT_LABELS), width=68)
        self.coin = self._add_combo(
            layout, "선/후공", self._with_all(COIN_LABELS), width=72)
        self.toss = self._add_combo(
            layout, "토스", self._with_all(COIN_TOSS_LABELS), width=64)

        self.reset_btn = QPushButton("초기화")
        self.reset_btn.setFixedHeight(24)
        self.reset_btn.clicked.connect(self.reset)
        layout.addWidget(self.reset_btn)
        layout.addStretch()

    # ── 구성 헬퍼 ────────────────────────────────────────────────

    @staticmethod
    def _with_all(label_map: dict) -> list[tuple[str, str | None]]:
        """canonical→라벨 매핑 앞에 '전체'(None)를 붙인 콤보 항목 리스트."""
        return [(_ALL_LABEL, None)] + [(lbl, v) for v, lbl in label_map.items()]

    def _add_combo(self, layout: QHBoxLayout, title: str,
                   items: list[tuple[str, str | None]],
                   width: int) -> QComboBox:
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {TEXT2}; font-size: 11px; background: transparent;"
            "border: none;")
        layout.addWidget(lbl)
        combo = QComboBox()
        combo.setFixedWidth(width)
        for label, value in items:
            combo.addItem(label, value)
        combo.currentIndexChanged.connect(self._emit_changed)
        layout.addWidget(combo)
        self._combos.append(combo)
        return combo

    def _emit_changed(self, *_) -> None:
        self.changed.emit()

    # ── 공개 API ─────────────────────────────────────────────────

    def set_deck_options_from(self, matches: Sequence[Match]) -> None:
        """기록에 등장한 덱명으로 내 덱/상대 덱 콤보를 갱신 (선택 유지)."""
        self._set_options(self.my_deck, sorted({m.my_deck for m in matches}))
        self._set_options(self.opp_deck,
                          sorted({m.opponent_deck for m in matches}))

    @staticmethod
    def _set_options(combo: QComboBox, names: list[str]) -> None:
        cur = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(_ALL_LABEL, None)
        for name in names:
            combo.addItem(name, name)
        idx = combo.findData(cur) if cur is not None else 0
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)

    def apply(self, matches: Sequence[Match]) -> list[Match]:
        """현재 조건으로 거른 list[Match] 반환 (stats.filter_matches 위임)."""
        return stats.filter_matches(
            matches,
            period=self.period.currentData(),
            my_deck=self.my_deck.currentData(),
            opponent_deck=self.opp_deck.currentData(),
            event_type=self.event.currentData(),
            result=self.result.currentData(),
            coin_result=self.coin.currentData(),
            coin_toss=self.toss.currentData(),
        )

    def is_active(self) -> bool:
        """기본값(전체)이 아닌 조건이 하나라도 있으면 True."""
        return any(c.currentIndex() != 0 for c in self._combos)

    def reset(self) -> None:
        """모든 조건을 '전체'로 되돌리고 changed를 1회 발행."""
        for combo in self._combos:
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self.changed.emit()

    def get_state(self) -> dict:
        """현재 필터 상태를 dict로 반환 (탭 간 동기화용)."""
        return {
            "period":   self.period.currentIndex(),
            "my_deck":  self.my_deck.currentData(),
            "opp_deck": self.opp_deck.currentData(),
            "event":    self.event.currentIndex(),
            "result":   self.result.currentIndex(),
            "coin":     self.coin.currentIndex(),
            "toss":     self.toss.currentIndex(),
        }

    def apply_state(self, state: dict) -> None:
        """get_state()로 얻은 dict를 적용하고 changed를 1회 발행."""
        def _set_index(combo: QComboBox, key: str) -> None:
            combo.blockSignals(True)
            combo.setCurrentIndex(state.get(key, 0))
            combo.blockSignals(False)

        def _set_data(combo: QComboBox, key: str) -> None:
            combo.blockSignals(True)
            idx = combo.findData(state.get(key))
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)

        _set_index(self.period, "period")
        _set_data(self.my_deck, "my_deck")
        _set_data(self.opp_deck, "opp_deck")
        _set_index(self.event, "event")
        _set_index(self.result, "result")
        _set_index(self.coin, "coin")
        _set_index(self.toss, "toss")
        self.changed.emit()
