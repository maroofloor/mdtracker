# Deep Interview Spec: 게임 창모드 OCR 지원

## Metadata
- Interview ID: di-mdtracker-window-resolution-001
- Rounds: 2 (+ Round 0 topology)
- Final Ambiguity Score: 22%
- Type: brownfield
- Generated: 2026-06-09
- Threshold: 20%
- Threshold Source: default
- Initial Context Summarized: no
- Status: BELOW_THRESHOLD_EARLY_EXIT (사용자 기술 결정 위임)

## Clarity Breakdown
| 차원 | 점수 | 가중치 | 가중값 |
|------|------|--------|--------|
| 목표 명확도 | 0.85 | 35% | 0.298 |
| 제약 명확도 | 0.75 | 25% | 0.188 |
| 성공 기준 | 0.70 | 25% | 0.175 |
| 컨텍스트 명확도 | 0.80 | 15% | 0.120 |
| **총 명확도** | | | **0.781** |
| **모호도** | | | **22%** |

## Topology
| 컴포넌트 | 상태 | 설명 | 비고 |
|----------|------|------|------|
| 게임 창모드 OCR | active | masterduel 창 자동 감지 → 해당 영역만 OCR 캡처 | 이번 스펙 범위 |
| 해상도 적응형 ROI | deferred | 해상도별 ROI 스케일링 | QHD까지 작동하므로 이후 필요 시 |
| 앱 창 상태 유지 | deferred | MDTracker 앱 창 위치/상태 저장 | 요청에 포함되지 않음 |

## Goal
`masterduel` 창 제목을 가진 게임 윈도우를 Win32 API로 자동 감지하고, 그 클라이언트 영역(title bar·테두리 제외)만 mss로 캡처하여 OCR이 창모드에서도 전체화면과 동일하게 동작하도록 한다.

## Constraints
- 창 감지: `pywin32` (`win32gui.FindWindow`) 사용, 창 제목 `"masterduel"` (대소문자 무관 검색)
- 캡처 영역: 클라이언트 영역(`GetClientRect` + `ClientToScreen`) — title bar·테두리 제외
- 창 미발견 시: 폴링 이터레이션 스킵 (상태 변경 없음, 에러 팝업 없음)
- ROI 좌표: 변경 없음 — 게임 콘텐츠 기준 상대 좌표로 그대로 유지
- DPI 처리: `ctypes.windll.shcore.GetScaleFactorForMonitor` 또는 Qt의 `devicePixelRatio`로 논리→물리 좌표 변환
- 창 제목은 `ocr_config.json`에 `"window_title"` 필드로 설정 가능 (기본값 `"masterduel"`)
- 기존 `monitor` 필드는 유지 (전체화면 모드 폴백 또는 멀티모니터 대응용)

## Non-Goals
- 해상도 변화에 따른 ROI 자동 스케일링 (deferred)
- 앱 창 위치/최대화 상태 저장 (deferred)
- 멀티모니터에서 게임 창이 어느 모니터에 있는지 자동 감지
- 게임 창 크기가 변경될 때 실시간 재감지

## Acceptance Criteria
- [ ] `masterduel` 창이 창모드로 실행 중일 때 OCR 폴링이 정상 동작한다 (코인토스·승패 인식)
- [ ] `masterduel` 창이 없으면 폴링이 조용히 스킵되고 UI에 에러가 표시되지 않는다
- [ ] 전체화면 모드(현재 동작)는 그대로 유지된다 — 기존 `monitor` 설정 경로 회귀 없음
- [ ] `ocr_config.json`에 `window_title` 필드 추가·제거 시 앱이 정상 기동한다
- [ ] DPI 150% 환경에서도 캡처 영역이 올바른 물리 픽셀 좌표를 사용한다

