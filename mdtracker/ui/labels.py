"""한국어 표시 라벨 ↔ canonical 값 매핑 + 콤보박스 헬퍼.

허용값(models의 상수)을 화면에 한국어로 보여주되, 저장은 canonical 값으로 한다.
모든 뷰가 이 매핑을 공유해 경계면 불일치를 막는다.
"""

from PySide6.QtWidgets import QComboBox

# 'unknown' = OCR 복구 경로가 놓친 듀얼의 미상 값 (사용자 교정 대상)
RESULT_LABELS = {"win": "승", "loss": "패", "draw": "무", "unknown": "미상"}
COIN_TOSS_LABELS = {"win": "승", "loss": "패"}          # 코인토스 승/패
COIN_LABELS = {"first": "선공", "second": "후공", "unknown": "미상"}  # 선/후공
EVENT_LABELS = {"ranked": "랭크", "event": "이벤트", "casual": "캐주얼", "wcs": "WCS"}

# WCS에서는 상대 덱을 확인할 수 없으므로 상대 덱을 이 값으로 자동 기록한다
WCS_OPP_DECK = "WCS"


def fill_combo(combo: QComboBox, label_map: dict) -> None:
    """value를 itemData로, 한국어 라벨을 표시 텍스트로 채운다."""
    combo.clear()
    for value, label in label_map.items():
        combo.addItem(label, value)


def combo_value(combo: QComboBox):
    """현재 선택의 canonical 값(itemData)을 반환."""
    return combo.currentData()


def select_value(combo: QComboBox, value) -> None:
    """canonical 값으로 콤보 선택."""
    idx = combo.findData(value)
    if idx >= 0:
        combo.setCurrentIndex(idx)


def fmt_pct(rate) -> str:
    """승률(0~1 또는 None)을 백분율 문자열로. 표본 없으면 '—'."""
    return "—" if rate is None else f"{rate * 100:.1f}%"
