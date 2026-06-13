# MDTracker 수정 작업 프롬프트 (Claude Code용)

아래 내용을 Claude Code 세션에 그대로 붙여넣어 사용하세요.
진단 근거: `diagnostics_report.html` 참조.

---

너는 `F:\AI\mdtracker` (PySide6 + SQLite + OCR 기반 Master Duel 승률 트래커)를 정비한다.
**CLAUDE.md의 작업 지침을 반드시 따른다**: 정밀한 수정(필요한 부분만), 단순성 우선,
변경 전 가정 명시, 각 단계마다 검증. 무관한 리팩토링·포맷 변경 금지.

검증 기준(공통): 각 변경 후 헤드리스 구성이 깨지지 않아야 한다.
```
QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe main.py --check
```
출력에 "메인 윈도우 구성 성공"이 나오면 통과. (Windows 콘솔에서 한글이 깨져 보여도 무방)

작업은 우선순위 순으로 진행하고, 각 항목을 독립 커밋 단위로 다룬다.
**모호하거나 실기 확인이 필요한 항목(특히 M1)은 임의로 단정하지 말고 먼저 질문/확인한다.**

---

## P1 — [HIGH] OCR 상태머신 타임아웃·복구 (poller.py)

**문제**: `mdtracker/ocr/poller.py` docstring은 "PLAYING이 `playing_timeout` 초과 시 링 버퍼
소급 검사 후 IDLE 복귀"를 명시하지만 구현이 없다. `_state_entered_at`은 죽은 변수이고,
상태를 되돌리는 경로는 서버 오류 팝업뿐이다. → COIN/PLAYING에서 화면을 놓치면 영구 정체,
이후 모든 듀얼이 기록되지 않는다.

**작업**:
1. `OcrConfig`(`ocr/config.py`)에 타임아웃 파라미터 추가:
   `coin_state_timeout: float = 30.0`, `playing_state_timeout: float = 600.0`.
2. `OcrPoller`의 메인 루프 또는 각 상태 핸들러에서 `now - self._state_entered_at`이
   해당 타임아웃을 초과하면 `_reset_state()`로 IDLE 복귀하도록 구현한다.
   (`_state_entered_at`을 실제로 사용하게 만든다.)
3. docstring의 "링 버퍼 소급 검사"는 **구현하지 않으므로 문구를 제거**하고, 실제 동작
   (타임아웃 시 IDLE 복귀)으로 정확히 다시 기술한다. 코드-문서 계약을 일치시킨다.

**제약**: 링 버퍼 같은 신규 추상화는 추가하지 않는다(단순성 우선). 타임아웃 복귀만 구현.
**검증**: `--check` 통과 + (가능하면) poller 단위 로직을 수동 점검할 수 있는 짧은 설명 추가.

---

## P2 — [HIGH] DB/설정 경로를 app_paths로 연결 (main.py)

**문제**: `mdtracker/app_paths.py`는 `%LOCALAPPDATA%/MDTracker` 경로를 정확히 산출하도록
작성됐으나 **호출처가 0건**이다. `main.py:41`은 DB를 프로젝트 폴더 `data/mdtracker.db`에
직접 저장한다 → 패키징 후 읽기전용 설치 폴더에서 쓰기 실패.

**작업**:
1. `main.py`에서 `from mdtracker.app_paths import default_db_path`를 사용해
   `DB_PATH = default_db_path()`로 교체. 상위 폴더 생성(`mkdir parents=True`)은 유지.
2. **마이그레이션 안전장치**: 신규 경로에 DB가 없고 기존 `<프로젝트>/data/mdtracker.db`가
   존재하면, 기존 파일을 신규 경로로 복사(이동 아님)한다. 기존 사용자의 기록 유실 방지.
   복사 로직은 main.py 진입부에 최소한으로.
3. (선택, 별도 판단) OCR 설정도 `default_ocr_config_path()` 우선 + 프로젝트 루트
   `ocr_config.json` 폴백 전략이 적절한지 **먼저 제안하고 승인받은 뒤** 진행한다.
   설정은 사용자가 직접 편집하는 파일이므로 경로 변경이 혼란을 줄 수 있어 신중히.

**제약**: 동작 경로만 바꾼다. app_paths.py 내부 로직은 이미 검증된 것으로 보고 수정 최소화.
**검증**: `--check` 통과 + 신규 경로에 DB가 생성되는지, 기존 DB가 있을 때 복사되는지 확인.

---

## P3 — [MED] 게임 창 제목 매칭 견고화 (engine.py / config.py)  ※ 실기 확인 선행

**문제**: `_get_window_capture_region`이 `"masterduel" in title.lower()` 부분일치에 의존.
실제 창 타이틀이 "Yu-Gi-Oh! MASTER DUEL"처럼 공백을 포함하면 매칭 실패 → `capture_screen()`이
None을 반환하고 OCR이 조용히 무동작.

**먼저 할 일 (질문/확인)**: 실제 Master Duel 창의 정확한 타이틀 문자열을 확인해야 한다.
사용자에게 실제 창 제목을 물어보거나, 임시 진단 스니펫(win32gui.EnumWindows로 보이는 창
제목 전체 출력)을 제시해 확인을 요청한다. **임의로 기본값을 바꾸지 말 것.**

