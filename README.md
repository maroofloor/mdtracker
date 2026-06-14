# MDTracker — Yu-Gi-Oh! Master Duel 전적 트래커

Steam의 Yu-Gi-Oh! Master Duel 플레이 화면을 자동으로 인식해 코인토스 승패, 선공/후공, 듀얼 결과를 기록하고 통계로 정리해주는 Python GUI 앱입니다.

[![Download](https://img.shields.io/github/v/release/maroofloor/mdtracker?label=Download&logo=github)](https://github.com/maroofloor/mdtracker/releases/latest)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 다운로드 (일반 사용자)

**Python·Tesseract 설치 없이** 바로 사용할 수 있습니다.

1. [최신 릴리스 페이지](https://github.com/maroofloor/mdtracker/releases/latest)에서 **`MDTracker_Setup_vX.Y.Z.exe`** 를 다운로드
2. 실행 → 안내에 따라 설치 (관리자 권한 불필요)
3. 시작 메뉴 또는 바탕화면의 **MDTracker** 아이콘으로 실행

> Windows SmartScreen 경고가 뜨면 **추가 정보 → 실행**을 눌러 진행하세요. (아직 코드 서명 인증서가 적용되지 않아 표시되는 경고입니다.)

### 업데이트

앱 실행 시 새 버전이 있으면 자동으로 알림이 뜹니다. **지금 업데이트**를 누르면 최신 설치 파일을 내려받아 설치합니다. 수동으로는 위 릴리스 페이지에서 최신 버전을 받아 다시 설치하면 됩니다.

> 소스에서 직접 실행하려는 개발자는 아래 [개발자용 설치](#개발자용-설치-소스에서-실행)를 참고하세요.

---

## 주요 기능

- **자동 OCR 기록** — 게임 화면을 실시간 캡처해 코인토스·선후공·승패 결과를 자동 감지
- **수동 기록** — OCR 없이 직접 결과를 입력하거나 자동 인식된 내용을 교정
- **대시보드 통계** — 전체 승률 / 덱별 매치업 / 메타 분포 / 기간별 추세 4개 탭
- **덱 관리** — 내 덱 목록 생성·수정·삭제, 퍼지 검색
- **CSV / Excel 내보내기** — 전적 데이터를 .csv 또는 .xlsx로 저장
- **다크 테마 GUI** — PySide6 기반 커스텀 프레임리스 창

---

## 시스템 요구사항

| 항목 | 최소 사양 |
|------|-----------|
| OS | Windows 10 / 11 (64-bit) |
| 해상도 | 1920×1080 권장 (다른 해상도는 `ocr_config.json` 조정 필요) |

> 일반 사용자는 Python·Tesseract를 따로 설치할 필요가 없습니다. 설치 파일에 모두 포함되어 있습니다.
> 아래 Python 3.10+ / Tesseract 5.x 요구사항은 **소스에서 직접 빌드·실행하는 개발자에게만** 해당합니다.
> macOS / Linux는 현재 미지원입니다.

---

## 개발자용 설치 (소스에서 실행)

> 일반 사용자는 이 섹션을 건너뛰고 위 [다운로드](#다운로드-일반-사용자)를 이용하세요.

### 1. Python 설치

[Python 3.12 다운로드](https://www.python.org/downloads/release/python-3120/)

설치 시 **"Add Python to PATH"** 체크 필수.

### 2. Tesseract OCR 설치

[UB-Mannheim Tesseract 다운로드](https://github.com/UB-Mannheim/tesseract/wiki)

설치 시 **Additional language data → Korean** 반드시 체크.

기본 설치 경로: `C:\Program Files\Tesseract-OCR\tesseract.exe`

### 3. 리포지토리 클론

```bash
git clone https://github.com/maroofloor/mdtracker.git
cd mdtracker
```

### 4. OCR 설정 파일 생성

```bash
copy ocr_config.example.json ocr_config.json
```

`ocr_config.json`을 열어 필요 시 수정합니다:

```json
{
  "monitor": 1,
  "window_title": "masterduel",
  "tesseract_cmd": "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
  "feedback_form_url": ""
}
```

| 항목 | 설명 |
|------|------|
| `monitor` | 게임이 실행 중인 모니터 번호 (1=주 모니터) |
| `window_title` | 게임 창 제목 (기본값 그대로 사용) |
| `tesseract_cmd` | Tesseract 설치 경로 (기본 경로와 다를 경우 수정) |
| `feedback_form_url` | 피드백 폼 URL (선택 사항, 비워두면 비활성) |

---

## 실행

### 방법 1 — 배치 파일 (권장)

```
run_main.bat
```

최초 실행 시 자동으로 가상 환경(`.venv`)을 생성하고 패키지를 설치합니다. 이후 실행부터는 즉시 앱이 시작됩니다.

### 방법 2 — 직접 실행

```bash
# 가상 환경 생성 (최초 1회)
python -m venv .venv
.venv\Scripts\activate

# 패키지 설치 (최초 1회)
pip install -r requirements.txt

# 앱 실행
python main.py
```

### 구성 검증 (헤드리스)

디스플레이 없는 환경이나 오류 발생 시 구성만 빠르게 검증:

```bash
set QT_QPA_PLATFORM=offscreen
.venv\Scripts\python.exe main.py --check
```

"메인 윈도우 구성 성공"이 출력되면 정상.

---

## 사용법

### 기본 흐름

```
앱 실행 → 덱 관리에서 내 덱 등록 → 기록 탭에서 내 덱 선택 → OCR 켜기 → 게임 플레이
```

### 화면 구성

#### 기록 탭

- **내 덱 선택** — 상단 드롭다운에서 현재 사용 중인 덱 선택
- **OCR 토글(● OCR)** — 버튼 클릭 시 자동 인식 시작. 듀얼 종료 후 결과 팝업이 뜨면 확인 또는 수정 후 저장
- **수동 추가([+])** — OCR 없이 직접 결과 입력. 코인토스, 선후공, 상대 덱, 승패, 메모 입력 가능
- **테이블 편집** — 상대 덱 셀을 더블클릭해 직접 수정
- **CSV/Excel 내보내기** — 우측 하단 버튼으로 현재 전적 전체 저장

#### 대시보드 탭

필터바(기간·내 덱·상대 덱)를 설정하면 아래 4개 서브탭이 동시에 갱신됩니다:

- **요약(KPI)** — 총 게임 수, 승률, 코인토스 승률, 선공 승률, 후공 승률
- **매치업** — 상대 덱별 승/패 통계 테이블
- **메타** — 상위 덱 분포 차트
- **추세** — 날짜별 승률 추이 그래프

#### 덱 관리 탭

- 덱 추가/수정/삭제
- 퍼지 검색으로 OCR이 잘못 인식한 덱 이름 자동 매칭

#### 설정 탭

- 창 크기 프리셋 (소/중/대)
- UI 스케일 조정
- 피드백 폼 링크

---

## OCR 자동 인식 상세

### 인식 흐름

```
[IDLE] 코인토스 화면 감지
  → [COIN] 선/후공 결정 화면 감지
  → [PLAYING] 승/패 배너 감지 → 결과 팝업
```

### 인식이 잘 안 될 때

**해상도 문제**
- 기본 ROI는 1920×1080 기준. 다른 해상도라면 `ocr_config.json`의 `coin_roi`, `result_roi` 등 비율값 조정 필요

**Tesseract 경로 오류**
- `ocr_config.json`의 `tesseract_cmd` 경로가 실제 설치 경로와 일치하는지 확인

**Korean 학습 데이터 누락**
- Tesseract 재설치 후 설치 옵션에서 Korean 데이터 추가

**창 모드 vs 전체화면**
- 창 모드 플레이 시 `window_title: "masterduel"` 설정으로 자동 감지
- 전체화면이라면 `monitor` 번호가 올바른지 확인

---

## 프로젝트 구조

```
mdtracker/
├── main.py                  # 앱 진입점
├── run_main.bat             # Windows 원클릭 실행 스크립트
├── requirements.txt         # Python 패키지 목록
├── ocr_config.json          # 환경별 OCR 설정 (gitignore 제외, 직접 생성)
├── ocr_config.example.json  # 설정 파일 템플릿
├── data/                    # SQLite DB 저장 위치 (자동 생성)
├── assets/                  # 아이콘, 폰트, 템플릿 이미지
└── mdtracker/
    ├── models.py            # 공유 도메인 모델
    ├── stats.py             # 순수 통계 함수
    ├── db.py                # SQLite 연결 + 저장소
    ├── ocr/                 # OCR 엔진 + 상태 머신 폴러
    └── ui/                  # PySide6 뷰 모음
```

---

## 테스트

```bash
# OCR 단위 테스트 (Tesseract·화면 없이 실행 가능)
.venv\Scripts\python.exe tests/test_ocr.py

# 통계 테스트
.venv\Scripts\python.exe tests/test_filter_stats.py
```

---

## 빌드 & 배포 (관리자용)

릴리스는 Git 태그 푸시로 자동화되어 있습니다. `mdtracker/__init__.py`의 `__version__`을 기준으로 GitHub Actions(`.github/workflows/release.yml`)가 PyInstaller 번들 → Tesseract 동봉 → Inno Setup 인스톨러 → GitHub Release 게시까지 수행합니다.

```bash
# 예: 0.2.1 릴리스
git tag v0.2.1
git push origin v0.2.1
```

태그를 푸시하면 Actions가 자동으로 `MDTracker_Setup_v0.2.1.exe`를 빌드해 릴리스에 첨부합니다. 버전 규칙(SemVer)·브랜치 전략은 `docs/github_versioning_plan.html`을, 로컬 빌드 절차는 `docs/build_guide.md`를 참고하세요.

---

## 라이선스

MIT License
