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
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QToolTip, QVBoxLayout, QWidget,
)

from .. import stats
from ..cardart.service import CardArtService
from ..styles import theme
from ..styles.theme import (
    ACCENT, BG, BORDER, LOSE, PANEL, TEXT, TEXT2, WIN,
)
from .advanced_bar import AdvancedBar
from .art_fetch import ArtFetcher
from .chart_theme import distribution_palette, style_plot
from .labels import fmt_pct

MIN_RELIABLE_N = 30
TIER1_CUM = 0.50
TIER2_CUM = 0.80

# 도넛 색 팔레트
_PALETTE = ["#4361ee", "#f97316", "#22c55e", "#eab308", "#a855f7",
            "#06b6d4", "#ec4899", "#84cc16", "#f43f5e", "#14b8a6"]


def _wr_color(win_rate) -> str:
    t = theme.active()
    if win_rate is None:
        return t.text2
    return t.win if win_rate >= 0.5 else t.lose


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
    """점유율 도넛 — 각 조각을 그 테마(상대 덱) 카드아트로 채운다.

    카드를 도넛 중심에 정렬하면 조각엔 카드 가장자리만 잘려 보인다. 그래서 각
    카드를 **그 조각의 위치(중앙: 중간 반지름·이등분각)에 놓고, 조각이 차지하는
    크기에 맞춰 커버 스케일**한다. 큰 조각엔 카드가 크게, 작은 조각엔 작게
    들어가며 항상 카드 중앙(일러스트)이 보인다. 색 식별용 옅은 틴트와 배경색
    구분선을 얹고, 아트가 없으면 팔레트 색으로 대체한다. 구멍은 좁게(0.42).
    """

    _HOLE_RATIO = 0.42

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # 세그먼트: (label, share, color, QPixmap|None, tooltip)
        self._segments: list[tuple] = []
        self._art_path = None              # 덱명 → 로컬 경로 resolver
        self._geo = None                   # (cx, cy, inner_r, outer_r) 히트테스트용
        self._arcs: list[tuple] = []       # (a_low, a_high, tooltip) 조각 각도범위
        self.setMinimumSize(220, 220)
        self.setMouseTracking(True)        # 호버 툴팁용

    def set_art_resolver(self, fn) -> None:
        """덱명을 받아 로컬 이미지 경로(또는 None)를 돌려주는 함수 등록."""
        self._art_path = fn

    def set_data(self, dist: list) -> None:
        palette = distribution_palette()
        segs = []
        for i, d in enumerate(dist[:len(palette) - 1]):
            segs.append((d["deck"], d["share"], palette[i % len(palette)],
                         self._load_art(d["deck"]), self._tip(d)))
        rest_items = dist[len(palette) - 1:]
        rest = sum(d["share"] for d in rest_items)
        if rest > 0:
            names = ", ".join(d["deck"] for d in rest_items[:6])
            more = " …" if len(rest_items) > 6 else ""
            tip = (f"기타 {len(rest_items)}종 · 점유율 {rest * 100:.1f}%\n"
                   f"{names}{more}")
            segs.append(("기타", rest, theme.active().border, None, tip))
        self._segments = segs
        self.update()

    @staticmethod
    def _tip(d: dict) -> str:
        games = d.get("wins", 0) + d.get("losses", 0)
        wr = fmt_pct(d["win_rate"]) if games else "—"
        return (f"{d['deck']}\n"
                f"점유율 {d['share'] * 100:.1f}% · {d['count']}전\n"
                f"내 승률 {wr} ({d.get('wins', 0)}승 {d.get('losses', 0)}패)")

    def _load_art(self, deck: str):
        if not self._art_path:
            return None
        path = self._art_path(deck)
        if not path:
            return None
        pix = QPixmap(path)
        return pix if not pix.isNull() else None

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        size = min(w, h) - 20
        if size <= 0 or not self._segments:
            return
        rect = QRectF((w - size) / 2, (h - size) / 2, size, size)
        cx, cy = rect.center().x(), rect.center().y()
        outer_r = size / 2.0
        inner_r = size * self._HOLE_RATIO / 2.0
        mid_r = (outer_r + inner_r) / 2.0
        sep = QColor(theme.active().bg)
        self._geo = (cx, cy, inner_r, outer_r)   # 히트테스트용
        self._arcs = []
        start_deg = 90.0                      # 12시 방향에서 시작
        for _label, share, color, pix, _tip in self._segments:
            span_deg = -share * 360.0
            self._arcs.append((start_deg + span_deg, start_deg, _tip))
            wedge = QPainterPath()
            wedge.moveTo(cx, cy)
            wedge.arcTo(rect, start_deg, span_deg)
            wedge.closeSubpath()

            p.save()
            p.setClipPath(wedge)
            if pix is not None:
                # 조각 중앙(중간 반지름·이등분각)에 배치, 조각 크기에 맞춰 커버
                mid_deg = start_deg + span_deg / 2.0
                brad = math.radians(mid_deg)
                tx = cx + mid_r * math.cos(brad)
                ty = cy - mid_r * math.sin(brad)
                half = abs(math.radians(span_deg)) / 2.0
                ch, sh = math.cos(half), math.sin(half)
                # 중앙에서 조각 네 모서리까지 최대 거리 → 그 지름으로 커버
                cover = max(math.hypot(outer_r * ch - mid_r, outer_r * sh),
                            math.hypot(inner_r * ch - mid_r, inner_r * sh))
                s = max(1.0, cover * 2.0 * 1.04)
                scaled = pix.scaled(
                    int(s), int(s),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation)
                p.drawPixmap(int(tx - scaled.width() / 2.0),
                             int(ty - scaled.height() / 2.0), scaled)
                tint = QColor(color)
                tint.setAlpha(28)             # 색 식별용 아주 옅은 틴트
                p.fillPath(wedge, tint)
            else:
                p.fillPath(wedge, QColor(color))
            p.restore()

            p.setPen(QPen(sep, 2))            # 조각 구분선
            p.setBrush(Qt.NoBrush)
            p.drawPath(wedge)
            start_deg += span_deg

        # 가운데 구멍 (좁게)
        hole = size * self._HOLE_RATIO
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.active().bg))
        p.drawEllipse(QRectF(cx - hole / 2, cy - hole / 2, hole, hole))

    # ── 호버 툴팁 ────────────────────────────────────────────────
    def _seg_at(self, pos) -> str | None:
        """커서 위치(QPointF)가 올라간 조각의 툴팁(없으면 None)."""
        if not self._geo or not self._arcs:
            return None
        cx, cy, inner_r, outer_r = self._geo
        dx = pos.x() - cx
        dy = cy - pos.y()                 # 화면 y는 아래로 증가 → 위로 보정
        r = math.hypot(dx, dy)
        if r < inner_r or r > outer_r:    # 구멍/바깥은 제외
            return None
        ang = math.degrees(math.atan2(dy, dx))
        for a_low, a_high, tip in self._arcs:
            for k in (-360.0, 0.0, 360.0):
                if a_low <= ang + k <= a_high:
                    return tip
        return None

    def mouseMoveEvent(self, e) -> None:
        pos = e.position() if hasattr(e, "position") else e.pos()
        tip = self._seg_at(pos)
        if tip:
            gp = (e.globalPosition().toPoint() if hasattr(e, "globalPosition")
                  else e.globalPos())
            QToolTip.showText(gp, tip, self)
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e) -> None:
        QToolTip.hideText()
        super().leaveEvent(e)


