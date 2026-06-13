"""OcrPoller 상태머신·복구 메커니즘 단위 테스트 — 화면/tesseract 불필요.

가짜 인식 결과를 모듈 함수에 주입해 _process_cycle()을 직접 구동한다.
검증 항목 (docs/ocr_recovery_design.md):
  - 정상 흐름 IDLE→COIN→PLAYING→발행
  - P1: 서버 오류 OCR 스로틀 (N주기 1회)
  - R1: PLAYING 한정 토스 복구 (미상 발행 + COIN 재진입), 스로틀·쿨다운 게이트,
        COIN에서는 미적용 (토스 잔상 가드)
  - R2: 창 소멸 카운터 ('not_found'만), 최소화('minimized')는 상태 유지
  - R3: COIN 타임아웃 — 발행 없이 IDLE

실행: QT_QPA_PLATFORM=offscreen .venv/bin/python tests/test_poller_recovery.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QCoreApplication  # noqa: E402

import mdtracker.ocr.poller as poller_mod  # noqa: E402
from mdtracker.ocr.config import OcrConfig  # noqa: E402
from mdtracker.ocr.poller import DuelState, OcrPoller  # noqa: E402

_app = QCoreApplication.instance() or QCoreApplication([])


class FakeEngine:
    def __init__(self, cfg):
        self.cfg = cfg
        self.templates = None
        self.last_capture_status = "ok"


def _cfg(**kw):
    base = dict(
        result_cooldown=8.0,
        coin_timeout=120.0,
        playing_toss_check_cycles=1,    # 테스트 기본: 스로틀 없음
        server_error_check_cycles=10_000,  # 테스트 기본: 서버오류 검사 비활성
        window_gone_cycles=3,
    )
    base.update(kw)
    return OcrConfig(**base)


_NONE3 = (None, 0.0, "")


class PollerTestCase(unittest.TestCase):
    """recognize_* 모듈 함수를 가짜로 치환하고 teardown에서 복원."""

    def setUp(self):
        self._orig = {
            name: getattr(poller_mod, name)
            for name in ("recognize_coin", "recognize_coin_toss",
                         "recognize_result", "recognize_server_error")
        }
        self.fakes = {
            "recognize_coin": lambda img, cfg: _NONE3,
            "recognize_coin_toss": lambda img, cfg: _NONE3,
            "recognize_result": lambda img, cfg, tpl: _NONE3,
            "recognize_server_error": lambda img, cfg: False,
        }
        for name, fn in self.fakes.items():
            setattr(poller_mod, name, fn)

    def tearDown(self):
        for name, fn in self._orig.items():
            setattr(poller_mod, name, fn)

    # ---- 헬퍼 ----
    def make_poller(self, **cfg_kw):
        engine = FakeEngine(_cfg(**cfg_kw))
        p = OcrPoller(engine)
        self.emitted = []
        self.states = []
        p.match_detected.connect(self.emitted.append)
        p.state_changed.connect(self.states.append)
        return p

    def set_fake(self, name, fn):
        setattr(poller_mod, name, fn)

    def to_playing(self, p, now=0.0):
        """IDLE → COIN → PLAYING 진입 (토스 패, 후공)."""
        self.set_fake("recognize_coin_toss", lambda i, c: ("loss", 0.9, "raw"))
        p._process_cycle("img", now)
        self.assertIs(p._state, DuelState.COIN)
        self.set_fake("recognize_coin_toss", lambda i, c: _NONE3)
        self.set_fake("recognize_coin", lambda i, c: ("second", 0.95, "raw"))
        p._process_cycle("img", now + 1)
        self.assertIs(p._state, DuelState.PLAYING)
        self.set_fake("recognize_coin", lambda i, c: _NONE3)


class TestNormalFlow(PollerTestCase):
    def test_full_duel_publishes_result(self):
        p = self.make_poller()
        self.to_playing(p)
        self.set_fake("recognize_result", lambda i, c, t: ("win", 0.97, {}))
        p._process_cycle("img", 10.0)

        self.assertEqual(len(self.emitted), 1)
        r = self.emitted[0]
        self.assertEqual(r.result, "win")
        self.assertEqual(r.coin_result, "second")
        self.assertEqual(r.coin_toss, "loss")
        self.assertFalse(r.needs_review)        # conf 0.97 ≥ 0.80
        self.assertIs(p._state, DuelState.IDLE)
        self.assertEqual(self.states, ["COIN", "PLAYING", "IDLE"])

    def test_result_cooldown_blocks_duplicate(self):
        p = self.make_poller()
        self.to_playing(p)
        self.set_fake("recognize_result", lambda i, c, t: ("win", 0.97, {}))
        p._process_cycle("img", 10.0)           # 발행 + IDLE
        # 쿨다운(8초) 내 재감지 — IDLE이므로 결과 인식 자체가 안 돌지만,
        # 바로 다음 듀얼이 PLAYING까지 갔다고 가정해도 쿨다운이 발행을 막는다
        self.to_playing(p, now=11.0)
        p._process_cycle("img", 13.0)           # 10+8=18초 이전
        self.assertEqual(len(self.emitted), 1)
        p._process_cycle("img", 19.0)           # 쿨다운 경과
        self.assertEqual(len(self.emitted), 2)


class TestR1TossRecovery(PollerTestCase):
    def test_new_toss_in_playing_publishes_unknown_and_reenters_coin(self):
        p = self.make_poller()
        self.to_playing(p)
        # 결과를 놓친 채 다음 판 토스 화면 출현
        self.set_fake("recognize_coin_toss", lambda i, c: ("win", 0.9, "raw"))
        p._process_cycle("img", 60.0)

        self.assertEqual(len(self.emitted), 1)
        r = self.emitted[0]
        self.assertEqual(r.result, "unknown")   # 이전 듀얼 = 결과 미상
        self.assertEqual(r.coin_result, "second")
        self.assertEqual(r.coin_toss, "loss")
        self.assertTrue(r.needs_review)
        # 새 토스로 COIN 재진입
        self.assertIs(p._state, DuelState.COIN)
        self.assertEqual(p._pending_toss, "win")
        self.assertIsNone(p._pending_coin)

    def test_toss_ocr_throttled_in_playing(self):
        calls = []
        p = self.make_poller(playing_toss_check_cycles=5)
        self.to_playing(p)                      # cycle = 2까지 사용

        def counting_toss(img, cfg):
            calls.append(p._cycle)
            return _NONE3
        self.set_fake("recognize_coin_toss", counting_toss)
        for i in range(3, 13):                  # cycle 3..12
            p._process_cycle("img", float(i))
        self.assertEqual(calls, [5, 10])        # 5주기마다 1회만

    def test_cooldown_gates_toss_recovery(self):
        p = self.make_poller()
        self.to_playing(p)
        p._cooldown_until = 100.0               # 결과 직후 잔상 시나리오
        self.set_fake("recognize_coin_toss", lambda i, c: ("win", 0.9, "raw"))
        p._process_cycle("img", 50.0)           # 쿨다운 내 — 무시
        self.assertEqual(len(self.emitted), 0)
        self.assertIs(p._state, DuelState.PLAYING)
        p._process_cycle("img", 101.0)          # 쿨다운 경과 — 복구 동작
        self.assertEqual(len(self.emitted), 1)
        self.assertIs(p._state, DuelState.COIN)

    def test_no_toss_recovery_in_coin_state(self):
        """COIN에서는 토스 잔상(8~12초 노출)을 새 토스로 재감지하면 안 된다."""
        p = self.make_poller()
        self.set_fake("recognize_coin_toss", lambda i, c: ("loss", 0.9, "raw"))
        p._process_cycle("img", 0.0)
        self.assertIs(p._state, DuelState.COIN)
        # 같은 토스 화면이 계속 보여도 (COIN 핸들러는 coin만 인식) 발행 없음
        for i in range(1, 20):
            p._process_cycle("img", float(i))
        self.assertEqual(len(self.emitted), 0)
        self.assertIs(p._state, DuelState.COIN)


class TestR2WindowGone(PollerTestCase):
    def test_window_gone_publishes_unknown(self):
        p = self.make_poller(window_gone_cycles=3)
        self.to_playing(p)
        p.engine.last_capture_status = "not_found"
        p._process_cycle(None, 10.0)
        p._process_cycle(None, 10.5)
        self.assertEqual(len(self.emitted), 0)  # 임계 미달
        self.assertIs(p._state, DuelState.PLAYING)
        p._process_cycle(None, 11.0)            # 3회째 — 발동
        self.assertEqual(len(self.emitted), 1)
        self.assertEqual(self.emitted[0].result, "unknown")
        self.assertIs(p._state, DuelState.IDLE)

    def test_minimized_does_not_count(self):
        """최소화는 소멸이 아니다 — 카운터 동결 + 상태 유지 (IsIconic 가드)."""
        p = self.make_poller(window_gone_cycles=3)
        self.to_playing(p)
        p.engine.last_capture_status = "minimized"
        for i in range(10):
            p._process_cycle(None, 10.0 + i)
        self.assertEqual(len(self.emitted), 0)
        self.assertIs(p._state, DuelState.PLAYING)
        self.assertEqual(p._window_gone_count, 0)

    def test_capture_recovery_resets_counter(self):
        p = self.make_poller(window_gone_cycles=3)
        self.to_playing(p)
        p.engine.last_capture_status = "not_found"
        p._process_cycle(None, 10.0)
        p._process_cycle(None, 10.5)
        p.engine.last_capture_status = "ok"
        p._process_cycle("img", 11.0)           # 캡처 재개 — 카운터 리셋
        self.assertEqual(p._window_gone_count, 0)
        p.engine.last_capture_status = "not_found"
        p._process_cycle(None, 11.5)
        p._process_cycle(None, 12.0)
        self.assertEqual(len(self.emitted), 0)  # 연속 3회가 아님

    def test_idle_window_gone_is_noop(self):
        p = self.make_poller(window_gone_cycles=3)
        p.engine.last_capture_status = "not_found"
        for i in range(10):
            p._process_cycle(None, float(i))
        self.assertEqual(len(self.emitted), 0)
        self.assertIs(p._state, DuelState.IDLE)


class TestR3CoinTimeout(PollerTestCase):
    def test_coin_timeout_resets_without_publish(self):
        p = self.make_poller(coin_timeout=120.0)
        self.set_fake("recognize_coin_toss", lambda i, c: ("win", 0.9, "raw"))
        p._process_cycle("img", 0.0)
        self.assertIs(p._state, DuelState.COIN)
        self.set_fake("recognize_coin_toss", lambda i, c: _NONE3)

        p._process_cycle("img", 119.0)          # 타임아웃 전
        self.assertIs(p._state, DuelState.COIN)
        p._process_cycle("img", 121.0)          # 타임아웃 후
        self.assertIs(p._state, DuelState.IDLE)
        self.assertEqual(len(self.emitted), 0)  # 발행 없음 (토스 정보만 폐기)
        self.assertIn("IDLE", self.states)      # 복구 경로 state_changed 발행

    def test_coin_timeout_survives_ocr_exceptions(self):
        """서버오류 영상(090952) 시나리오: OCR이 계속 실패해도 타임아웃은 동작."""
        def boom(img, cfg):
            raise RuntimeError("tesseract failure")
        p = self.make_poller(coin_timeout=120.0)
        self.set_fake("recognize_coin_toss", lambda i, c: ("win", 0.9, "raw"))
        p._process_cycle("img", 0.0)
        self.set_fake("recognize_coin", boom)
        p._process_cycle("img", 121.0)
        self.assertIs(p._state, DuelState.IDLE)
        self.assertEqual(len(self.emitted), 0)


class TestP1ServerErrorThrottle(PollerTestCase):
    def test_server_error_checked_every_n_cycles(self):
        calls = []
        p = self.make_poller(server_error_check_cycles=8)

        def counting(img, cfg):
            calls.append(p._cycle)
            return False
        self.set_fake("recognize_server_error", counting)
        for i in range(1, 17):                  # cycle 1..16
            p._process_cycle("img", float(i))
        self.assertEqual(calls, [8, 16])

    def test_server_error_resets_state(self):
        p = self.make_poller(server_error_check_cycles=1)
        self.to_playing(p)
        self.set_fake("recognize_server_error", lambda i, c: True)
        p._process_cycle("img", 10.0)
        self.assertIs(p._state, DuelState.IDLE)
        self.assertEqual(len(self.emitted), 0)  # 서버오류는 발행 없이 초기화


if __name__ == "__main__":
    unittest.main()
