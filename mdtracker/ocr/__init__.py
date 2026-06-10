"""OCR 파이프라인 — 화면 캡처로 Master Duel 대전 결과(승/패·선후공) 자동 인식.

반자동: result(VICTORY/DEFEAT 템플릿) + coin_result("당신이 선공/후공입니다" OCR)만
자동 추출하고, 상대 덱은 수동 입력. tesseract 미설치 시 import는 되며 실제 호출 시점에
의존성 오류가 난다(수동 입력 폴백은 UI가 담당).

근거/검증: _workspace/02_ocr_research.md
"""

from .config import OcrConfig
from .engine import OcrEngine, OcrResult, to_match_fields

__all__ = ["OcrConfig", "OcrEngine", "OcrResult", "to_match_fields", "OcrPoller"]


def __getattr__(name):
    # OcrPoller는 PySide6에 의존 → 필요할 때만 로드(엔진만 쓰는 곳은 Qt 불필요)
    if name == "OcrPoller":
        from .poller import OcrPoller
        return OcrPoller
    raise AttributeError(name)
