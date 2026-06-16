"""대시보드 히어로용 QPainter 위젯 — 승률 도넛 + 코인 50% 게이지.

색은 테마 토큰을 따르고 theme_notifier.changed 시 다시 그린다.
데이터/통계 로직은 호출자가 계산해 set_*()로 주입한다(이 위젯은 표현만).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import (
    Property, QEasingCurve, QPropertyAnimation, QRectF, Qt,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..styles import theme


def _mix(c1: QColor, c2: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(
        round(c1.red() + (c2.red() - c1.red()) * t),
        round(c1.green() + (c2.green() - c1.green()) * t),
        round(c1.blue() + (c2.blue() - c1.blue()) * t),
    )


class DonutGauge(QWidget):
    """승률 도넛 — 중앙에 백분율, 아래에 승/패. rate None이면 빈 상태."""

    def __init__(self, size: int = 168, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rate: Optional[float] = None
        self._wins = 0
        self._losses = 0
        self._n = 0
        self._anim_rate = 0.0
        self._anim = QPropertyAnimation(self, b"animRate", self)
        self._anim.setDuration(650)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setMinimumSize(size, size)
        try:
            theme.theme_notifier.changed.connect(lambda *_: self.update())
        except Exception:
            pass

    def get_anim_rate(self) -> float:
        return self._anim_rate

    def set_anim_rate(self, v: float) -> None:
        self._anim_rate = v
        self.update()

    animRate = Property(float, get_anim_rate, set_anim_rate)

    def set_data(self, rate: Optional[float], wins: int, losses: int,
                 n: int) -> None:
        self._rate = rate
        self._wins, self._losses, self._n = wins, losses, n
        target = rate or 0.0
        self._anim.stop()
        self._anim.setStartValue(self._anim_rate)
        self._anim.setEndValue(target)
        self._anim.start()
        self.update()

    def paintEvent(self, _event) -> None:
        t = theme.active()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        side = min(self.width(), self.height())
        thick = max(10.0, side * 0.12)
        margin = thick / 2 + 2
        rect = QRectF(
            (self.width() - side) / 2 + margin,
            (self.height() - side) / 2 + margin,
            side - 2 * margin, side - 2 * margin)

        rate = self._rate
        # 값 아크는 테마 강조색 사용 — 테마 전환이 분명히 드러난다.
        # (승률의 좋고 나쁨은 가운데 % 숫자 색으로 표현)
        value_color = QColor(t.border) if rate is None else QColor(t.accent)

        # 트랙
        track = QPen(QColor(t.surface2), thick)
        track.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(track)
        p.drawArc(rect, 0, 360 * 16)

        # 값 아크 (12시 방향에서 시계방향, 애니메이션 값으로 채움)
        arc_rate = self._anim_rate
        if rate is not None and arc_rate > 0:
            pen = QPen(value_color, thick)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            span = int(-arc_rate * 360 * 16)
            p.drawArc(rect, 90 * 16, span)

        # 중앙 텍스트 (숫자 카운트업)
        pct = "—" if rate is None else f"{round(self._anim_rate * 100)}%"
        if rate is None:
            pct_color = t.text2
        else:
            pct_color = t.win if rate >= 0.5 else t.lose
        p.setPen(QColor(pct_color))
        f = QFont("Noto Sans KR")
        f.setBold(True)
        f.setPixelSize(int(side * 0.24))
        p.setFont(f)
        top = QRectF(rect.x(), rect.y() + rect.height() * 0.24,
                     rect.width(), rect.height() * 0.42)
        p.drawText(top, Qt.AlignmentFlag.AlignCenter, pct)

        sub = "기록 없음" if self._n == 0 else f"{self._wins}승 {self._losses}패"
        p.setPen(QColor(t.text2))
        fs = QFont("Noto Sans KR")
        fs.setPixelSize(int(side * 0.085))
        p.setFont(fs)
        bottom = QRectF(rect.x(), rect.y() + rect.height() * 0.58,
                        rect.width(), rect.height() * 0.28)
        p.drawText(bottom, Qt.AlignmentFlag.AlignCenter, sub)
        p.end()


class CoinGauge(QWidget):
    """코인토스 승률 게이지 — 50% 기준선 표시. rate None이면 빈 상태."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rate: Optional[float] = None
        self._win = 0
        self._n = 0
        self.setMinimumHeight(10)
        self.setFixedHeight(10)
        try:
            theme.theme_notifier.changed.connect(lambda *_: self.update())
        except Exception:
            pass

    def set_data(self, rate: Optional[float], win: int, n: int) -> None:
        self._rate, self._win, self._n = rate, win, n
        self.update()

    def paintEvent(self, _event) -> None:
        t = theme.active()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(t.surface2))
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)

        if self._rate is not None and self._n:
            fill_w = w * max(0.0, min(1.0, self._rate))
            if fill_w > 0:
                p.setBrush(QColor(t.accent))   # 테마 강조색으로 채움
                p.drawRoundedRect(QRectF(0, 0, fill_w, h), h / 2, h / 2)

        # 50% 기준선
        p.setPen(QPen(QColor(t.text2), 1))
        x = w / 2
        p.drawLine(int(x), 0, int(x), h)
        p.end()
