"""PDF 전적 리포트 생성 — QPdfWriter + QPainter 기반.

새 의존성 없이(PySide6만으로) 요약·시즌 리포트를 A4 PDF로 렌더한다.
데이터 집계는 stats.py 순수 함수에 위임하고, 이 모듈은 DB 조회 + 그리기만 한다.
카드 아트(CardArtService)가 주어지면 내 덱별 표에 썸네일을 끼워 넣는다(선택).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6.QtCore import QMarginsF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QPixmap,
)
from PySide6.QtWidgets import QApplication

from . import stats
from .ui.labels import fmt_pct

_DPI = 150
_MM = _DPI / 25.4  # 1mm를 device 픽셀로


def _mm(v: float) -> float:
    return v * _MM


class _Canvas:
    """y 커서를 들고 자동 페이지 넘김을 처리하는 그리기 헬퍼."""

    def __init__(self, writer: QPdfWriter, painter: QPainter, colors: dict):
        self.w = writer
        self.p = painter
        self.c = colors
        self.width = writer.width()
        self.height = writer.height()
        self.y = 0.0

    # ── 페이지 ────────────────────────────────────────────────
    def _ensure(self, need: float) -> None:
        if self.y + need > self.height:
            self.w.newPage()
            self.y = 0.0

    def gap(self, h_mm: float) -> None:
        self.y += _mm(h_mm)

    # ── 텍스트 ────────────────────────────────────────────────
    def _font(self, size: int, bold: bool = False) -> QFont:
        f = QFont(self.base_font)
        f.setPointSize(size)
        f.setBold(bold)
        return f

    def text(self, s: str, *, size: int = 10, bold: bool = False,
             color: Optional[str] = None, indent_mm: float = 0.0,
             align=Qt.AlignmentFlag.AlignLeft) -> None:
        self.p.setFont(self._font(size, bold))
        fm = self.p.fontMetrics()
        line_h = fm.height() + _mm(1.2)
        self._ensure(line_h)
        self.p.setPen(QColor(color or self.c["text"]))
        rect = QRectF(_mm(indent_mm), self.y,
                      self.width - _mm(indent_mm), line_h)
        self.p.drawText(rect, int(align | Qt.AlignmentFlag.AlignVCenter), s)
        self.y += line_h

    def heading(self, s: str) -> None:
        self.gap(3)
        self._ensure(_mm(9))
        self.p.setFont(self._font(13, bold=True))
        fm = self.p.fontMetrics()
        line_h = fm.height() + _mm(1.5)
        self.p.setPen(QColor(self.c["accent"]))
        self.p.drawText(QRectF(0, self.y, self.width, line_h),
                        int(Qt.AlignmentFlag.AlignLeft
                            | Qt.AlignmentFlag.AlignVCenter), s)
        self.y += line_h
        # 밑줄
        self.p.setPen(QColor(self.c["border"]))
        self.p.drawLine(0, int(self.y), int(self.width), int(self.y))
        self.gap(2)

    # ── 진행/승률 바 ──────────────────────────────────────────
    def bar(self, rate: float, *, x_mm: float, w_mm: float,
            h_mm: float = 3.0) -> None:
        x, w, h = _mm(x_mm), _mm(w_mm), _mm(h_mm)
        rate = max(0.0, min(1.0, rate))
        self.p.setPen(Qt.PenStyle.NoPen)
        self.p.setBrush(QColor(self.c["surface2"]))
        self.p.drawRoundedRect(QRectF(x, self.y, w, h), h / 2, h / 2)
        fill = w * rate
        if fill > 0:
            col = self.c["win"] if rate >= 0.5 else self.c["lose"]
            self.p.setBrush(QColor(col))
            self.p.drawRoundedRect(QRectF(x, self.y, fill, h), h / 2, h / 2)

    def deck_row(self, name: str, rec: dict, *, art_path: Optional[str]) -> None:
        """내 덱별 승률 한 줄: [썸네일] 이름 | 바 | 전적."""
        row_h = _mm(7)
        self._ensure(row_h)
        cy = self.y
        x = 0.0
        # 썸네일
        thumb = _mm(6)
        if art_path:
            pix = QPixmap(art_path)
            if not pix.isNull():
                pix = pix.scaled(int(thumb), int(thumb),
                                 Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                 Qt.TransformationMode.SmoothTransformation)
                self.p.drawPixmap(int(x), int(cy), int(thumb), int(thumb), pix)
        x += thumb + _mm(2)
        # 이름
        self.p.setFont(self._font(10, bold=True))
        self.p.setPen(QColor(self.c["text"]))
        self.p.drawText(QRectF(x, cy, _mm(40), thumb),
                        int(Qt.AlignmentFlag.AlignLeft
                            | Qt.AlignmentFlag.AlignVCenter), name)
        # 바 (썸네일+이름 뒤 ~ 우측 전적칸 앞 사이를 채움, device px로 직접 계산)
        wr = rec["win_rate"] or 0.0
        bar_x = x + _mm(42)
        bar_w = max(_mm(10), self.width - bar_x - _mm(48))
        bar_h = _mm(3)
        bar_y = cy + thumb / 2 - bar_h / 2
        self.p.setPen(Qt.PenStyle.NoPen)
        self.p.setBrush(QColor(self.c["surface2"]))
        self.p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h),
                               bar_h / 2, bar_h / 2)
        if wr > 0:
            col = self.c["win"] if wr >= 0.5 else self.c["lose"]
            self.p.setBrush(QColor(col))
            self.p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w * wr, bar_h),
                                   bar_h / 2, bar_h / 2)
        # 전적
        self.p.setFont(self._font(9))
        self.p.setPen(QColor(self.c["text2"]))
        txt = f"{fmt_pct(rec['win_rate'])}  ({rec['wins']}승 {rec['losses']}패 · {rec['n']}전)"
        self.p.drawText(QRectF(self.width - _mm(46), cy, _mm(46), thumb),
                        int(Qt.AlignmentFlag.AlignRight
                            | Qt.AlignmentFlag.AlignVCenter), txt)
        self.y = cy + row_h


def _colors() -> dict:
    """인쇄용(흰 배경) 고대비 팔레트.

    화면 테마는 어두운 배경 기준이라 그대로 흰 종이에 쓰면 글자가 흐려진다.
    문서는 항상 짙은 글자/밝은 배경으로 고정해 가독성을 확보한다.
    """
    return {
        "bg": "#ffffff",
        "text": "#0f172a",        # 거의 검정 (제목·본문)
        "text2": "#475569",       # 슬레이트-600 (보조 텍스트, 흰 배경서 충분히 진함)
        "accent": "#1d4ed8",      # 블루-700 (섹션 제목)
        "border": "#cbd5e1",      # 슬레이트-300 (밑줄)
        "surface": "#f1f5f9",
        "surface2": "#e2e8f0",    # 바 트랙 (연회색)
        "win": "#16a34a",         # 그린-600
        "lose": "#dc2626",        # 레드-600
    }


def export_report_pdf(db, path: str, *, art=None) -> str:
    """전적 리포트 PDF를 path에 생성하고 그 경로를 돌려준다.

    art: CardArtService (선택). 주어지면 내 덱 썸네일을 표에 넣는다.
    """
    matches = db.matches.all()

    writer = QPdfWriter(path)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setResolution(_DPI)
    writer.setPageMargins(QMarginsF(15, 15, 15, 15),
                          QPageLayout.Unit.Millimeter)
    writer.setTitle("Master Duel 전적 리포트")

    painter = QPainter(writer)
    try:
        colors = _colors()
        cv = _Canvas(writer, painter, colors)
        app = QApplication.instance()
        cv.base_font = app.font() if app is not None else QFont()

        _render(cv, matches, art)
    finally:
        painter.end()
    return path


def _render(cv: _Canvas, matches: list, art) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    summary = stats.win_rate_summary(matches)
    ov = summary["overall"]

    # ── 표지 헤더 ──────────────────────────────────────────────
    cv.text("Master Duel 전적 리포트", size=20, bold=True, color=cv.c["text"])
    cv.text(f"생성: {now}", size=9, color=cv.c["text2"])
    if matches:
        first = min(m.played_at for m in matches)[:10]
        last = max(m.played_at for m in matches)[:10]
        cv.text(f"기간: {first} ~ {last}   ·   총 {len(matches)}전",
                size=9, color=cv.c["text2"])
    cv.gap(3)

    # ── 요약 ──────────────────────────────────────────────────
    cv.heading("전체 요약")
    draw_s = f"  무 {ov['draws']}" if ov["draws"] else ""
    cv.text(f"승률 {fmt_pct(ov['win_rate'])}   "
            f"({ov['wins']}승 {ov['losses']}패{draw_s} · {ov['n']}전)",
            size=13, bold=True)
    cv.gap(1)
    cv.bar(ov["win_rate"] or 0.0, x_mm=0, w_mm=120, h_mm=4)
    cv.gap(6)

    # 코인토스 / 선후공
    ctr = summary["coin_toss_rate"]
    cv.text(f"코인토스 승률: {fmt_pct(ctr['rate'])}  ({ctr['win']}/{ctr['n']})  "
            "— 기댓값 50%", size=10, color=cv.c["text2"])
    bc = summary["by_coin"]

    def _coin_line(label, d):
        return f"{label} {fmt_pct(d['win_rate'])} ({d['n']}전)" if d["n"] else f"{label} —"

    cv.text("선후공별 승률:  "
            + _coin_line("선공", bc["first"]) + "   ·   "
            + _coin_line("후공", bc["second"]), size=10, color=cv.c["text2"])

    # ── 내 덱별 승률 ──────────────────────────────────────────
    by_deck = sorted(summary["by_my_deck"].items(),
                     key=lambda kv: kv[1]["n"], reverse=True)
    if by_deck:
        cv.heading("내 덱별 승률")
        for deck, rec in by_deck:
            ap = art.local_path(deck) if art is not None else None
            cv.deck_row(deck, rec, art_path=ap)

    # ── 상대 메타 분포 ────────────────────────────────────────
    meta = stats.opponent_meta(matches)
    if meta["distribution"]:
        cv.heading("상대 덱 메타 (상위 12)")
        for d in meta["distribution"][:12]:
            wr = fmt_pct(d["win_rate"]) if (d["wins"] + d["losses"]) else "—"
            cv.text(
                f"{d['deck']}    {d['share']*100:.0f}%  ({d['count']}회)"
                f"    내 승률 {wr}",
                size=10, color=cv.c["text"])

    # ── 시즌별 요약 ───────────────────────────────────────────
    seasons = sorted({m.season for m in matches if m.season}, reverse=True)
    if seasons:
        cv.heading("시즌별 요약")
        for season in seasons:
            sm = stats.win_rate_summary(
                [m for m in matches if m.season == season])["overall"]
            cv.text(
                f"{season}    승률 {fmt_pct(sm['win_rate'])}    "
                f"({sm['wins']}승 {sm['losses']}패 · {sm['n']}전)",
                size=10, color=cv.c["text"])

    if not matches:
        cv.gap(4)
        cv.text("기록이 없습니다. 먼저 전적을 입력하세요.",
                size=11, color=cv.c["text2"])