**작업(확인 후)**:
1. 비교 시 공백·대소문자를 정규화(예: 영숫자만 추출 후 비교)하여 "MASTER DUEL"도 매칭되게.
2. `window_title` 설정 시 창을 못 찾으면: (a) `monitor` 방식으로 폴백하거나
   (b) 폴러가 상태바에 "게임 창 탐지 실패"를 1회 노출(현재는 완전 무음). 둘 중 하나를 택해
   제안 후 구현.

**검증**: `--check` 통과. 실기 캡처 검증은 사용자 환경 필요 — 검증 방법을 안내.

---

## P4 — [MED] 게임 프로세스 감지의 subprocess 폴링 완화 (record_view.py)

**문제**: `_game_watch_timer`가 2초마다 `_is_game_running()`을 호출하고, 매번
`tasklist.exe`(+`pgrep`)를 subprocess로 스폰한다 → 시간당 ~1,800회 프로세스 생성, UI 끊김 우려.

**작업** (둘 중 하나, 더 단순한 쪽을 택해 제안):
- (A) 타이머 주기를 2초 → 5초로 완화. (최소 변경)
- (B) Windows에서는 이미 `win32gui`로 창을 열거하므로(P3와 연계) "창 존재 여부"로
  프로세스 감지를 대체해 subprocess 스폰을 제거.

**제약**: 자동 시작 UX(게임 감지 시 OCR 자동 ON)는 유지한다.
**검증**: `--check` 통과 + 타이머/감지 로직이 기존과 동일한 사용자 흐름을 보존하는지 확인.

---

## P5 — [MED] CSV 내보내기 인코딩 utf-8-sig로 통일 (repository.py)

**문제**: `repository.py:124` `export_csv`가 `encoding="utf-8"`(BOM 없음)이라 Excel에서
한글이 깨진다. 덱 가져오기는 `utf-8-sig`라 비일관적.

**작업**: `export_csv`의 `open(...)` 인코딩을 `"utf-8-sig"`로 변경(한 줄).
**검증**: 내보낸 CSV에 BOM이 포함되는지 확인. 기존 컬럼/포맷은 그대로.

---

## P6 — [MED] 번들 폰트 폴백 처리 (theme.py)

**문제**: `assets/fonts/`가 없어 Noto Sans KR가 로드되지 않는데 QSS는 전역으로
`font-family:"Noto Sans KR"`를 강제한다.

**작업** (둘 중 하나를 제안 후):
- (A) 폰트 파일을 실제로 동봉할 계획이면 폴더/파일 추가 안내만 하고 코드는 유지.
- (B) 동봉하지 않으면, `load_fonts()`가 폰트를 1개도 등록하지 못한 경우 QSS의
  `font-family`를 시스템 기본(예: `"Malgun Gothic", "Segoe UI", sans-serif`)으로 폴백.

**제약**: 한글 렌더링은 어느 경우든 보장되어야 한다.
**검증**: `--check` 시 QFontDatabase 경고가 줄거나 폴백이 적용되는지 확인.

---

## P7 — [LOW] 정리 묶음 (저위험, 한 커밋 가능)

1. **main.py:11-17** pandas 선임포트 try/except 블록 제거(미사용·requirements에 없음).
2. **config.py:88** `from_json`의 튜플 복원을 list 타입 필드 일반화로 확장
   (`coin_bin_thresholds`, `toss_roi`, `server_error_roi` 포함).
3. **record_view.py:430,933** "CSV 수출" → "CSV 내보내기" (덱 탭 용어와 통일).
4. **kpi_view.py:136-143** "KPI 카드 3열/3개" 주석을 실제(2개)와 일치하게 수정.
5. **CLAUDE.md** 아키텍처 트리 현행화: 누락된 `kpi_view·matchup_view·meta_view·trend_view·
   manual_dialog·sidebar·title_bar` 추가, `theme.py` 위치를 `mdtracker/styles/`로 정정.

**검증**: `--check` 통과.

---

## P8 — [LOW] 회귀 안전망: 단위 테스트 추가 (신규 tests/)

**작업**: CLAUDE.md의 테스트 경로 규약에 맞춰 최소 테스트를 추가한다.
- `tests/test_stats.py`: `win_rate_summary` / `trend_series` / `matchup_matrix` /
  `opponent_meta`의 빈 데이터·0 나누기·무승부 분모 제외·표본수(n) 정확성 검증.
- `tests/test_ocr.py`: `to_match_fields` 매핑(신뢰도 최솟값, confirmed 플래그)과
  `OcrResult.has_signal` 검증 (화면/tesseract 불필요한 순수 로직만).

**제약**: 화면·tesseract·DB 파일 없이 도는 테스트만. P1~P7 변경 후 회귀 확인용으로도 활용.
**검증**: `.venv/Scripts/python.exe tests/test_stats.py` 등 무오류 실행.

---

### 진행 방식
- P1 → P8 순서로, 각 항목 완료 시 변경 파일과 검증 결과를 요약 보고.
- P2-3(설정 경로), P3(창 제목), P4/P6(택일), P8 범위는 **착수 전 짧게 확인**받는다.
- 한 항목의 변경이 다른 동작을 깨지 않는지 매 단계 `--check`로 확인한다.
