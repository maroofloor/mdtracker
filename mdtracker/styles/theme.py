"""테마 시스템 — 디자인 토큰 + 런타임 교체 가능한 3개 테마.

설계 개요
---------
- 3개 테마(``neon`` / ``minimal`` / ``ygo``)를 런타임에 전환할 수 있다.
- 모든 색 토큰은 :class:`Theme` 한 곳에 모이고, ``THEMES`` 레지스트리로 관리한다.
- **하위 호환**: 기존 모듈 상수(``ACCENT``, ``BG`` 등)는 활성 테마값으로
  동기화되어 그대로 import해 쓸 수 있다. (예: ``from ..styles.theme import ACCENT``)
- :func:`set_theme` 호출 시 전역 QSS를 재적용하고
  :data:`theme_notifier` 의 ``changed`` 시그널을 발행한다.

점진적 라이브(progressive live) 정책
-----------------------------------
- 접근자(:func:`active`)/시그널(:data:`theme_notifier`)을 사용하도록 마이그레이션된
  화면은 런타임 전환 시 **즉시** 갱신된다.
- 아직 모듈 상수를 import 시점에 값으로 복사해 쓰는 화면은, 전환된 테마가
  **다음 실행부터** 반영된다(상수는 import 시점에 캡처되기 때문).
- 시작 시점에는 저장된 테마를 모듈 import 시점에 로드하므로 **모든 화면이 일관**된다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtGui import QFont, QFontDatabase

# ── 영속화 키 ─────────────────────────────────────────────────────
_SETTINGS_ORG = "MDTracker"
_SETTINGS_APP = "MDTracker"
_SETTINGS_KEY = "theme"
DEFAULT_THEME = "minimal"   # 승인된 기본 테마: B 모던 미니멀


# ── 테마 토큰 정의 ────────────────────────────────────────────────
@dataclass(frozen=True)
class Theme:
    """하나의 테마가 갖는 모든 디자인 토큰."""

    id: str
    name: str          # 화면 표시용 이름 (한국어)
    description: str    # 설정/온보딩 미리보기 설명

    # 배경 계층
    bg: str
    panel: str
    surface: str
    surface2: str
    border: str
    # 강조색
    accent: str
    accent2: str        # hover
    accent_subtle: str  # 반투명 강조
    # 결과색
    win: str
    win_bg: str
    win_dark: str       # 내보내기 등 동작 버튼 배경
    lose: str
    lose_bg: str
    lose_dark: str      # 위험 동작 버튼 배경
    import_color: str   # 가져오기 버튼 배경
    draw: str
    draw_bg: str
    # 선후공
    first: str
    second: str
    # 텍스트
    text: str
    text2: str
    text3: str
    # 특수
    row_sel: str        # 선택된 행
    row_ocr: str        # OCR 미확정 행
    ocr_act: str        # OCR 활성 상태 표시

    def consts(self) -> dict[str, str]:
        """UPPERCASE 모듈 상수명 → 값 매핑 (하위 호환용)."""
        return {
            "BG": self.bg, "PANEL": self.panel, "SURFACE": self.surface,
            "SURFACE2": self.surface2, "BORDER": self.border,
            "ACCENT": self.accent, "ACCENT2": self.accent2,
            "ACCENT_SUBTLE": self.accent_subtle,
            "WIN": self.win, "WIN_BG": self.win_bg, "WIN_DARK": self.win_dark,
            "LOSE": self.lose, "LOSE_BG": self.lose_bg,
            "LOSE_DARK": self.lose_dark, "IMPORT_COLOR": self.import_color,
            "DRAW": self.draw, "DRAW_BG": self.draw_bg,
            "FIRST": self.first, "SECOND": self.second,
            "TEXT": self.text, "TEXT2": self.text2, "TEXT3": self.text3,
            "ROW_SEL": self.row_sel, "ROW_OCR": self.row_ocr,
            "OCR_ACT": self.ocr_act,
        }


# ── 3개 테마 팔레트 ───────────────────────────────────────────────
# A안 — 게이밍 다크 네온: 현재 네이비 테마의 진화, 일렉트릭 블루 강조.
_NEON = Theme(
    id="neon", name="게이밍 네온",
    description="딥 네이비 + 일렉트릭 블루. e스포츠 트래커 감성.",
    bg="#0b0f19", panel="#131b2e", surface="#1a2235", surface2="#1f2a3f",
    border="#2a3349",
    accent="#4361ee", accent2="#3a56d4", accent_subtle="rgba(67,97,238,0.18)",
    win="#22c55e", win_bg="#052e16", win_dark="#16a34a",
    lose="#ef4444", lose_bg="#2a0f12", lose_dark="#7f1d1d",
    import_color="#0369a1", draw="#6b7280", draw_bg="#11151f",
    first="#60a5fa", second="#f97316",
    text="#e2e8f0", text2="#94a3b8", text3="#475569",
    row_sel="#1f3356", row_ocr="#231c0a", ocr_act="#22c55e",
)

# B안 — 모던 미니멀(기본): 차분한 그레이-블루, 절제된 색, 가독성 최우선.
_MINIMAL = Theme(
    id="minimal", name="모던 미니멀",
    description="차분한 그레이-블루 · 넓은 여백. 데이터 가독성 최우선.",
    bg="#10141b", panel="#161b24", surface="#1c222e", surface2="#222a38",
    border="#2b3340",
    accent="#5b8def", accent2="#4878d6", accent_subtle="rgba(91,141,239,0.14)",
    win="#3fb950", win_bg="#0d2a16", win_dark="#2ea043",
    lose="#f0544c", lose_bg="#2a1212", lose_dark="#b3261e",
    import_color="#2f81f7", draw="#8b949e", draw_bg="#1c222e",
    first="#6ca8ff", second="#f0883e",
    text="#e6edf3", text2="#9aa7b8", text3="#5b6675",
    row_sel="#1e2c44", row_ocr="#2a2410", ocr_act="#3fb950",
)

# C안 — 유희왕 테마: 다크 블루 + 골드 라인. IP 몰입감.
_YGO = Theme(
    id="ygo", name="유희왕 테마",
    description="다크 블루 + 골드 라인. 마스터듀얼 UI 모티프.",
    bg="#0a0e1a", panel="#10182b", surface="#17223b", surface2="#1d2a47",
    border="#2d3c5c",
    accent="#d4af37", accent2="#b8932b", accent_subtle="rgba(212,175,55,0.16)",
    win="#36c98d", win_bg="#06281f", win_dark="#1f9e6e",
    lose="#e0556b", lose_bg="#2a0f17", lose_dark="#8c1f33",
    import_color="#3b7dd8", draw="#8a93a8", draw_bg="#17223b",
    first="#6fb3ff", second="#f0a030",
    text="#f3ecd8", text2="#aab4c8", text3="#586a86",
    row_sel="#22335a", row_ocr="#2c2410", ocr_act="#36c98d",
)

THEMES: dict[str, Theme] = {t.id: t for t in (_NEON, _MINIMAL, _YGO)}


# ── 변경 알림 시그널 (점진적 라이브용) ─────────────────────────────
class _ThemeNotifier(QObject):
    """런타임 테마 전환을 화면들에 알린다. 인자는 새 테마 id."""

    changed = Signal(str)


theme_notifier = _ThemeNotifier()


# ── 활성 테마 상태 ────────────────────────────────────────────────
def _read_saved_theme_id() -> str:
    """QSettings에서 저장된 테마 id를 읽는다(없으면 기본값)."""
    try:
        raw = QSettings(_SETTINGS_ORG, _SETTINGS_APP).value(
            _SETTINGS_KEY, DEFAULT_THEME)
        tid = str(raw) if raw else DEFAULT_THEME
    except Exception:
        tid = DEFAULT_THEME
    return tid if tid in THEMES else DEFAULT_THEME


def _sync_globals(t: Theme) -> None:
    """활성 테마값을 UPPERCASE 모듈 상수로 동기화(하위 호환)."""
    globals().update(t.consts())


# 모듈 import 시점에 저장된 테마를 활성화 → 모든 소비 모듈이 일관된 값을 캡처.
_active: Theme = THEMES[_read_saved_theme_id()]
_sync_globals(_active)


def available_themes() -> list[Theme]:
    """선택 UI에서 쓸 전체 테마 목록."""
    return list(THEMES.values())


def get_theme(theme_id: str) -> Theme:
    """id로 테마 조회(없으면 기본 테마)."""
    return THEMES.get(theme_id, THEMES[DEFAULT_THEME])


def get_active_theme() -> Theme:
    return _active


def active() -> Theme:
    """새로 작성/마이그레이션되는 위젯이 라이브 토큰을 읽는 접근자."""
    return _active


def set_active_theme(theme_id: str) -> Theme:
    """활성 테마만 교체하고 전역 상수를 동기화한다.

    QSS 재적용·영속화·시그널 발행은 하지 않는다(:func:`set_theme` 참고).
    """
    global _active
    _active = get_theme(theme_id)
    _sync_globals(_active)
    return _active


# ── QSS 생성 ──────────────────────────────────────────────────────
def _build_qss(t: Theme) -> str:
    """활성 테마 토큰으로 전체 애플리케이션 QSS를 생성한다."""
    return f"""
