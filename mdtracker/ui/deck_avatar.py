"""덱 대표 카드 아바타 위젯 (QPainter).

이미지가 있으면 둥근 모서리로 표시하고, 없으면 덱명 해시 기반 색 그라디언트 +
이니셜 폴백을 그린다. 텍스트 색은 테마 토큰을 따르며 테마 전환 시 갱신된다.
더블클릭하면 clicked 시그널을 발행한다(대표 카드 지정 진입점).
"""

from __future__ import annotations

import hashlib
from typing import Optional

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPixmap,
)
from PySide6.QtWidgets import QWidget

from ..styles import theme


def _hue_for(name: str) -> int:
    digest = hashlib.md5((name or "?").encode("utf-8")).hexdigest()
    return int(digest[:6], 16) % 360


class DeckAvatar(QWidget):
    clicked = Signal()

    def __init__(self, deck_name: str, image_path: Optional[str] = None,
                 size: int = 34, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._name = deck_name or ""
        self._size = size
        self._pix: Optional[QPixmap] = None
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("더블클릭하여 대표 카드 지정")
        if image_path:
            self.set_image(image_path)
        # 테마 전환 시 폴백 색/텍스트 갱신
        try:
            theme.theme_notifier.changed.connect(self._on_theme_changed)
        except Exception:
            pass

    def _on_theme_changed(self, _theme_id: str) -> None:
        self.update()

    def set_image(self, image_path: Optional[str]) -> None:
        if not image_path:
            self._pix = None
        else:
            pix = QPixmap(image_path)
            self._pix = None if pix.isNull() else pix
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        radius = max(4.0, w * 0.22)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
        p.setClipPath(path)

        if self._pix is not None:
            scaled = self._pix.scaled(
                w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation)
            x = (scaled.width() - w) // 2
            y = (scaled.height() - h) // 2
            p.drawPixmap(0, 0, scaled, x, y, w, h)
            p.end()
            return

        # 폴백: 색 그라디언트 + 이니셜
        hue = _hue_for(self._name)
        c1 = QColor.fromHsl(hue, 130, 96)
        c2 = QColor.fromHsl((hue + 28) % 360, 140, 66)
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)
        p.fillRect(QRectF(0, 0, w, h), grad)

        initial = self._name.strip()[:1] if self._name.strip() else "?"
        p.setClipping(False)
        font = QFont("Noto Sans KR")
        font.setBold(True)
        font.setPixelSize(max(10, int(h * 0.46)))
        p.setFont(font)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, initial)
        p.end()

    def mouseDoubleClickEvent(self, _event) -> None:
        self.clicked.emit()