class MetaView(QWidget):
    def __init__(self, db, matches_provider=None):
        super().__init__()
        self.db = db
        self._matches = matches_provider or db.matches.all
        self.art = CardArtService(db.decks)
        self._fetcher = ArtFetcher(self.art, self)
        self._fetcher.fetched.connect(lambda *_: self.refresh())
        theme.theme_notifier.changed.connect(lambda *_: self.refresh())
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

        # 부차 컨트롤은 '고급'으로 접는다(삭제 아님): 정렬·막대/도넛
        self._adv = AdvancedBar()
        self._adv.add_label("정렬")
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(["빈도순", "위협 지수순"])
        self._sort_combo.currentIndexChanged.connect(self.refresh)
        self._adv.add_widget(self._sort_combo)
        self._chart_toggle = QPushButton("도넛 보기")
        self._chart_toggle.setCheckable(True)
        self._chart_toggle.toggled.connect(self._on_chart_toggled)
        self._adv.add_widget(self._chart_toggle)
        bar.addWidget(self._adv)
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
        style_plot(self.plot)
        body.addWidget(self.plot, 1)

        # 도넛 (기본 보기) — 각 조각을 상대 덱 카드아트로 채운다
        self.donut = _DonutWidget()
        self.donut.set_art_resolver(self.art.local_path)
        self.donut.hide()
        body.addWidget(self.donut, 1)
        root.addLayout(body, 1)

        # 도넛을 기본 보기로 — 막대 차트는 '고급'에서 전환
        self._chart_toggle.setChecked(True)

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
            for d in dist[:12]:               # 표시될 상위 덱 아트 선요청
                self._fetcher.request(d["deck"])
            self.donut.set_data(dist)
            return

        self.plot.clear()
        style_plot(self.plot)
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
            brushes = [QColor(theme.active().accent) for _ in tiered]
            self.plot.setLabel("bottom", "횟수")
            tick_labels = [(i, tiered[i]["deck"]) for i in ys]
        bars = pg.BarGraphItem(x0=0, y=ys, height=0.6, width=widths,
                               brushes=brushes)
        self.plot.addItem(bars)
        self.plot.getAxis("left").setTicks([tick_labels])
        if widths and max(widths) > 0:
            self.plot.setXRange(0, max(widths))
