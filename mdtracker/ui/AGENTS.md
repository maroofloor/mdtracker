# UI PACKAGE GUIDE

## OVERVIEW

PySide6 기반 데스크톱 UI다. 좌측 사이드바, 프레임리스 메인 윈도우, 기록 탭, OCR 확인 패널, 통계 대시보드, 덱 관리, 설정 화면으로 구성된다.

## STRUCTURE

```text
ui/
├── main_window.py        # 탭 호스트, 신호 라우팅, QSettings 저장
├── record_view.py        # 수동 입력, OCR 토글, 표 편집, CSV export
├── manual_dialog.py      # 수동 기록 추가 / 기존 기록 교정 모달
├── ocr_panel.py          # OCR 감지 결과 확인 패널
├── dashboard_view.py     # KPI/매치업/메타/추세 합성 화면
├── settings_view.py      # 창 크기, UI 스케일, 피드백 다이얼로그
├── *_view.py             # 각 통계/관리 위젯
├── labels.py             # 값과 표시 라벨 매핑
├── sidebar.py
└── title_bar.py
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| 탭 추가/라우팅 | `main_window.py` | `QStackedWidget`, `Sidebar`, refresh 흐름을 함께 수정한다. |
| 기록 입력/편집 | `record_view.py` | 수동 저장, OCR 자동 저장, inline edit가 한 화면에 있다. |
| 수동 입력 모달 | `manual_dialog.py` | `labels.py` 매핑과 `DeckRepository.list_names()`로 콤보를 채운다. |
| 표시 라벨 변경 | `labels.py` | 저장값은 영어 enum, 화면은 한국어 라벨이다. |
| 통계 화면 | `dashboard_view.py`, `kpi_view.py`, `matchup_view.py`, `meta_view.py`, `trend_view.py` | DB에서 읽고 `stats.py` 결과를 표시한다. |
| 덱 관리 | `deck_view.py` | `DeckRepository`만 사용한다. |
| 설정/피드백 | `settings_view.py` | `size_changed`, `scale_changed` 신호와 `ocr_config.json`의 피드백 URL을 사용한다. |
| 스모크 검증 | `tests/test_ui_smoke.py` | `QT_QPA_PLATFORM=offscreen`으로 실행한다. |

## CONVENTIONS

- 화면 표시 텍스트는 한국어를 유지한다. 저장값은 `models.py`의 영어 허용값을 사용한다.
- 코인토스 승패(`coin_toss`)와 선후공(`coin_result`)은 UI 라벨도 분리해서 표시한다.
- UI는 DB에 직접 SQL을 쓰지 않는다. `Database.matches`와 `Database.decks`만 호출한다.
- 기록 변경 후에는 `RecordView.data_changed`를 통해 통계 화면이 새로고침되게 한다.
- 통계 위젯은 `refresh()` 메서드를 제공하고 탭 전환 시 재계산 가능해야 한다.
- `QSettings("MDTracker", "MDTracker")`는 창 크기와 UI 스케일 저장에 사용된다.
- `RecordView.shutdown()`은 닫기 시 OCR 폴러를 정리하는 경로다. 새 스레드/타이머를 추가하면 종료 경로도 추가한다.
- 색상과 공통 스타일은 가능한 `mdtracker/styles/theme.py` 상수를 사용한다.
- `settings_view.py`에서 저장하는 OCR 설정은 루트 `ocr_config.json`과 `app_settings`의 역할을 구분한다.

## ANTI-PATTERNS

- UI 라벨 문자열을 DB 저장값으로 넣지 말 것. `labels.py`의 매핑을 사용한다.
- OCR 자동 저장에서 상대 덱을 추정하지 말 것. 기본은 `미정`, 사용자가 교정한다.
- `MainWindow.closeEvent()`에서 `RecordView.shutdown()` 호출을 제거하지 말 것.
- 테스트 없이 `record_view.py`의 테이블 컬럼 순서를 바꾸지 말 것. 스모크 테스트가 컬럼 의미를 검증한다.
- WSL에서 OCR 토글이 실게임 캡처까지 검증됐다고 말하지 말 것.
- 피드백 URL이나 로컬 tesseract 경로 같은 환경 설정을 코드 상수로 고정하지 말 것.

## COMMANDS

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python tests/test_ui_smoke.py
QT_QPA_PLATFORM=offscreen .venv/bin/python main.py --check
```

## NOTES

- `RecordView`는 큰 파일이다. 변경 시 관련 helper와 테스트 위치를 먼저 찾고 작은 범위로 수정한다.
- `DashboardView` 내부는 KPI, 매치업, 메타, 추세 위젯을 소유한다.
- `SettingsView` 피드백 팝업은 `PySide6.QtWebEngineWidgets`가 없거나 URL이 비어 있으면 오류 라벨을 보여준다.
- 프레임리스 윈도우와 둥근 마스크가 있으므로 resize/close 이벤트 변경은 실제 구성 검증이 필요하다.
- UI 아이콘/윈도우 아이콘 변경은 `assets/icon.png`, `assets/icon.ico`와 패키징 산출물까지 경로를 확인한다.
