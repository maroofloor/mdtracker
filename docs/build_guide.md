# MDTracker 빌드 & 배포 가이드

## 전체 구조

```
배포 방식: PyInstaller(폴더 번들) + Inno Setup(인스톨러) + GitHub Releases(배포+자동업데이트)

사용자 흐름:
  GitHub Releases → MDTracker_Setup_vX.Y.Z.exe 다운로드
  → 설치 (Python/Tesseract 불필요)
  → 앱 실행 시 자동으로 새 버전 확인
```

---

## 1. 로컬 빌드 (개발자)

### 준비

```powershell
# 의존성 설치
pip install -r requirements.txt
pip install pyinstaller

# Tesseract 번들 준비
# UB Mannheim 빌드 다운로드: https://github.com/UB-Mannheim/tesseract/wiki
# 설치 후 C:\Program Files\Tesseract-OCR\ → 프로젝트 루트의 tesseract\ 에 복사
robocopy "C:\Program Files\Tesseract-OCR" "tesseract" /E
```

### 빌드

```powershell
# PyInstaller 번들 생성 (dist\MDTracker\)
pyinstaller MDTracker.spec --noconfirm

# Inno Setup 인스톨러 생성 (installer\Output\)
# Inno Setup 6 필요: https://jrsoftware.org/isinfo.php
ISCC installer\MDTracker_Setup.iss
```

결과물: `installer\Output\MDTracker_Setup_v0.1.0.exe`

---

## 2. GitHub Actions 자동 빌드

### 설정 (최초 1회)

1. GitHub 저장소 생성 후 push
2. `mdtracker/updater.py` 상단의 `GITHUB_OWNER` / `GITHUB_REPO` 를 본인 값으로 수정
3. Actions 탭 → 워크플로 활성화 확인

### 릴리스 배포

```bash
# 버전 태그를 push하면 자동 빌드 + GitHub Release 생성
git tag v0.2.0
git push origin v0.2.0
```

Actions 탭에서 진행 상황 확인 → 완료 후 Releases 탭에 인스톨러 자동 업로드.

---

## 3. 버전 관리 규칙

`mdtracker/__init__.py`의 `__version__` 이 단일 진실의 원천(source of truth).
CI가 태그 기준으로 자동 동기화한다.

| 변경 종류 | 버전 올리는 곳 | 예시 |
|-----------|---------------|------|
| 버그 수정 | PATCH | `0.1.0` → `0.1.1` |
| 기능 추가 | MINOR | `0.1.0` → `0.2.0` |
| 호환성 파괴 변경 | MAJOR | `0.1.0` → `1.0.0` |

---

## 4. Tesseract 번들 구조

```
dist\MDTracker\
├── MDTracker.exe
├── tesseract\                 ← Tesseract 바이너리
│   ├── tesseract.exe
│   ├── tessdata\
│   │   ├── kor.traineddata    ← 한국어 OCR 필수
│   │   └── eng.traineddata
│   └── ...
├── assets\
├── mdtracker\
└── ...
```

`ocr_config.json`의 `tesseract_cmd` 값:
- **번들 실행파일**: `"tesseract\\tesseract.exe"` (상대 경로, 앱 루트 기준)
- **개발 환경**: `""` (PATH에서 탐색) 또는 절대 경로

앱이 시작될 때 `ocr_config.json`을 `%APPDATA%\MDTracker\` 에서 읽는다.
인스톨러가 처음 설치 시 예시 파일을 그 경로에 복사해 준다.

---

## 5. 자동 업데이트 동작

1. 앱 시작 시 `mdtracker/updater.py` 가 백그라운드 스레드에서 GitHub API 호출
2. 현재 버전 < 최신 릴리스 버전이면 팝업 표시
3. 사용자가 "지금 업데이트" 선택 → 인스톨러 다운로드 → 실행 후 앱 자동 종료
4. 설치 완료 후 새 버전으로 재시작

개발 환경(`sys.frozen == False`)에서는 업데이트 확인을 건너뛴다.

---

## 6. 주의 사항

- **아이콘**: `assets/icon.png` → `.ico` 변환 권장 (`MDTracker.spec`의 `icon=` 수정)
- **코드 서명**: 인증서 없이 배포하면 Windows SmartScreen 경고가 뜰 수 있음. 사용자에게 "추가 정보 → 실행" 안내 또는 EV 코드 서명 인증서 구매 고려
- **`tesseract\` 폴더는 `.gitignore`에 추가**: 바이너리를 저장소에 커밋하지 않음
- **DB 파일**: `%APPDATA%\MDTracker\` 에 저장하도록 `app_paths.py` 확인 권장. 현재는 앱 폴더(`data\`) 저장이므로 업데이트 시 덮어쓰이지 않도록 인스톨러가 `data\` 디렉터리를 건드리지 않음
