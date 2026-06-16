"""'고급' 접기 토글 — 부차 컨트롤을 기본 숨김으로 모으는 공용 위젯.

기본 보기에는 핵심 컨트롤만 노출하고, 정렬·축·차트형식 등 부차 토글은
'고급 ▾' 버튼을 눌러야 펼쳐지게 한다. **삭제가 아니라 접기**이므로 모든
기능은 그대로 유지된다. 버튼은 전역 QSS(QPushButton)를 따르므로 테마 전환에
자동 대응하고, 추가 라벨은 활성 테마의 text2 색을 쓴다.

사용 예::

    self._adv = AdvancedBar()
    self._adv.add_label("정렬")
    self._adv.add_widget(self._sort_combo)
    self._adv.add_widget(self._chart_toggle)
    bar.addWidget(self._adv)        # 기본 바 끝(보통 addStretch 뒤)에 배치
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from ..styles import theme

_LABEL_CLOSED = "고급  ▾"
_LABEL_OPEN = "고급  ▴"


class AdvancedBar(QWidget):
    """'고급 ▾' 토글 버튼 + 접히는 가로 컨테이너(부차 컨트롤)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self._btn = QPushButton(_LABEL_CLOSED)
        self._btn.setCheckable(True)
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setToolTip("부차 옵션 펼치기/접기")
        self._btn.toggled.connect(self._on_toggled)
        lay.addWidget(self._btn)

        self._panel = QWidget()
        self._panel.setStyleSheet("background: transparent;")
        self._panel_lay = QHBoxLayout(self._panel)
        self._panel_lay.setContentsMargins(0, 0, 0, 0)
        self._panel_lay.setSpacing(8)
        self._panel.hide()
        lay.addWidget(self._panel)

    def _on_toggled(self, on: bool) -> None:
        self._btn.setText(_LABEL_OPEN if on else _LABEL_CLOSED)
        self._panel.setVisible(on)

    # ── 컨트롤 추가 ───────────────────────────────────────────────
    def add_widget(self, w: QWidget) -> QWidget:
        """접히는 영역에 컨트롤을 추가하고 그대로 반환한다."""
        self._panel_lay.addWidget(w)
        return w

    def add_label(self, text: str) -> QLabel:
        """접히는 영역에 부차 라벨(text2 색)을 추가한다."""
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {theme.active().text2}; font-size: 12px;")
        self._panel_lay.addWidget(lbl)
        return lbl
