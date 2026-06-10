"""OCR 설정 — ROI·임계값·전처리 파라미터를 코드 밖으로 외부화한다.

실제 플레이 영상(1920×1080, 한글 클라이언트) 분석으로 확정한 기본값.
근거: _workspace/02_ocr_research.md. 해상도/레이아웃이 바뀌면 JSON으로 덮어쓴다.

ROI는 해상도 독립적으로 비율(0~1)로 저장하고, 캡처 시 실제 픽셀로 환산한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Tuple

# (x0, y0, x1, y1) — 화면 크기에 대한 비율
Roi = Tuple[float, float, float, float]


def default_config_path() -> Path:
    """런타임 OCR 설정 표준 위치 = 프로젝트 루트의 ocr_config.json.

    앱(record_view)과 진단 스크립트(ocr_probe)가 같은 파일을 공유한다.
    """
    return Path(__file__).resolve().parents[2] / "ocr_config.json"


@dataclass
class OcrConfig:
    # --- 캡처 ---
    monitor: int = 1                       # mss 모니터 인덱스 (1=주 모니터). window_title 설정 시 무시됨
    window_title: str = "masterduel"       # 창 제목으로 게임 창 자동 감지 (빈 문자열이면 monitor 방식 사용)
    poll_interval: float = 0.25            # 폴링 주기(초). 짧은 결과 화면(빠른 확인) 누락 방지

    # --- 선/후공 (한글 텍스트 OCR) ---
    # "당신이 선공/후공입니다" 텍스트 줄만 타이트하게 (위쪽 포털 노이즈 배제)
    coin_roi: Roi = (0.26, 0.64, 0.74, 0.715)
    coin_bin_threshold: int = 190          # 진단/미리보기용 단일 임계
    # 실게임 페이드 인/아웃 대비: 여러 임계로 OCR해 가장 신뢰 높은 판독 채택
    coin_bin_thresholds: Tuple[int, ...] = (150, 175, 200, 225)
    coin_upscale: int = 3                  # OCR 전 업스케일 배율
    # 성능: ROI에 밝은 글자가 거의 없으면(빈 화면) OCR 자체를 건너뜀
    coin_min_text_ratio: float = 0.004     # 밝은 픽셀 비율 하한
    coin_early_exit_conf: float = 0.90     # 이 신뢰 이상이면 남은 임계 시도 생략
    tess_lang: str = "kor"
    tess_psm: int = 7                      # 단일 텍스트 줄

    # --- 코인토스 승/패 (토스 선택 화면 OCR) ---
    # "선공/후공을 선택해주세요"(내가 선택=승) vs "상대가 …선택하고 있습니다"(상대 선택=패)
    # 확정 문구보다 폭이 넓어 가로로 더 넓은 ROI 사용
    toss_roi: Roi = (0.18, 0.61, 0.82, 0.71)
    # Windows에서 tesseract.exe가 PATH에 없을 때 지정 (예: r"C:\Program Files\Tesseract-OCR\tesseract.exe").
    # 빈 문자열이면 PATH에서 찾는다 (Linux/WSL 기본).
    tesseract_cmd: str = ""

    # --- 승/패 (영문 스타일 배너 → 템플릿 매칭) ---
    result_roi: Roi = (0.12, 0.40, 0.88, 0.56)
    result_bin_threshold: int = 200        # 배너 흰 글자 마스크 임계
    # 실제 VICTORY/DEFEAT는 IoU 0.9+, 시작 'DUEL' 배너는 ~0.31 → 0.5로 명확 분리
    result_match_threshold: float = 0.50   # 템플릿 IoU 최소치(미만이면 결과 없음)
    result_match_margin: float = 0.05      # 승/패 IoU 차이 최소(모호 방지)

    # --- 신뢰도 / 폴백 ---
    review_threshold: float = 0.80         # 이 미만이면 needs_review=True (교정 요청)
    result_cooldown: float = 8.0           # 결과 1회 발행 후 재발행 억제(초). 한 듀얼 중복 방지

    # --- 폴러 복구/스로틀 (설계: docs/ocr_recovery_design.md) ---
    # P1: 서버오류 한글 OCR(200~500ms)을 매주기 돌리면 실효 주기가 늘어나
    #     0.75초짜리 항복 DEFEAT 창을 놓친다 → N주기 1회로 스로틀 (8주기 ≈ 2초)
    server_error_check_cycles: int = 8
    # R1: PLAYING 중 새 토스 감지(=이전 듀얼 결과 누락 확정) OCR 스로틀 (10주기 ≈ 2.5초)
    playing_toss_check_cycles: int = 10
    # R2: 창 소멸 판정 — capture_screen이 'not_found'를 연속 N회 반환 시 (40회 ≈ 10초)
    window_gone_cycles: int = 40
    # R3: COIN 구간(토스 확인 → 선후공 확정) 정체 타임아웃(초). 실측 상한 15~25초
    coin_timeout: float = 120.0

    # --- 서버 오류 다이얼로그 ("게임 서버로부터 응답이 없습니다") ---
    # 오류 팝업 내 본문 텍스트 영역 (1920×1080 기준 스크린샷 분석값)
    server_error_roi: Roi = (0.26, 0.43, 0.74, 0.58)

    # --- 에셋 ---
    template_dir: str = field(
        default_factory=lambda: str(Path(__file__).parent / "templates")
    )

    # --- 피드백 ---
    feedback_form_url: str = ""             # Google Form URL (빈 문자열이면 비활성)

    # ---- 직렬화 ----
    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2))

    @classmethod
    def from_json(cls, path: str | Path) -> "OcrConfig":
        data = json.loads(Path(path).read_text())
        # 알 수 없는 키는 무시(전방 호환), 튜플 복원
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        for k in ("coin_roi", "result_roi"):
            if k in known and isinstance(known[k], list):
                known[k] = tuple(known[k])
        return cls(**known)

    @classmethod
    def load_or_default(cls, path: str | Path) -> "OcrConfig":
        p = Path(path)
        return cls.from_json(p) if p.exists() else cls()