/* ── 전역 기본 ──────────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {{
    background-color: {t.bg};
    color: {t.text};
    font-family: "Noto Sans KR";
    font-size: 12px;
}}

/* ── 탭 ─────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {t.border};
    background-color: {t.bg};
}}
QTabBar::tab {{
    background-color: {t.panel};
    color: {t.text2};
    padding: 6px 16px;
    border: 1px solid {t.border};
    border-bottom: none;
    min-width: 72px;
    font-size: 12px;
    font-family: "Noto Sans KR";
}}
QTabBar::tab:selected {{
    background-color: {t.bg};
    color: {t.text};
    border-bottom: 2px solid {t.accent};
}}
QTabBar::tab:hover:!selected {{
    background-color: {t.surface};
    color: {t.text};
}}

/* ── 그룹박스 ────────────────────────────────────────────────── */
QGroupBox {{
    background-color: {t.panel};
    border: 1px solid {t.border};
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 6px;
}}
QGroupBox::title {{
    color: {t.text2};
    subcontrol-origin: margin;
    left: 10px;
    font-size: 11px;
}}

/* ── 테이블 ──────────────────────────────────────────────────── */
QTableWidget {{
    background-color: {t.bg};
    gridline-color: transparent;
    color: {t.text};
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
    background-color: {t.row_sel};
    color: {t.text};
}}
QHeaderView::section {{
    background-color: {t.panel};
    color: {t.text3};
    border: none;
    border-bottom: 1px solid {t.border};
    padding: 6px 8px;
    font-size: 11px;
    font-weight: 600;
    font-family: "Noto Sans KR";
}}
QHeaderView {{
    background-color: {t.panel};
}}

