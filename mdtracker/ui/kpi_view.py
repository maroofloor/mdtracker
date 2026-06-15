"""KPI 요약 뷰 — 승률 카드 그리드 + 그라디언트 바 + 내 덱별 승률 테이블."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import stats
from ..cardart.service import CardArtService
from ..styles.theme import (
    ACCENT, BG, BORDER, LOSE, PANEL, SURFACE, SURFACE2, TEXT, TEXT2, WIN,
)
from .art_fetch import ArtFetcher
from .deck_avatar import DeckAvatar
from .donut import CoinGauge, DonutGauge
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

        rate_row = QHBoxLayout()
        rate_row.setContentsMargins(0, 0, 0, 0)
        rate_row.setSpacing(6)
        self._rate_lbl = QLabel("—")
        self._rate_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 28px; font-weight: 700; border: none;")
        rate_row.addWidget(self._rate_lbl)
        self._delta_lbl = QLabel("")
        self._delta_lbl.setStyleSheet(
            f"color: {TEXT2}; font-size: 11px; font-weight: 700; border: none;")
        self._delta_lbl.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
        rate_row.addWidget(self._delta_lbl)
        rate_row.addStretch(1)
        layout.addLayout(rate_row)

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

        self._best = QLabel("")
        self._best.setStyleSheet(
            f"color: {TEXT2}; font-size: 10px; border: none;")
        layout.addWidget(self._best)

    def update_data(self, s: dict, streak: dict, best: dict | None = None,
                    delta: float | None = None) -> None:
        ov = s["overall"]
        wr = ov["win_rate"] or 0.0
        color = WIN if wr >= 0.5 else LOSE
        self._rate_lbl.setText(fmt_pct(wr))
        self._rate_lbl.setStyleSheet(
            f"color: {color}; font-size: 28px; font-weight: 700; border: none;")
        # 직전 기간 대비 증감 (%p) — 비교 표본이 없으면(delta=None) 생략
        if delta is None:
            self._delta_lbl.setText("")
            self._delta_lbl.hide()
        else:
            arrow = "▲" if delta >= 0 else "▼"
            d_color = WIN if delta >= 0 else LOSE
            self._delta_lbl.setText(f"{arrow} {abs(delta):.1f}%p")
            self._delta_lbl.setStyleSheet(
                f"color: {d_color}; font-size: 11px; font-weight: 700;"
                " border: none;")
            self._delta_lbl.show()
        self._bar.set_rate(wr)
        draws = ov.get("draws", 0)
        draw_str = f"  무{draws}" if draws > 0 else ""
        self._detail.setText(
            f"{ov['wins']}승  {ov['losses']}패{draw_str}  ·  {ov['n']}전")
        self._streak.setText(_streak_text(streak))
        if best and (best["win"] or best["loss"]):
            self._best.setText(
                f"최고  🔥{best['win']}연승 / ❄{best['loss']}연패")
            self._best.show()
        else:
            self._best.hide()


class KpiView(QWidget):
    """대시보드 요약 탭 — KPI 카드 3개 + 선/후공 + 덱별 승률."""

    def __init__(self, db, matches_provider=None) -> None:
        super().__init__()
        self.db = db
        # 대시보드 공통 필터를 거친 list[Match] 공급자 (기본: 전체)
        self._matches = matches_provider or db.matches.all
        self.art = CardArtService(db.decks)
        self._deck_avatars: dict[str, DeckAvatar] = {}
        self._fetcher = ArtFetcher(self.art, self)
        self._fetcher.fetched.connect(self._on_art_fetched)
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # ── 히어로 밴드: 승률 도넛 + 스트릭 + 코인 게이지 ──────────
        hero = QHBoxLayout()
        hero.setSpacing(20)
        self.donut = DonutGauge(168)
        hero.addWidget(self.donut)

        right = QVBoxLayout()
        right.setSpacing(6)
        right.addStretch(1)
        hero_title = QLabel("전체 승률")
        hero_title.setStyleSheet(
            f"color:{TEXT2}; font-size:12px; font-weight:600; border:none;")
        right.addWidget(hero_title)
        self.hero_streak = QLabel("—")
        self.hero_streak.setStyleSheet(
            f"color:{TEXT}; font-size:20px; font-weight:700; border:none;")
        right.addWidget(self.hero_streak)
        coin_title = QLabel("코인토스 (50% 기준)")
        coin_title.setStyleSheet(
            f"color:{TEXT2}; font-size:11px; border:none; padding-top:6px;")
        right.addWidget(coin_title)
        self.coin_gauge = CoinGauge()
        right.addWidget(self.coin_gauge)
        self.hero_coin = QLabel("—")
        self.hero_coin.setStyleSheet(
            f"color:{TEXT2}; font-size:11px; border:none;")
        right.addWidget(self.hero_coin)
        right.addStretch(1)
        hero.addLayout(right, 1)
        root.addLayout(hero)

        # ── KPI 카드 3열 ─────────────────────────────────────────
        card_row = QHBoxLayout()
        card_row.setSpacing(10)
        self._cards: list[KpiCard] = []
        for title in ["전체", "오늘", "7일", "30일"]:
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
        self._coin_n_widgets: dict[str, QLabel] = {}
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
            n_lbl = QLabel("")
            n_lbl.setStyleSheet(
                f"color:{TEXT2}; font-size:9px; border:none;")
            bl.addWidget(title_lbl)
            bl.addWidget(val_lbl)
            bl.addWidget(n_lbl)
            coin_row.addWidget(box)
            self._coin_widgets[key] = val_lbl
            self._coin_n_widgets[key] = n_lbl
        root.addLayout(coin_row)

        # ── 코인토스 승률 (토스 자체를 이긴 비율) ────────────────
        self.toss_rate_lbl = QLabel()
        self.toss_rate_lbl.setStyleSheet(
            f"color:{TEXT2}; font-size:12px; font-weight:600; padding:2px 0;")
        root.addWidget(self.toss_rate_lbl)

        # ── 토스 승리 시 선택 비율 + 선택별 승률 ─────────────────
        self.choice_lbl = QLabel()
        self.choice_lbl.setStyleSheet(
            f"color:{TEXT2}; font-size:11px; border:none;")
        self.choice_rate_lbl = QLabel()
        self.choice_rate_lbl.setStyleSheet(
            f"color:{TEXT2}; font-size:11px; border:none;")
        root.addWidget(self.choice_lbl)
        root.addWidget(self.choice_rate_lbl)

        # ── 내 덱별 승률 (아트 썸네일 + 가로 승률 바 리스트) ──────
        deck_title = QLabel("내 덱별 승률")
        deck_title.setStyleSheet(
            f"color:{TEXT2}; font-size:15px; font-weight:600;")
        root.addWidget(deck_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        deck_container = QWidget()
        deck_container.setStyleSheet("background: transparent;")
        self._deck_box = QVBoxLayout(deck_container)
        self._deck_box.setContentsMargins(0, 0, 0, 0)
        self._deck_box.setSpacing(6)
        self._deck_box.addStretch(1)
        scroll.setWidget(deck_container)
        root.addWidget(scroll, 1)

    # ── internal helpers ─────────────────────────────────────────

    def _period_matches(self) -> tuple[list, list, list, list]:
        all_matches = self._matches()
        today_prefix = date.today().isoformat()
        today = [m for m in all_matches if m.played_at.startswith(today_prefix)]
        seven_ago = (date.today() - timedelta(days=6)).isoformat()
        week = [m for m in all_matches if m.played_at[:10] >= seven_ago]
        thirty_ago = (date.today() - timedelta(days=29)).isoformat()
        month30 = [m for m in all_matches if m.played_at[:10] >= thirty_ago]
        return all_matches, today, week, month30

    def _delta_pp(self, all_matches: list, cur_rate, span: int) -> float | None:
        """직전 동일 길이 기간 대비 승률 증감(%p). 비교 표본 0이면 None."""
        if cur_rate is None:
            return None
        t = date.today()
        cur_start = (t - timedelta(days=span - 1)).isoformat()
        prev_start = (t - timedelta(days=2 * span - 1)).isoformat()
        prev = [m for m in all_matches
                if prev_start <= m.played_at[:10] < cur_start]
        prev_rate = stats.win_rate_summary(prev)["overall"]["win_rate"]
        if prev_rate is None:           # 비교 표본 0 → 델타 생략
            return None
        return (cur_rate - prev_rate) * 100.0

    @staticmethod
    def _choice_rate_text(by_choice: dict | None) -> str:
        """토스 승리 시 선공/후공 선택별 듀얼 승률. 표본 3건 미만은 경고."""
        if not by_choice:
            return ""

        def _part(label: str, t: dict) -> str:
            n = t["n"]
            if n < 3:
                return f"{label} ⚠ 표본 {n}건"
            return f"{label} {fmt_pct(t['win_rate'])} ({t['wins']}승{t['losses']}패)"

        return ("토스 승리 시  "
                + _part("선공 선택", by_choice["first"])
                + "  ·  "
                + _part("후공 선택", by_choice["second"]))

    def refresh(self) -> None:
        all_matches, today, week, month30 = self._period_matches()
        s_all = stats.win_rate_summary([])  # 빈 데이터셋 기본값 (NameError 방어)

        period_lists = [all_matches, today, week, month30]
        # 7일 카드(idx 2)·30일 카드(idx 3)만 직전 기간 대비 델타 표기
        spans = [None, None, 7, 30]
        for card, ms, span in zip(self._cards, period_lists, spans):
            s = stats.win_rate_summary(ms)
            t = stats.trend_series(ms)
            delta = (self._delta_pp(all_matches, s["overall"]["win_rate"], span)
                     if span else None)
            card.update_data(s, t["current_streak"], t.get("best_streak"), delta)
            if card is self._cards[0]:
                s_all = s

        self.overall_lbl.setText(f"전체  {_line(s_all['overall'])}")

        # ── 히어로 갱신 (도넛 + 스트릭 + 코인 게이지) ──────────────
        ov = s_all["overall"]
        self.donut.set_data(ov["win_rate"], ov["wins"], ov["losses"], ov["n"])
        t_all = stats.trend_series(all_matches)
        self.hero_streak.setText(_streak_text(t_all["current_streak"]))
        ctr_h = s_all["coin_toss_rate"]
        self.coin_gauge.set_data(ctr_h["rate"], ctr_h["win"], ctr_h["n"])
        self.hero_coin.setText(
            f"{fmt_pct(ctr_h['rate'])}  ({ctr_h['win']}/{ctr_h['n']})"
            if ctr_h["n"] else "기록 없음")

        def _pct(d: dict) -> str:
            return fmt_pct(d["win_rate"]) if d["n"] else "—"

        def _set_box(key: str, d: dict) -> None:
            self._coin_widgets[key].setText(_pct(d))
            self._coin_n_widgets[key].setText(f"({d['n']}전)" if d["n"] else "")

        _set_box("first", s_all["by_coin"]["first"])
        _set_box("second", s_all["by_coin"]["second"])
        _set_box("toss_win", s_all["by_coin_toss"]["win"])
        _set_box("toss_loss", s_all["by_coin_toss"]["loss"])

        # 코인토스 승률 — 50%가 기댓값. 49~51%는 중립색, 벗어나면 약하게 강조.
        ctr = s_all["coin_toss_rate"]
        if ctr["n"]:
            in_band = 0.49 <= (ctr["rate"] or 0.0) <= 0.51
            band_color = TEXT2 if in_band else TEXT
            self.toss_rate_lbl.setText(
                f"코인토스 승률 {fmt_pct(ctr['rate'])} "
                f"({ctr['win']}/{ctr['n']})")
            self.toss_rate_lbl.setStyleSheet(
                f"color:{band_color}; font-size:12px; font-weight:600;"
                " padding:2px 0;")
        else:
            self.toss_rate_lbl.setText("코인토스 승률 —")
            self.toss_rate_lbl.setStyleSheet(
                f"color:{TEXT2}; font-size:12px; font-weight:600; padding:2px 0;")

        c = s_all["toss_win_choice"]
        if c["n"]:
            self.choice_lbl.setText(
                f"토스 승리 시 선공 선택: {fmt_pct(c['first'] / c['n'])} "
                f"({c['first']}/{c['n']})")
        else:
            self.choice_lbl.setText("토스 승리 시 선공 선택: —")

        # 토스 승리 시 선택별 듀얼 승률 (표본 3건 미만 경고)
        self.choice_rate_lbl.setText(self._choice_rate_text(c.get("by_choice")))

        decks = sorted(s_all["by_my_deck"].items(),
                       key=lambda kv: kv[1]["n"], reverse=True)
        # 기존 행 제거 후 재구성
        while self._deck_box.count():
            item = self._deck_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._deck_avatars = {}
        for deck, d in decks:
            self._deck_box.addWidget(self._make_deck_row(deck, d))
        self._deck_box.addStretch(1)

    def _make_deck_row(self, deck: str, d: dict) -> QWidget:
        wr = d["win_rate"] or 0.0
        wr_color = WIN if wr >= 0.5 else LOSE
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        h = QHBoxLayout(row)
        h.setContentsMargins(4, 2, 4, 2)
        h.setSpacing(10)

        avatar = DeckAvatar(deck, self.art.local_path(deck), size=30)
        self._deck_avatars[deck] = avatar
        self._fetcher.request(deck)
        h.addWidget(avatar)

        name = QLabel(deck)
        name.setFixedWidth(130)
        name.setStyleSheet(
            f"color:{TEXT}; font-size:13px; font-weight:600; border:none;")
        h.addWidget(name)

        bar = WinRateBar()
        bar.setFixedHeight(8)
        bar.set_rate(wr)
        h.addWidget(bar, 1)

        rec = QLabel(
            f"{fmt_pct(wr)}  ({d['wins']}승 {d['losses']}패 · {d['n']}전)")
        rec.setFixedWidth(170)
        rec.setStyleSheet(f"color:{wr_color}; font-size:11px; border:none;")
        h.addWidget(rec)
        return row

    def _on_art_fetched(self, deck_name: str, path: str) -> None:
        avatar = self._deck_avatars.get(deck_name)
        if avatar is not None and path:
            avatar.set_image(path)
