"""공통 필터바 — 기간·덱·타입·결과·선후공·코인토스 조건 선택 위젯.

기록 탭과 대시보드가 공유한다. 실제 필터링은 stats.filter_matches()
순수 함수에 위임하고, 이 위젯은 조건 UI와 changed 시그널만 담당한다.
DB 접근 없음 — 덱 목록은 set_deck_options_from(list[Match])로 주입받는다.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import stats
from ..models import Match
from ..styles.theme import ACCENT, BORDER, PANEL, TEXT, TEXT2
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


class FlowLayout(QLayout):
    """가로로 채우다 폭이 부족하면 다음 줄로 접는 레이아웃.

    좁은 창에서 필터 칩이 잘리지 않고 여러 줄로 자동 줄바꿈된다.
    (Qt 공식 FlowLayout 예제를 PySide6용으로 단순화.)
    """

    def __init__(self, parent=None, margin: int = 0,
                 hspacing: int = 6, vspacing: int = 4) -> None:
        super().__init__(parent)
        self._items: list = []
        self._hspace = hspacing
        self._vspace = vspacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item) -> None:        # noqa: N802 (Qt 시그니처)
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):           # noqa: N802
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):           # noqa: N802
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):          # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:    # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:    # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:     # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:            # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:         # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        m = self.contentsMargins()
        x = rect.x() + m.left()
        y = rect.y() + m.top()
        right = rect.right() - m.right()
        line_height = 0
        for item in self._items:
            w = item.sizeHint().width()
            h = item.sizeHint().height()
            next_x = x + w + self._hspace
            if next_x - self._hspace > right and line_height > 0:
                x = rect.x() + m.left()
                y = y + line_height + self._vspace
                next_x = x + w + self._hspace
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), QSize(w, h)))
            x = next_x
            line_height = max(line_height, h)
        return y + line_height - rect.y() + m.bottom()


class FilterBar(QWidget):
    """조건 콤보 7개 + 초기화 버튼. 조건 변경 시 changed 시그널 발행."""

    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            f"FilterBar {{ background-color: {PANEL};"
            f"border-bottom: 1px solid {BORDER}; }}")
        sp = QSizePolicy(QSizePolicy.Policy.Preferred,
                         QSizePolicy.Policy.Minimum)
        sp.setHeightForWidth(True)
        self.setSizePolicy(sp)

        # FilterBar = 헤더(접기 토글) + 본문(필터 칩). 본문은 접을 수 있다.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── 헤더: 접기/펼치기 토글 + (접힘 시) 적용 중 표시 ──
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        hb = QHBoxLayout(header)
        hb.setContentsMargins(8, 3, 8, 3)
        hb.setSpacing(8)
        self.toggle_btn = QPushButton("▸  필터")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setStyleSheet(
            f"QPushButton{{ color:{TEXT2}; background:transparent; border:none;"
            " font-size:12px; font-weight:600; padding:2px 4px; text-align:left;}"
            f"QPushButton:hover{{ color:{TEXT}; }}")
        self.toggle_btn.toggled.connect(self._on_toggle)
        hb.addWidget(self.toggle_btn)
        self._active_lbl = QLabel("")
        self._active_lbl.setStyleSheet(
            f"color:{ACCENT}; font-size:11px; background:transparent; border:none;")
        hb.addWidget(self._active_lbl)
        hb.addStretch(1)
        outer.addWidget(header)

        # ── 본문: 필터 칩 (좁으면 줄바꿈되는 FlowLayout) ──
        self._body = QWidget()
        self._body.setStyleSheet("background: transparent;")
        bsp = QSizePolicy(QSizePolicy.Policy.Preferred,
                          QSizePolicy.Policy.Minimum)
        bsp.setHeightForWidth(True)
        self._body.setSizePolicy(bsp)
        layout = FlowLayout(self._body, margin=6, hspacing=8, vspacing=4)
        outer.addWidget(self._body)

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

        self.season = self._add_combo(
            layout, "시즌", [(_ALL_LABEL, None)], width=80)

        self.reset_btn = QPushButton("초기화")
        self.reset_btn.setFixedHeight(24)
        self.reset_btn.clicked.connect(self.reset)
        layout.addWidget(self.reset_btn)

        # 기본은 접힌 상태로 시작한다.
        self._body.setVisible(False)
        self._update_active_indicator()

    # ── 접기/펼치기 ──────────────────────────────────────────────

    def _on_toggle(self, checked: bool) -> None:
        self._body.setVisible(checked)
        self.toggle_btn.setText(("▾" if checked else "▸") + "  필터")
        self._update_active_indicator()

    def _update_active_indicator(self) -> None:
        """접혀 있을 때 필터가 적용 중이면 헤더에 표시(놓치지 않도록)."""
        if not self._body.isVisible() and self.is_active():
            self._active_lbl.setText("● 적용 중")
        else:
            self._active_lbl.setText("")

    # ── 구성 헬퍼 ────────────────────────────────────────────────

    @staticmethod
    def _with_all(label_map: dict) -> list[tuple[str, str | None]]:
        """canonical→라벨 매핑 앞에 '전체'(None)를 붙인 콤보 항목 리스트."""
        return [(_ALL_LABEL, None)] + [(lbl, v) for v, lbl in label_map.items()]

    def _add_combo(self, layout: QLayout, title: str,
                   items: list[tuple[str, str | None]],
                   width: int) -> QComboBox:
        # 라벨+콤보를 한 칩으로 묶어 줄바꿈 시 분리되지 않게 한다.
        chip = QWidget()
        chip.setStyleSheet("background: transparent;")
        h = QHBoxLayout(chip)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {TEXT2}; font-size: 11px; background: transparent;"
            "border: none;")
        h.addWidget(lbl)
        combo = QComboBox()
        combo.setFixedWidth(width)
        for label, value in items:
            combo.addItem(label, value)
        combo.currentIndexChanged.connect(self._emit_changed)
        h.addWidget(combo)
        layout.addWidget(chip)
        self._combos.append(combo)
        return combo

    def _emit_changed(self, *_) -> None:
        self._update_active_indicator()
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


    def set_season_options_from(self, matches: Sequence[Match]) -> None:
        """기록에 등장한 시즌(YYYY-MM)으로 시즌 콤보 갱신 (선택 유지)."""
        seasons = sorted(
            {m.season for m in matches if m.season},
            reverse=True  # 최신 시즌 먼저
        )
        self._set_options(self.season, seasons)

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
            season=self.season.currentData(),
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
        self._update_active_indicator()
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
            "season":   self.season.currentData(),
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
        _set_data(self.season, "season")
        self._update_active_indicator()
        self.changed.emit()