## Assumptions Exposed & Resolved
| 가정 | 질문 | 결정 |
|------|------|------|
| 창 감지 방식 | 자동 vs 수동 설정 | Win32 자동 감지 |
| 창 제목 | 알 수 없음 | `"masterduel"` (사용자 확인) |
| ROI 기준점 | 모니터 절대좌표 vs 게임창 상대좌표 | 게임창 상대좌표로 통일 (클라이언트 영역 캡처) |
| 창 미발견 처리 | 에러 표시 vs 조용히 스킵 | 조용히 스킵 (사용자 위임) |
| 나머지 기술 결정 | 사용자에게 질문 | 사용자가 구현 전체 위임 |

## Technical Context
**변경 대상 파일:**
- `mdtracker/ocr/engine.py:262-266` — `mss.monitors[cfg.monitor]` → 창 감지 결과 bounding box
- `mdtracker/ocr/config.py:31` — `OcrConfig`에 `window_title: str = "masterduel"` 필드 추가
- `ocr_config.json` — `"window_title": "masterduel"` 키 추가
- `requirements.txt` — `pywin32` 추가 (이미 있으면 스킵)

**핵심 구현 패턴:**
```python
# 새 유틸 함수 (engine.py 또는 별도 win_utils.py)
import win32gui, ctypes

def get_game_window_rect(title: str) -> dict | None:
    """창 클라이언트 영역을 mss grab용 dict로 반환. 미발견 시 None."""
    hwnd = win32gui.FindWindow(None, title)
    if not hwnd or not win32gui.IsWindowVisible(hwnd):
        # 대소문자 무관 폴백
        hwnd = _find_window_icase(title)
    if not hwnd:
        return None
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    cx, cy = win32gui.ClientToScreen(hwnd, (0, 0))
    # DPI 보정: 물리 픽셀로 변환
    scale = _get_dpi_scale(hwnd)
    return {
        "top": int(cy * scale), "left": int(cx * scale),
        "width": int((right - left) * scale), "height": int((bottom - top) * scale)
    }
```

**`engine.py` 변경 요점:**
```python
# 기존
monitor = sct.monitors[self.cfg.monitor]

# 변경 후
if self.cfg.window_title:
    region = get_game_window_rect(self.cfg.window_title)
    if region is None:
        return None  # 창 없으면 이번 폴링 스킵
    monitor = region
else:
    monitor = sct.monitors[self.cfg.monitor]
```

## Ontology (Key Entities)
| 엔티티 | 타입 | 필드 | 관계 |
|--------|------|------|------|
| OcrConfig | core domain | monitor, window_title, rois | OcrEngine이 소유 |
| OcrEngine | core domain | cfg, screenshot, roi_match | OcrConfig 참조 |
| GameWindowRect | supporting | top, left, width, height | Win32 API로 취득, mss에 전달 |
| OcrPoller | core domain | state, engine | OcrEngine 실행 |

## Ontology Convergence
| 라운드 | 엔티티 수 | 신규 | 변경 | 안정 | 안정률 |
|--------|-----------|------|------|------|--------|
| 1 | 4 | 4 | - | - | N/A |
| 2 | 4 | 0 | 0 | 4 | 100% |

## Interview Transcript
<details>
<summary>전체 Q&A (Round 0~2)</summary>

### Round 0 (Topology)
**Q:** 3개 컴포넌트(게임 창모드 OCR / 해상도 적응형 ROI / 앱 창 상태 유지) 토폴로지 확인
**A:** 지금 QHD까지는 되니까 우선 1번만 해보자

### Round 1
**Q:** 게임 창 위치를 어떻게 파악해야 하나요? (자동 감지 vs 수동 설정)
**A:** 자동 감지, 창 제목 "masterduel"로 표시됨
**Ambiguity:** 42.5% (Goal: 0.70, Constraints: 0.60, Criteria: 0.30, Context: 0.70)

### Round 2
**Q:** OCR 동작이 전체화면과 완전히 동일해야 하나요?
**A:** 내가 이쪽으론 무지해서 알아서 해줘
**Ambiguity:** 22% (Goal: 0.85, Constraints: 0.75, Criteria: 0.70, Context: 0.80)

</details>
