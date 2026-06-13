"""모던 네이비 대시보드 테마 — 디자인 토큰 + 전체 QSS."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

# ── 기본 팔레트 (Deep Navy) ────────────────────────────────────────
BG      = "#0b0f19"   # 최심층 배경 (윈도우)
PANEL   = "#131b2e"   # 패널/카드
SURFACE = "#1a2235"   # 테이블 기본 행
SURFACE2= "#1f2a3f"   # 테이블 교대 행
BORDER  = "#2a3349"   # 구분선

# ── 강조색 (Electric Blue) ────────────────────────────────────────
ACCENT  = "#4361ee"
ACCENT2 = "#3a56d4"   # hover
ACCENT_SUBTLE = "rgba(67,97,238,0.15)"

# ── 결과 색 ──────────────────────────────────────────────────────
WIN     = "#22c55e"
WIN_BG  = "#052e16"
LOSE    = "#ef4444"
LOSE_BG = "#fff1f2"
DRAW    = "#6b7280"
DRAW_BG = "#f9fafb"

# ── 선후공 색 ─────────────────────────────────────────────────────
FIRST   = "#60a5fa"   # 선공
SECOND  = "#f97316"   # 후공

# ── 텍스트 ───────────────────────────────────────────────────────
TEXT    = "#e2e8f0"
TEXT2   = "#94a3b8"
TEXT3   = "#475569"

# ── 특수 ─────────────────────────────────────────────────────────
ROW_SEL = "#1f3356"   # 선택된 행
ROW_OCR = "#231c0a"   # OCR 미확정 행
OCR_ACT = "#22c55e"   # OCR 활성 상태 표시

_FONT_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"


def load_fonts() -> None:
    """Noto Sans KR 폰트 로드 — 앱 시작 시 한 번만 실행."""
    for fname in (
        "NotoSansKR-VariableFont_wght.ttf",
        "static/NotoSansKR-Regular.ttf",
        "static/NotoSansKR-Medium.ttf",
        "static/NotoSansKR-Bold.ttf",
    ):
        path = _FONT_DIR / fname
        if path.exists():
            QFontDatabase.addApplicationFont(str(path))


_QSS = f"""
/* ── 전역 기본 ──────────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Noto Sans KR";
    font-size: 12px;
}}

/* ── 탭 ─────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background-color: {BG};
}}
QTabBar::tab {{
    background-color: {PANEL};
    color: {TEXT2};
    padding: 6px 16px;
    border: 1px solid {BORDER};
    border-bottom: none;
    min-width: 72px;
    font-size: 12px;
    font-family: "Noto Sans KR";
}}
QTabBar::tab:selected {{
    background-color: {BG};
    color: {TEXT};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover:!selected {{
    background-color: {SURFACE};
    color: {TEXT};
}}

/* ── 그룹박스 ────────────────────────────────────────────────── */
QGroupBox {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 6px;
}}
QGroupBox::title {{
    color: {TEXT2};
    subcontrol-origin: margin;
    left: 10px;
    font-size: 11px;
}}

/* ── 테이블 ──────────────────────────────────────────────────── */
QTableWidget {{
    background-color: {BG};
    gridline-color: transparent;
    color: {TEXT};
    border: none;
    font-size: 12px;
    font-family: "Noto Sans KR";
}}
QTableWidget::item {{
    padding: 0 8px;
    border: none;
    min-height: 48px;
}}
QTableWidget::item:selected {{
    background-color: {ROW_SEL};
    color: {TEXT};
}}
QHeaderView::section {{
    background-color: {PANEL};
    color: {TEXT3};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 8px;
    font-size: 11px;
    font-weight: 600;
    font-family: "Noto Sans KR";
}}
QHeaderView {{
    background-color: {PANEL};
}}

/* ── 버튼 ────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
    font-family: "Noto Sans KR";
}}
QPushButton:hover {{
    background-color: #1e2c47;
    color: {TEXT};
}}
QPushButton:pressed {{
    background-color: #16202f;
}}
QPushButton:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    color: #ffffff;
}}
QPushButton:disabled {{
    color: {TEXT3};
    background-color: {PANEL};
    border-color: {BORDER};
}}

/* ── 콤보박스 ────────────────────────────────────────────────── */
QComboBox {{
    background-color: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
    font-family: "Noto Sans KR";
    selection-background-color: {ACCENT};
}}
QComboBox:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background-color: {PANEL};
    color: {TEXT};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
    outline: none;
    font-family: "Noto Sans KR";
}}

/* ── 입력 필드 ───────────────────────────────────────────────── */
QLineEdit, QDateTimeEdit {{
    background-color: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
    font-family: "Noto Sans KR";
}}
QLineEdit:focus, QDateTimeEdit:focus {{
    border-color: {ACCENT};
}}

/* ── 스크롤바 ────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {BG};
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {BG};
    height: 6px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 3px;
    min-width: 20px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── 레이블 ──────────────────────────────────────────────────── */
QLabel {{
    color: {TEXT};
    background-color: transparent;
    font-family: "Noto Sans KR";
}}

/* ── 체크박스 ────────────────────────────────────────────────── */
QCheckBox {{
    color: {TEXT};
    font-family: "Noto Sans KR";
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border: 1px solid {ACCENT};
    border-radius: 3px;
}}

/* ── 기타 ────────────────────────────────────────────────────── */
QSplitter::handle {{ background-color: {BORDER}; }}
QDialog {{ background-color: {PANEL}; }}
QMessageBox {{ background-color: {PANEL}; }}
QCalendarWidget {{ background-color: {PANEL}; color: {TEXT}; }}
QToolTip {{
    background-color: {PANEL};
    color: {TEXT};
    border: 1px solid {BORDER};
    font-size: 11px;
    font-family: "Noto Sans KR";
}}
"""


# ── UI 스케일 (0.75 ~ 1.5) ───────────────────────────────────────
_ui_scale: float = 1.0


def get_ui_scale() -> float:
    return _ui_scale


def set_ui_scale(scale: float) -> None:
    global _ui_scale
    _ui_scale = max(0.75, min(1.5, round(float(scale), 2)))


def sp(base: int) -> int:
    """스케일 적용 픽셀 크기 반환."""
    return max(1, round(base * _ui_scale))


def apply_theme(app) -> None:
    """Noto Sans KR 폰트 로드 후 전체 QSS 적용."""
    load_fonts()
    font = QFont("Noto Sans KR", 9)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    app.setStyleSheet(_QSS)
