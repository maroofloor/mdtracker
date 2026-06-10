"""OCR 엔진 — 한 장의 화면 이미지에서 승/패·선후공을 추출한다.

설계 근거: _workspace/02_ocr_research.md (실제 영상 검증).
- 선/후공: "당신이 선공/후공입니다" 한글 → 전처리 후 tesseract `kor`.
- 승/패: VICTORY/DEFEAT 영문 스타일 배너 → OCR 불가, 고정 그래픽 템플릿 매칭.
- 인식 실패는 예외가 아니라 낮은 confidence/None 경로. 잘못된 자동기록보다 미인식이 안전.

capture_and_extract()는 mss로 실시간 캡처하지만, extract_from_image()는
PIL 이미지를 받아 화면/의존성 없이 단위 검증 가능하게 분리한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageOps

from .config import OcrConfig, Roi

# 템플릿 비교용 정규화 크기 (배너 ROI 비율 76:16 ≈ 가로로 긴 띠)
_TEMPLATE_SIZE = (480, 96)


@dataclass
class OcrResult:
    """OCR 추출 결과. UI/DB가 추정 없이 소비하는 계약 (반자동: opponent_deck 없음).

    result/coin_result가 None이면 해당 신호 미감지. UI는 needs_review=True면
    confirmed=False로 폼을 채워 사용자 교정을 받는다.
    폴러의 복구 경로(R1/R2)는 놓친 듀얼을 result='unknown'으로 발행한다 (설계 §6).
    """

    result: Optional[str] = None        # 'win' | 'loss' | 'draw' | 'unknown' | None
    coin_result: Optional[str] = None   # 'first' | 'second' | None
    coin_toss: Optional[str] = None     # 'win' | 'loss' | None (내가 토스를 이겼는지)
    result_conf: float = 0.0            # 0~1
    coin_conf: float = 0.0              # 0~1
    toss_conf: float = 0.0             # 0~1
    needs_review: bool = True
    coin_raw: str = ""                  # OCR 원문 (디버그/교정 표시용)

    @property
    def has_signal(self) -> bool:
        return (self.result is not None or self.coin_result is not None
                or self.coin_toss is not None)


# ---------------------------------------------------------------- 전처리 유틸
def _pixel_box(roi: Roi, w: int, h: int):
    return (int(roi[0] * w), int(roi[1] * h), int(roi[2] * w), int(roi[3] * h))


def _bright_mask(crop: Image.Image, threshold: int) -> np.ndarray:
    """밝은(흰) 글자 픽셀 마스크 (bool 2D). 배너/텍스트가 흰색이라는 점을 이용."""
    g = np.asarray(ImageOps.grayscale(crop))
    return g >= threshold


# ---------------------------------------------------------------- 선/후공
def _apply_tess_cmd(cfg: OcrConfig):
    import pytesseract  # 지연 임포트: tesseract 미설치 환경에서 모듈 로드는 가능하게
    if cfg.tesseract_cmd:  # Windows 등 PATH 밖 tesseract.exe 지정
        pytesseract.pytesseract.tesseract_cmd = cfg.tesseract_cmd
    return pytesseract


def _has_bright_text(gray: Image.Image, threshold: int, min_ratio: float) -> bool:
    """ROI에 밝은(흰) 글자 픽셀이 충분한지 — 빈 화면이면 OCR을 건너뛰기 위한 저비용 게이트."""
    return float((np.asarray(gray) >= threshold).mean()) >= min_ratio


def _ocr_line(gray: Image.Image, threshold: int, cfg: OcrConfig, pytesseract):
    """밝은 글자 이진화 → 업스케일 → OCR. (raw_text, conf 0~1) 반환."""
    bw = gray.point(lambda p: 0 if p >= threshold else 255)
    bw = bw.resize((bw.width * cfg.coin_upscale, bw.height * cfg.coin_upscale),
                   Image.LANCZOS)
    data = pytesseract.image_to_data(
        bw, lang=cfg.tess_lang, config=f"--psm {cfg.tess_psm}",
        output_type=pytesseract.Output.DICT,
    )
    words, confs = [], []
    for txt, c in zip(data["text"], data["conf"]):
        if txt.strip():
            words.append(txt.strip())
            try:
                cv = float(c)
            except (TypeError, ValueError):
                cv = -1
            if cv >= 0:
                confs.append(cv)
    raw = " ".join(words)
    conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
    return raw, conf


def classify_coin_text(compact: str) -> Optional[str]:
    """선후공 확정 문구 분류 (공백 제거 텍스트 입력).

    "당신이 선공/후공입니다" → 'first'/'second'. 선공·후공이 둘 다 보이면
    토스 선택 화면이므로 거부(None). 순수 함수 — tesseract 없이 단위 테스트 가능.
    """
    has_first, has_second = "선공" in compact, "후공" in compact
    if "당신이" in compact and (has_first != has_second):
        return "first" if has_first else "second"
    return None


def classify_toss_text(compact: str) -> Optional[str]:
    """토스 선택 화면 분류 (공백 제거 텍스트 입력). P2 강화 키워드.

    실제 토스 화면 문구는 선공·후공이 둘 다 들어 있다:
      "선공/후공을 선택해주세요" (내가 선택)       → 'win'
      "대전 상대가 선공/후공을 선택하고 있습니다"  → 'loss'
    듀얼 중 안내 배너("상대가 효과 대상을 선택하고 있습니다" 류)는
    선공·후공이 없어 거부된다 — coin ROI와 겹치는 배너 오탐 방지(설계 P2).
    """
    if "당신이" in compact:  # "당신이 선공/후공입니다" = coin_result 화면 → toss 아님
        return None
    if "선공" not in compact or "후공" not in compact:
        return None
    if "주세요" in compact:      # "…선택해주세요" = 내가 선택 = 토스 승
        return "win"
    if "상대" in compact:        # "상대가 …선택하고 있습니다" = 토스 패
        return "loss"
    return None


def _recognize_coin_text(img: Image.Image, cfg: OcrConfig, classify):
    """coin_roi를 다중 임계로 OCR하고 classify()가 인정한 최고 신뢰 판독 채택."""
    pytesseract = _apply_tess_cmd(cfg)
    w, h = img.size
    gray = ImageOps.grayscale(img.crop(_pixel_box(cfg.coin_roi, w, h)))
    if not _has_bright_text(gray, cfg.coin_bin_threshold, cfg.coin_min_text_ratio):
        return (None, 0.0, "")  # 빈 화면 — OCR 생략

    best = (None, 0.0, "")
    for thr in cfg.coin_bin_thresholds:
        raw, conf = _ocr_line(gray, thr, cfg, pytesseract)
        compact = raw.replace(" ", "")  # "선 공" 같은 글자 사이 공백 제거
        cand = classify(compact)
        if cand is None:
            if not best[2]:
                best = (best[0], best[1], raw)  # 디버그용 마지막 raw 보존
            continue
        if conf > best[1]:
            best = (cand, conf, raw)
        if conf >= cfg.coin_early_exit_conf:
            break  # 충분히 확신 — 남은 임계 생략
    return best


def recognize_coin(img: Image.Image, cfg: OcrConfig):
    """(coin_result|None, conf 0~1, raw_text) 반환.

    실게임 페이드 대비: 여러 이진화 임계로 OCR하고, 유효 판독 중 최고 신뢰를 채택.
    확정 문구 "당신이 선공/후공입니다"만 인정(선택중/선택해주세요 류는 둘 다 포함→거부).
    """
    return _recognize_coin_text(img, cfg, classify_coin_text)


def recognize_coin_toss(img: Image.Image, cfg: OcrConfig):
    """(coin_toss|None 'win'/'loss', conf 0~1, raw_text) 반환.

    토스 선택 화면으로 내가 토스를 이겼는지 판별 (classify_toss_text 참조).
    확정 문구·기타 화면은 None.
    "선택해주세요" 텍스트는 coin_roi에서만 안정적으로 잡힘 (toss_roi는 폭이 넓어 노이즈 多).
    """
    return _recognize_coin_text(img, cfg, classify_toss_text)


# ---------------------------------------------------------------- 서버 오류 다이얼로그
def recognize_server_error(img: Image.Image, cfg: OcrConfig) -> bool:
    """화면에 "게임 서버로부터 응답이 없습니다" 팝업이 있는지 감지.

    True면 폴러가 상태를 IDLE로 초기화해야 한다.
    """
    pytesseract = _apply_tess_cmd(cfg)
    w, h = img.size
    gray = ImageOps.grayscale(img.crop(_pixel_box(cfg.server_error_roi, w, h)))
    if not _has_bright_text(gray, cfg.coin_bin_threshold, cfg.coin_min_text_ratio):
        return False
    raw, _ = _ocr_line(gray, cfg.coin_bin_threshold, cfg, pytesseract)
    compact = raw.replace(" ", "")
    return "응답이없습니다" in compact or "서버로부터" in compact


# ---------------------------------------------------------------- 승/패 (템플릿)
def _iou(a: np.ndarray, b: np.ndarray) -> float:
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return float(inter) / float(union) if union else 0.0


def _result_mask(img: Image.Image, cfg: OcrConfig) -> np.ndarray:
    w, h = img.size
    crop = img.crop(_pixel_box(cfg.result_roi, w, h))
    bw = crop.resize(_TEMPLATE_SIZE, Image.LANCZOS)
    return _bright_mask(bw, cfg.result_bin_threshold)


class _Templates:
    """victory/defeat 레퍼런스 마스크 로더 (지연 로드)."""

    def __init__(self, template_dir: str):
        self.dir = Path(template_dir)
        self._victory: Optional[np.ndarray] = None
        self._defeat: Optional[np.ndarray] = None

    @staticmethod
    def _load(path: Path) -> Optional[np.ndarray]:
        if not path.exists():
            return None
        m = np.asarray(ImageOps.grayscale(Image.open(path).resize(_TEMPLATE_SIZE)))
        return m >= 127

    @property
    def victory(self):
        if self._victory is None:
            self._victory = self._load(self.dir / "victory.png")
        return self._victory

    @property
    def defeat(self):
        if self._defeat is None:
            self._defeat = self._load(self.dir / "defeat.png")
        return self._defeat


def recognize_result(img: Image.Image, cfg: OcrConfig, templates: _Templates):
    """(result|None, conf 0~1, {'win':iou,'loss':iou}) 반환."""
    tv, td = templates.victory, templates.defeat
    if tv is None or td is None:
        return None, 0.0, {}
    mask = _result_mask(img, cfg)
    sv, sd = _iou(mask, tv), _iou(mask, td)
    scores = {"win": sv, "loss": sd}
    best = max(sv, sd)
    if best < cfg.result_match_threshold or abs(sv - sd) < cfg.result_match_margin:
        return None, best, scores
    return ("win" if sv > sd else "loss"), best, scores


# ---------------------------------------------------------------- 창 감지/캡처 (창모드 지원)
def _find_game_window(title: str):
    """창 제목 부분일치로 게임 창 hwnd 탐색. 미발견/비Windows 환경이면 None."""
    try:
        import win32gui
    except ImportError:
        return None

    target = title.lower()
    found = [None]

    def _enum(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and target in win32gui.GetWindowText(hwnd).lower():
            found[0] = hwnd
        return True

    win32gui.EnumWindows(_enum, None)
    return found[0]


def _is_window_minimized(hwnd) -> bool:
    """최소화 여부 — R2가 '창 소멸'로 오인하지 않도록 구분한다."""
    try:
        import win32gui
        return bool(win32gui.IsIconic(hwnd))
    except Exception:
        return False


def _client_screen_region(hwnd) -> Optional[dict]:
    """hwnd의 클라이언트 영역을 mss grab 용 dict로 반환. 0 크기/실패면 None."""
    # PySide6이 Per-Monitor DPI Aware v2를 설정하므로 win32gui는 물리 픽셀 반환 — 스케일 변환 불필요
    try:
        import win32gui
        cx, cy = win32gui.ClientToScreen(hwnd, (0, 0))
        _, _, cw, ch = win32gui.GetClientRect(hwnd)
    except Exception:
        return None

    if cw <= 0 or ch <= 0:
        return None

    return {"top": cy, "left": cx, "width": cw, "height": ch}


# PrintWindow 플래그 — 클라이언트 영역만(타이틀바 제외, 비율 ROI 호환) + DWM 렌더 표면
_PW_CLIENTONLY = 0x1
_PW_RENDERFULLCONTENT = 0x2


def _capture_window_printwindow(hwnd) -> Optional[Image.Image]:
    """DWM이 보관한 창 자체의 렌더링 표면을 복사 (설계 §4).

    화면 영역 grab과 달리 다른 창이 게임을 가려도 게임 화면을 정상 캡처한다.
    실패(0 반환·예외) 시 None — 호출 측이 화면 영역 grab으로 폴백한다.
    win32ui는 이미 의존 중인 pywin32에 포함 — 새 의존성 없음.
    """
    import ctypes
    try:
        import win32gui
        import win32ui
    except ImportError:
        return None

    try:
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
    except Exception:
        return None
    w, h = right - left, bottom - top
    if w <= 0 or h <= 0:
        return None

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = save_dc = bmp = None
    try:
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(bmp)
        ok = ctypes.windll.user32.PrintWindow(
            hwnd, save_dc.GetSafeHdc(), _PW_CLIENTONLY | _PW_RENDERFULLCONTENT)
        if not ok:
            return None
        info = bmp.GetInfo()
        data = bmp.GetBitmapBits(True)
        return Image.frombuffer(
            "RGB", (info["bmWidth"], info["bmHeight"]), data, "raw", "BGRX", 0, 1)
    except Exception:
        return None
    finally:
        try:
            if bmp is not None:
                win32gui.DeleteObject(bmp.GetHandle())
            if save_dc is not None:
                save_dc.DeleteDC()
            if mfc_dc is not None:
                mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)
        except Exception:
            pass


def _is_black_frame(img: Image.Image, threshold: int = 16) -> bool:
    """사실상 전흑 프레임 여부 — 전체화면 독점 모드에서 PrintWindow가
    검은 프레임을 반환하는 사례 감지 (→ 화면 영역 grab 폴백)."""
    return int(np.asarray(ImageOps.grayscale(img)).max(initial=0)) < threshold


# ---------------------------------------------------------------- 엔진 파사드
class OcrEngine:
    def __init__(self, cfg: Optional[OcrConfig] = None):
        self.cfg = cfg or OcrConfig()
        self.templates = _Templates(self.cfg.template_dir)
        # 직전 capture_screen()의 실패 사유 (R2 캡처 계약):
        #   'ok'        — 캡처 성공
        #   'not_found' — 게임 창 없음 (종료/크래시) → R2 소멸 카운트 대상
        #   'minimized' — 창은 있으나 캡처 불가 (최소화 등) → 상태 유지 대상
        self.last_capture_status: str = "ok"

    def extract_from_image(self, img: Image.Image) -> OcrResult:
        """화면 한 장 → OcrResult. (화면/실시간 의존 없음, 테스트 가능)"""
        coin, coin_conf, coin_raw = recognize_coin(img, self.cfg)
        toss, toss_conf, _ = recognize_coin_toss(img, self.cfg)
        result, res_conf, _ = recognize_result(img, self.cfg, self.templates)

        # 교정 필요 판단: 결과·선후공의 신뢰도만 사용(coin_toss는 보조)
        confs = [c for sig, c in ((coin, coin_conf), (result, res_conf)) if sig]
        needs_review = (not confs) or (min(confs) < self.cfg.review_threshold)
        return OcrResult(
            result=result, coin_result=coin, coin_toss=toss,
            result_conf=res_conf, coin_conf=coin_conf, toss_conf=toss_conf,
            needs_review=needs_review, coin_raw=coin_raw,
        )

    def capture_screen(self) -> Optional[Image.Image]:
        """현재 게임 화면 캡처 → PIL 이미지. 실패 시 None. (실시간 경로)

        창 모드(window_title 설정 시)에서는 PrintWindow(가림 무관)를 우선 시도하고,
        실패/검은 프레임이면 기존 화면 영역 grab으로 자동 폴백한다 (설계 §4).
        None 반환 시 사유는 last_capture_status('not_found'|'minimized')로 구분한다.
        """
        if not self.cfg.window_title:
            img = self._grab_region(None)              # 모니터 전체 모드
            self.last_capture_status = "ok"
            return img

        hwnd = _find_game_window(self.cfg.window_title)
        if hwnd is None:
            self.last_capture_status = "not_found"
            return None
        if _is_window_minimized(hwnd):
            # 최소화 — Unity는 렌더링을 멈출 수 있어 어떤 캡처 기술로도 보장 불가.
            # R2가 소멸로 오인하지 않도록 별도 신호. 놓친 결과는 R1이 회수한다.
            self.last_capture_status = "minimized"
            return None

        img = _capture_window_printwindow(hwnd)
        if img is not None and not _is_black_frame(img):
            self.last_capture_status = "ok"
            return img

        # 폴백: 화면 영역 grab (전체화면 독점 모드 등 PrintWindow 검은 프레임 사례)
        region = _client_screen_region(hwnd)
        if region is None:
            # 창은 있는데 클라이언트 영역 0 크기 — 최소화/전환 중으로 취급 (R2 오인 방지)
            self.last_capture_status = "minimized"
            return None
        img = self._grab_region(region)
        self.last_capture_status = "ok"
        return img

    def _grab_region(self, region: Optional[dict]) -> Optional[Image.Image]:
        """mss 화면 영역 grab. region=None이면 cfg.monitor 전체."""
        import mss  # 지연 임포트
        with mss.MSS() as sct:
            mon = region if region is not None else sct.monitors[self.cfg.monitor]
            shot = sct.grab(mon)
            return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    def capture_and_extract(self) -> Optional[OcrResult]:
        img = self.capture_screen()
        if img is None:
            return None
        return self.extract_from_image(img)


# ---------------------------------------------------------------- DB 매핑
def to_match_fields(r: OcrResult) -> dict:
    """OcrResult → Match가 받는 OCR 유래 필드만 (architect 계약 기준).

    played_at·my_deck·opponent_deck·season은 UI가 채운다(반자동). 여기선
    source='ocr', result/coin_result, 신뢰도, confirmed만 제공.
    ocr_confidence는 존재하는 신호들의 최솟값(보수적).
    """
    confs = [c for sig, c in ((r.result, r.result_conf),
                              (r.coin_result, r.coin_conf),
                              (r.coin_toss, r.toss_conf)) if sig]
    return {
        "result": r.result,
        "coin_result": r.coin_result,
        "coin_toss": r.coin_toss,
        "source": "ocr",
        "ocr_confidence": (min(confs) if confs else 0.0),
        "confirmed": not r.needs_review,
    }
