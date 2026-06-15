"""카드 아트 서브시스템 — YGOPRODeck API로 덱별 대표 카드 이미지를 확보·캐시.

- 데이터/통계/OCR 로직과 독립적이며 Qt에 의존하지 않는다(UI 위젯은 ui 패키지).
- 자동 매핑은 archetypes.py의 한↔영 시드 표에 있는 덱만 (임의 추측 금지).
- 이미지는 개인용 로컬 캐시에만 저장한다(번들/재배포·핫링크 금지).
"""

from .service import CardArtService

__all__ = ["CardArtService"]
