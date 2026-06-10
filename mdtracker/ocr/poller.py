"""실시간 폴링 워커 — 상태 머신 기반으로 한 듀얼을 조립한다.

상태 머신:
  IDLE    → coin_toss('win'|'loss') 감지 시 → COIN
  COIN    → coin_result('first'|'second') 감지 시 → PLAYING
  PLAYING → result('win'|'loss') 감지 시 → 기록 발행 + IDLE
  Any     → "게임 서버로부터 응답이 없습니다" 감지 시 → IDLE (발행 없이 초기화)

상태별로 관련 recognition 함수만 호출하므로 오탐이 대폭 감소한다.

정체 복구 (설계: docs/ocr_recovery_design.md — 게임 길이에 의존하는
PLAYING 타임아웃 대신 "현재 상태와 양립 불가능한 이벤트"를 복구 신호로 쓴다):
  R1  PLAYING 중 새 토스 감지 = 이전 듀얼 결과를 놓친 것이 확정
      → 이전 듀얼을 결과 미상(result='unknown')으로 발행 후 새 토스로 COIN 재진입.
      COIN에는 적용하지 않는다(토스 문구 8~12초 잔상을 새 토스로 재감지하는 오발행 방지).
      토스 OCR은 스로틀(playing_toss_check_cycles)·result_cooldown 게이트를 통과해야 돈다.
  R2  창 소멸 — capture_screen()이 'not_found'를 연속 window_gone_cycles회 반환하고
      IDLE이 아니면 R1과 동일하게 미상 발행 후 IDLE. 최소화('minimized')는 소멸이
      아니므로 카운터를 올리지 않고 상태를 유지한다(복원 시 캡처 재개, 놓친 결과는 R1이 회수).
  R3  COIN 한정 타임아웃(coin_timeout) — 초과 시 토스 정보만 버리고 발행 없이 IDLE.
      서버오류 팝업 OCR마저 실패하는 CONNECTING 정체의 안전망.

성능 (P1): 루프는 상태별 인식(특히 저비용 결과 템플릿 매칭)을 먼저 수행하고,
서버 오류 한글 OCR은 server_error_check_cycles주기마다 1회로 스로틀한다.
팝업은 사용자가 닫을 때까지 지속되므로 감지율 손실이 없다.

UI 스레드를 막지 않도록 QThread에서 돌고, 결과는 시그널로 넘긴다.
"""

from __future__ import annotations

import time
from enum import Enum, auto

from PySide6.QtCore import QThread, Signal

from .engine import (
    OcrEngine, OcrResult,
    recognize_coin, recognize_coin_toss, recognize_result, recognize_server_error,
)


class DuelState(Enum):
    IDLE = auto()     # 대기: coin_toss 승/패만 감지
    COIN = auto()     # coin_toss 확인됨: coin_result(선공/후공) 감지
    PLAYING = auto()  # coin_result 확인됨: 승/패 결과 감지 (+ R1 토스 복구)


