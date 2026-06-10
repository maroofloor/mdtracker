"""도메인 모델 — 팀 전체가 공유하는 데이터 계약의 일부.

OCR 파이프라인·통계 엔진·UI가 모두 이 모델을 주고받는다.
허용값(상수)을 한곳에 모아 경계면 불일치를 방지한다.
"""

from dataclasses import dataclass
from typing import Optional

# 허용값 — 검증·UI 드롭다운·OCR 파싱이 공유한다
# 'unknown' = OCR 복구 경로(R1/R2)가 결과를 놓친 듀얼을 미상으로 발행한 것.
# NULL 대신 sentinel 값을 써서 스키마 NOT NULL을 유지한다 (설계 §6).
RESULTS = ("win", "loss", "draw", "unknown")
COIN_TOSS_RESULTS = ("win", "loss")         # 코인토스 승/패 (내가 토스를 이겼는지)
COIN_RESULTS = ("first", "second", "unknown")  # 선공 / 후공 (미상 발행 시 'unknown')
EVENT_TYPES = ("ranked", "event", "casual", "wcs")
SOURCES = ("manual", "ocr")


@dataclass
class Match:
    """한 판의 대전 기록.

    source='ocr'인 경우 ocr_confidence가 채워지고, 신뢰도가 낮으면
    confirmed=False로 저장되어 사용자 교정 대상이 된다.
    opponent_deck이 미확정(퍼지매칭 실패)이면 opponent_raw에 OCR 원문을 보존한다.
    """

    played_at: str                          # ISO8601 (예: "2026-06-02T21:30:00")
    my_deck: str
    opponent_deck: str
    coin_result: str                        # 'first' | 'second' | 'unknown' (선공/후공)
    result: str                             # 'win' | 'loss' | 'draw' | 'unknown'
    coin_toss: Optional[str] = None         # 'win' | 'loss' — 내가 코인토스를 이겼는지
    event_type: str = "ranked"              # 'ranked' | 'event' | 'casual' | 'wcs'
    source: str = "manual"                  # 'manual' | 'ocr'
    ocr_confidence: Optional[float] = None  # 0~1, manual이면 None
    opponent_raw: Optional[str] = None      # OCR 원문 (미확정 덱명 보존)
    rank_label: Optional[str] = None        # 예: "플래티넘1"
    season: Optional[str] = None            # 예: "2026-06"
    confirmed: bool = True                  # 사용자 확정 여부 (낮은 confidence면 False)
    notes: Optional[str] = None
    id: Optional[int] = None


@dataclass
class Deck:
    """정식(canonical) 덱 명칭 룩업 항목."""

    name: str                               # canonical 명칭 (예: "스네이크아이")
    is_mine: bool = False                   # 내가 쓰는 덱 후보 표시
    id: Optional[int] = None