/* ── 버튼 ────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {t.surface};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
    font-family: "Noto Sans KR";
}}
QPushButton:hover {{
    background-color: {t.surface2};
    color: {t.text};
}}
QPushButton:pressed {{
    background-color: {t.bg};
}}
QPushButton:checked {{
    background-color: {t.accent};
    border-color: {t.accent};
    color: #ffffff;
}}
QPushButton:disabled {{
    color: {t.text3};
    background-color: {t.panel};
    border-color: {t.border};
}}

/* ── 콤보박스 ────────────────────────────────────────────────── */
QComboBox {{
    background-color: {t.surface};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
    font-family: "Noto Sans KR";
    selection-background-color: {t.accent};
}}
QComboBox:focus {{
    border-color: {t.accent};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background-color: {t.panel};
    color: {t.text};
    border: 1px solid {t.border};
    selection-background-color: {t.accent};
    outline: none;
    font-family: "Noto Sans KR";
}}

/* ── 입력 필드 ───────────────────────────────────────────────── */
QLineEdit, QDateTimeEdit {{
    background-color: {t.surface};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
    font-family: "Noto Sans KR";
}}
QLineEdit:focus, QDateTimeEdit:focus {{
    border-color: {t.accent};
}}

/* ── 스크롤바 ────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {t.bg};
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t.border};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {t.bg};
    height: 6px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {t.border};
    border-radius: 3px;
    min-width: 20px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── 레이블 ──────────────────────────────────────────────────── */
QLabel {{
    color: {t.text};
    background-color: transparent;
    font-family: "Noto Sans KR";
}}

/* ── 체크박스 ────────────────────────────────────────────────── */
QCheckBox {{
    color: {t.text};
    font-family: "Noto Sans KR";
}}
QCheckBox::indicator:checked {{
    background-color: {t.accent};
    border: 1px solid {t.accent};
    border-radius: 3px;
}}

/* ── 기타 ────────────────────────────────────────────────────── */
QSplitter::handle {{ background-color: {t.border}; }}
QDialog {{ background-color: {t.panel}; }}
QMessageBox {{ background-color: {t.panel}; }}
QCalendarWidget {{ background-color: {t.panel}; color: {t.text}; }}
QToolTip {{
    background-color: {t.panel};
    color: {t.text};
    border: 1px solid {t.border};
    font-size: 11px;
    font-family: "Noto Sans KR";
}}
"""


# ── 폰트 ──────────────────────────────────────────────────────────
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


# ── 테마 적용 / 전환 ──────────────────────────────────────────────
def apply_theme(app, theme_id: str | None = None) -> None:
    """폰트 로드 후 활성(또는 지정) 테마의 QSS를 app에 적용.

    앱 시작 시 main.py에서 호출. ``theme_id`` 를 주면 그 테마로 전환한다.
    """
    if theme_id is not None:
        set_active_theme(theme_id)
    load_fonts()
    font = QFont("Noto Sans KR", 9)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    app.setStyleSheet(_build_qss(_active))


def set_theme(app, theme_id: str) -> Theme:
    """런타임 테마 전환 — 전역 QSS 재적용 + 영속화 + 시그널 발행.

    설정 화면 등에서 호출. 마이그레이션된 화면은 ``theme_notifier.changed`` 를
    구독해 즉시 갱신할 수 있고, 그렇지 않은 화면은 다음 실행부터 반영된다.
    """
    t = set_active_theme(theme_id)
    if app is not None:
        app.setStyleSheet(_build_qss(t))
    try:
        QSettings(_SETTINGS_ORG, _SETTINGS_APP).setValue(_SETTINGS_KEY, t.id)
    except Exception:
        pass
    theme_notifier.changed.emit(t.id)
    return t
