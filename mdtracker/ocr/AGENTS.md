# OCR PACKAGE GUIDE

## OVERVIEW

실제 Master Duel 화면에서 코인토스 승패, 선후공, 승패 결과, 서버 오류 팝업을 추출하는 패키지다. 잘못된 자동기록이 최대한 발생하지 않도록 하되, 잘못된 자동기록보다 미인식과 사용자 교정이 우선이다.

## STRUCTURE

```text
ocr/
├── config.py              # ROI, 임계값, tesseract, 템플릿 경로
├── engine.py              # 이미지 전처리, OCR, 템플릿 매칭, DB 필드 매핑
├── poller.py              # QThread 상태 머신, 실시간 신호 병합
└── templates/
    ├── victory.png
    └── defeat.png
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| ROI/임계값 변경 | `config.py` | 기본값은 실영상 근거다. JSON 덮어쓰기와 호환되어야 한다. |
| 단일 프레임 인식 | `engine.py` | `extract_from_image()`가 테스트 가능한 경로다. |
| 실시간 자동 저장 흐름 | `poller.py` | 상태별로 필요한 recognizer만 호출한다. |
| 회귀 테스트 | `tests/test_ocr.py` | `_workspace/frames` 샘플과 템플릿을 사용한다. |
| 연구 근거 | `_workspace/02_ocr_research.md` | 새 해상도나 ROI 판단 시 확인한다. |
| Windows ROI 진단 | `_workspace/ocr_probe.py` | 루트 `ocr_config.json`과 같은 설정을 공유한다. |

## CONVENTIONS

- `OcrResult`는 UI/DB가 추정 없이 소비하는 계약이다. 필드 의미를 바꾸면 `tests/test_ocr.py`와 `RecordView`까지 함께 점검한다.
- `coin_toss`는 내가 토스를 이겼는지(`win`/`loss`)이고, `coin_result`는 실제 선후공(`first`/`second`)이다. 두 필드를 섞지 않는다.
- `recognize_coin()`은 확정 문구 `"당신이 선공/후공입니다"`만 선후공으로 인정한다.
- `recognize_coin_toss()`는 선택 화면에서 토스 승패만 판별한다. 확정 문구는 토스 신호가 아니다.
- 승패 결과는 tesseract가 아니라 `victory.png`/`defeat.png` 템플릿 IoU로 판별한다.
- `to_match_fields()`의 `ocr_confidence`는 존재하는 신호의 최솟값이다. 보수적 신뢰도 정책을 유지한다.
- tesseract, mss는 지연 import 경로를 유지해 모듈 import와 단위 테스트가 화면/바이너리 없이 가능하게 둔다.
- 서버 오류 팝업은 매치 발행 없이 폴러 상태만 `IDLE`로 되돌리는 신호다.

## ANTI-PATTERNS

- 모호한 화면을 낮은 임계값으로 강제 인식하지 말 것.
- `"선공"`과 `"후공"`이 함께 나온 선택/대기 문구를 선후공 확정으로 처리하지 말 것.
- 템플릿이 없을 때 예외 대신 결과 없음 경로가 동작해야 한다.
- `poller.py`에서 모든 recognizer를 매 프레임 호출해 오탐률과 부하를 올리지 말 것.
- Windows tesseract 경로를 코드에 하드코딩하지 말 것. `ocr_config.json` 또는 `OcrConfig.tesseract_cmd`를 사용한다.
- `OcrConfig.from_json()`의 전방 호환 정책을 깨고 알 수 없는 로컬 설정 키 때문에 실행을 실패시키지 말 것.

## COMMANDS

```bash
.venv/bin/python tests/test_ocr.py
.venv/bin/python -m pytest tests/test_ocr.py
```

## NOTES

- `poll_interval` 기본값은 짧은 결과 화면 누락 방지 목적이다.
- `result_cooldown`은 한 듀얼의 중복 발행 방지 장치다.
- 서버 오류 팝업 감지 시 발행 없이 상태를 `IDLE`로 초기화한다.
- 루트 `assets/victory.png`, `assets/defeat.png`는 원본/자료 성격이고 런타임 템플릿 경로는 기본적으로 `mdtracker/ocr/templates/`다.
