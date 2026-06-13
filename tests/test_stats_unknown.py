"""stats.py — result/coin_result='unknown' 제외 동작 검증 (설계 §6).

미상 결과는 win/loss/draw 어디에도 집계되지 않아 승률 분모·표본(n)에서
자연히 빠진다 — 의도된 동작.

실행: .venv/bin/python tests/test_stats_unknown.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mdtracker.models import Match  # noqa: E402
from mdtracker.stats import win_rate_summary  # noqa: E402


def _m(result, coin_result="first", **kw):
    base = dict(
        played_at="2026-06-10T12:00:00", my_deck="덱A", opponent_deck="덱B",
        coin_result=coin_result, result=result, confirmed=True,
    )
    base.update(kw)
    return Match(**base)


class TestUnknownExcluded(unittest.TestCase):
    def test_unknown_result_excluded_from_win_rate_and_n(self):
        ms = [_m("win"), _m("loss"), _m("unknown"), _m("unknown")]
        ov = win_rate_summary(ms, include_unconfirmed=True)["overall"]
        self.assertEqual(ov["wins"], 1)
        self.assertEqual(ov["losses"], 1)
        self.assertEqual(ov["draws"], 0)
        self.assertEqual(ov["n"], 2)            # unknown 2건은 표본에서 제외
        self.assertAlmostEqual(ov["win_rate"], 0.5)

    def test_unknown_coin_excluded_from_by_coin(self):
        ms = [
            _m("win", coin_result="first"),
            _m("loss", coin_result="second"),
            _m("win", coin_result="unknown"),   # R2 복구 발행 (COIN 정체)
        ]
        by_coin = win_rate_summary(ms, include_unconfirmed=True)["by_coin"]
        self.assertEqual(by_coin["first"]["n"], 1)
        self.assertEqual(by_coin["second"]["n"], 1)
        self.assertNotIn("unknown", by_coin)    # first/second만 집계

    def test_all_unknown_gives_empty_rate(self):
        ms = [_m("unknown")]
        ov = win_rate_summary(ms, include_unconfirmed=True)["overall"]
        self.assertEqual(ov["n"], 0)
        self.assertIsNone(ov["win_rate"])


if __name__ == "__main__":
    unittest.main()
