# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 앱 실행

```bash
# 일반 실행
python main.py

# 헤드리스 구성 검증 (디스플레이 없는 환경)
QT_QPA_PLATFORM=offscreen python main.py --check
```

## 테스트

테스트 파일이 생기면 아래 경로에 위치한다:

```bash
# OCR 단위 테스트 (화면/tesseract 없이 실행 가능)
.venv/bin/python tests/test_ocr.py

# UI 스모크 테스트 (헤드리스)
QT_QPA_PLATFORM=offscreen .venv/bin/python tests/test_ui_smoke.py
```

## 의존성 설치

```bash
pip install -r requirements.txt
# tesseract 바이너리 별도 설치 필요 (kor 학습데이터 포함)
# Windows: ocr_config.json의 tesseract_cmd에 경로 지정
```

---

## 아키텍처

### 계층 구조

```
main.py
└── Database (db.py)           ← SQLite 연결 + 저장소 소유
    ├── MatchRepository         ← match CRUD + 필터 조회
    └── DeckRepository          ← deck CRUD + 퍼지 매칭
mdtracker/
├── models.py                  ← 공유 도메인 모델 (Match, Deck, 허용값 상수)
├── stats.py                   ← 순수 통계 함수 (list[Match] → dict)
├── app_paths.py               ← 플랫폼별 DB/설정 경로
├── ocr/
│   ├── config.py              ← ROI·임계값 (ocr_config.json 로드)
│   ├── engine.py              ← 이미지 전처리·OCR·템플릿 매칭·DB 필드 매핑
│   ├── poller.py              ← QThread 상태 머신 (IDLE→COIN→PLAYING)
│   └── templates/             ← victory.png / defeat.png
└── ui/
    ├── main_window.py         ← 탭 호스트, QSettings, 신호 라우팅
    ├── record_view.py         ← 수동 입력·OCR 토글·표 편집·CSV 내보내기
    ├── dashboard_view.py      ← KPI/매치업/메타/추세 합성
    ├── deck_view.py           ← 덱 관리
    ├── settings_view.py       ← 창 크기·UI 스케일·피드백
    ├── ocr_panel.py           ← OCR 결과 확인 패널
    ├── labels.py              ← 영어 저장값 ↔ 한국어 표시 라벨 매핑
    └── styles/theme.py        ← QSS 테마·색상 상수
```

### 핵심 데이터 흐름

1. **수동 입력**: `RecordView` → `MatchRepository.add()` → `data_changed` 시그널 → `DashboardView.refresh()`
2. **OCR 자동 입력**: `OcrPoller`(QThread) → `match_detected` 시그널 → `RecordView`(확인 팝업) → `MatchRepository.add()`
3. **통계 표시**: 탭 전환 시 `refresh()` 호출 → `MatchRepository.list()` → `stats.py` 순수 함수 → 위젯 렌더링

### OCR 상태 머신

`OcrPoller`는 세 상태를 순서대로 거쳐야만 매치를 발행한다:
- **IDLE**: `coin_toss`('win'/'loss') 감지 대기
- **COIN**: `coin_result`('first'/'second') 감지 대기
- **PLAYING**: 승패 결과 감지 → 발행 후 IDLE 복귀

서버 오류 팝업 감지 시 어느 상태에서든 발행 없이 IDLE로 초기화된다.

### 중요한 필드 구분

- `coin_toss`: 내가 코인토스를 이겼는지 (`'win'`/`'loss'`)
- `coin_result`: 실제 선후공 (`'first'`/`'second'`)
- 두 필드는 서로 다른 개념이므로 혼용하지 않는다.

---

## 핵심 규칙

- **UI는 직접 SQL을 쓰지 않는다.** `Database.matches`, `Database.decks`만 호출한다.
- **화면 표시 텍스트는 한국어, DB 저장값은 영어.** `labels.py`의 매핑을 통해 변환한다. UI 라벨 문자열을 DB에 직접 넣지 않는다.
- **`stats.py`는 순수 함수다.** DB 접근 없이 `list[Match]`를 입력으로 받아 계산만 한다.
- **OCR 자동 저장에서 상대 덱을 추정하지 않는다.** 기본값은 `미정`, 사용자가 교정한다.
- **새 스레드/타이머 추가 시** `RecordView.shutdown()` 종료 경로에 반드시 정리 코드를 추가한다.
- **tesseract·mss는 지연 import.** 모듈 로드와 단위 테스트가 바이너리/화면 없이 가능하도록 유지한다.
- **Windows tesseract 경로는 코드에 하드코딩하지 않는다.** `ocr_config.json` 또는 `OcrConfig.tesseract_cmd`를 사용한다.

## 설정 파일

- `ocr_config.json` (루트): tesseract 경로, 모니터 번호, 피드백 URL 등 환경별 OCR 설정
- `app_settings` (DB): 세션 간 UI 상태 영속 (`Database.get_setting`/`set_setting`)
- `QSettings("MDTracker", "MDTracker")`: 창 크기·UI 스케일 영속