class OcrPoller(QThread):
    match_detected = Signal(object)   # 병합된 OcrResult (result + coin 정보)
    state_changed  = Signal(str)      # DuelState.name ("IDLE" | "COIN" | "PLAYING")
    error = Signal(str)

    def __init__(self, engine: OcrEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._running = False
        # ── 상태 머신 ──
        self._state = DuelState.IDLE
        self._pending_toss: str | None = None       # IDLE→COIN 에서 저장
        self._pending_toss_conf: float = 0.0
        self._pending_coin: str | None = None       # COIN→PLAYING 에서 저장
        self._pending_coin_conf: float = 0.0
        self._state_entered_at: float = 0.0         # 현재 상태 진입 시각
        # ── 결과 쿨다운 (중복 발행 방지 — 토스 복구 감지에도 적용) ──
        self._cooldown_until: float = 0.0
        # ── 폴링 주기 카운터 (스로틀 기준) ──
        self._cycle: int = 0
        # ── R2: 창 소멸 연속 카운터 ──
        self._window_gone_count: int = 0

    # ---------------------------------------------------------------- 메인 루프
    def run(self) -> None:
        self._running = True
        interval_ms = max(1, int(self.engine.cfg.poll_interval * 1000))

        while self._running:
            try:
                img = self.engine.capture_screen()
            except Exception as exc:                   # noqa: BLE001
                self.error.emit(str(exc))
                self.msleep(interval_ms)
                continue

            self._process_cycle(img, time.monotonic())
            self.msleep(interval_ms)

    def _process_cycle(self, img, now: float) -> None:
        """폴링 1주기 처리. run()에서 분리해 QThread 없이 단위 테스트 가능."""
        cfg = self.engine.cfg
        self._cycle += 1

        if img is None:                                # 캡처 실패 — R2 판정
            self._handle_no_capture(cfg, now)
            return
        self._window_gone_count = 0

        # ── 상태별 전환 (저비용 인식 우선 — P1) ──
        if self._state is DuelState.IDLE:
            self._handle_idle(img, cfg, now)
        elif self._state is DuelState.COIN:
            self._handle_coin(img, cfg, now)
        elif self._state is DuelState.PLAYING:
            self._handle_playing(img, cfg, now)

        # ── 서버 오류 감지 (스로틀 + 상태 인식 뒤 — P1) ──
        if self._cycle % max(1, cfg.server_error_check_cycles) == 0:
            try:
                if recognize_server_error(img, cfg):
                    self._reset_state()                # 발행 없이 IDLE 복귀
            except Exception:                          # noqa: BLE001 - tesseract 미설치 등
                pass

    # ---------------------------------------------------------------- 상태 핸들러
    def _handle_no_capture(self, cfg, now: float) -> None:
        """캡처 실패 처리 (R2). 'not_found'만 소멸로 카운트, 'minimized'는 상태 유지."""
        status = getattr(self.engine, "last_capture_status", "not_found")
        if status == "minimized":
            return  # 최소화 — 듀얼 진행 중일 수 있음. 카운터 동결, 복원 대기
        if self._state is DuelState.IDLE:
            self._window_gone_count = 0
            return
        self._window_gone_count += 1
        if self._window_gone_count >= max(1, cfg.window_gone_cycles):
            self._publish_unknown(cfg, now)            # R2: 미상 발행 후 초기화
            self._reset_state()

    def _handle_idle(self, img, cfg, now: float) -> None:
        """IDLE: coin_toss(토스 승/패)만 감지."""
        try:
            toss, conf, _ = recognize_coin_toss(img, cfg)
        except Exception:                              # noqa: BLE001
            return
        if toss and conf > self._pending_toss_conf:
            self._pending_toss = toss
            self._pending_toss_conf = conf
            self._transition(DuelState.COIN, now)

    def _handle_coin(self, img, cfg, now: float) -> None:
        """COIN: coin_result(선공/후공)만 감지. 정체 시 R3 타임아웃."""
        try:
            coin, conf, _ = recognize_coin(img, cfg)
        except Exception:                              # noqa: BLE001
            coin, conf = None, 0.0                     # OCR 실패해도 타임아웃 검사는 계속
        if coin and conf > self._pending_coin_conf:
            self._pending_coin = coin
            self._pending_coin_conf = conf
            self._transition(DuelState.PLAYING, now)
            return
        # R3: COIN 구간은 실측 15~25초 상한 — 초과 시 토스만 버리고 IDLE (발행 없음)
        if (cfg.coin_timeout > 0
                and now - self._state_entered_at > cfg.coin_timeout):
            self._reset_state()

    def _handle_playing(self, img, cfg, now: float) -> None:
        """PLAYING: 승/패 결과 감지(매주기, 저비용) + R1 토스 복구(스로틀)."""
        try:
            result, conf, _ = recognize_result(img, cfg, self.engine.templates)
        except Exception:                              # noqa: BLE001
            result, conf = None, 0.0

        if result and now >= self._cooldown_until:
            self.match_detected.emit(OcrResult(
                result=result,
                coin_result=self._pending_coin,
                coin_toss=self._pending_toss,
                result_conf=conf,
                coin_conf=self._pending_coin_conf,
                toss_conf=self._pending_toss_conf,
                needs_review=(conf < cfg.review_threshold
                              or self._pending_coin is None),
                coin_raw="",
            ))
            self._cooldown_until = now + cfg.result_cooldown
            self._reset_state()
            return

        # ── R1: 새 토스 감지 = 이전 듀얼 결과 누락 확정 (PLAYING 한정) ──
        # 스로틀: 토스 OCR을 매주기 돌리면 듀얼 중 배너가 게이트를 통과할 때마다
        # tesseract가 돌아 P1의 실효 주기 증가 문제를 재도입한다.
        if self._cycle % max(1, cfg.playing_toss_check_cycles) != 0:
            return
        if now < self._cooldown_until:                 # 결과 직후 잔상 오인 방지
            return
        try:
            toss, tconf, _ = recognize_coin_toss(img, cfg)
        except Exception:                              # noqa: BLE001
            return
        if toss:
            self._publish_unknown(cfg, now)            # 이전 듀얼 = 결과 미상
            self._reset_state()
            self._pending_toss = toss                  # 새 토스로 COIN 재진입
            self._pending_toss_conf = tconf
            self._transition(DuelState.COIN, now)

    # ---------------------------------------------------------------- 헬퍼
    def _publish_unknown(self, cfg, now: float) -> None:
        """놓친 듀얼을 결과 미상으로 발행 (R1/R2 공용).

        coin_result가 None일 수 있다(COIN 정체 중 창 소멸) — UI가 'unknown'으로
        저장하고 사용자 교정을 받는다. 'first' 등으로 추정하지 않는다.
        """
        self.match_detected.emit(OcrResult(
            result="unknown",
            coin_result=self._pending_coin,
            coin_toss=self._pending_toss,
            result_conf=0.0,
            coin_conf=self._pending_coin_conf,
            toss_conf=self._pending_toss_conf,
            needs_review=True,
            coin_raw="",
        ))
        self._cooldown_until = now + cfg.result_cooldown

    def _transition(self, new_state: DuelState, now: float) -> None:
        self._state = new_state
        self._state_entered_at = now
        self.state_changed.emit(new_state.name)

    def _reset_state(self) -> None:
        was_idle = self._state is DuelState.IDLE
        self._state = DuelState.IDLE
        self._state_entered_at = 0.0
        self._pending_toss = None
        self._pending_toss_conf = 0.0
        self._pending_coin = None
        self._pending_coin_conf = 0.0
        self._window_gone_count = 0
        if not was_idle:                               # 복구 경로 가시성 (OCR 패널)
            self.state_changed.emit(DuelState.IDLE.name)

    def stop(self) -> None:
        self._running = False
        self.wait(3000)
