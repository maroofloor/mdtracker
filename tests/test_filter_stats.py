"""stats.filter_matches — 필터바 공용 순수 필터 검증.

기간(period)·덱·타입·결과·선후공·코인토스 축별 필터와
조건 None(전체) 통과, coin_toss 미기록(None) 제외를 확인한다.

실행: .venv/bin/python tests/test_filter_stats.py
"""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mdtracker.models import Match  # noqa: E402
from mdtracker.stats import filter_matches  # noqa: E402

TODAY = date(2026, 6, 10)


def _m(played_at="2026-06-10T12:00:00", my_deck="덱A", opp="덱B",
       coin_result="first", coin_toss=None, result="win",
       event_type="ranked", **kw):
    return Match(
        played_at=played_at, my_deck=my_deck, opponent_deck=opp,
        coin_result=coin_result, coin_toss=coin_toss, result=result,
        event_type=event_type, **kw,
    )


class TestPeriod(unittest.TestCase):
    def setUp(self):
        self.ms = [
            _m(played_at="2026-06-10T09:00:00"),   # 오늘
            _m(played_at="2026-06-05T09:00:00"),   # 5일 전
            _m(played_at="2026-06-01T09:00:00"),   # 이번 달 첫날
            _m(played_at="2026-05-20T09:00:00"),   # 30일 이내
            _m(played_at="2026-04-01T09:00:00"),   # 그 이전
        ]

    def test_all(self):
        self.assertEqual(len(filter_matches(self.ms, today=TODAY)), 5)

    def test_today(self):
        out = filter_matches(self.ms, period="today", today=TODAY)
        self.assertEqual([m.played_at[:10] for m in out], ["2026-06-10"])

    def test_7d(self):
        out = filter_matches(self.ms, period="7d", today=TODAY)
        self.assertEqual(len(out), 2)   # 06-10, 06-05 (06-04 이후)

    def test_30d(self):
        out = filter_matches(self.ms, period="30d", today=TODAY)
        self.assertEqual(len(out), 4)   # 05-12 이후

    def test_month(self):
        out = filter_matches(self.ms, period="month", today=TODAY)
        self.assertEqual(len(out), 3)   # 06-01 포함

    def test_invalid_period_raises(self):
        with self.assertRaises(ValueError):
            filter_matches(self.ms, period="year", today=TODAY)


class TestFields(unittest.TestCase):
    def setUp(self):
        self.ms = [
            _m(my_deck="덱A", opp="덱B", result="win",
               coin_result="first", coin_toss="win", event_type="ranked"),
            _m(my_deck="덱A", opp="덱C", result="loss",
               coin_result="second", coin_toss="loss", event_type="event"),
            _m(my_deck="덱D", opp="덱B", result="draw",
               coin_result="unknown", coin_toss=None, event_type="wcs"),
        ]

    def test_my_deck(self):
        self.assertEqual(len(filter_matches(self.ms, my_deck="덱A")), 2)

    def test_opponent_deck(self):
        self.assertEqual(len(filter_matches(self.ms, opponent_deck="덱B")), 2)

    def test_event_type(self):
        self.assertEqual(len(filter_matches(self.ms, event_type="wcs")), 1)

    def test_result(self):
        self.assertEqual(len(filter_matches(self.ms, result="loss")), 1)

    def test_coin_result(self):
        self.assertEqual(
            len(filter_matches(self.ms, coin_result="unknown")), 1)

    def test_coin_toss_excludes_none(self):
        # coin_toss 필터 지정 시 미기록(None) 게임은 제외된다
        self.assertEqual(len(filter_matches(self.ms, coin_toss="win")), 1)
        self.assertEqual(len(filter_matches(self.ms, coin_toss="loss")), 1)

    def test_combined(self):
        out = filter_matches(self.ms, my_deck="덱A", result="win")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].opponent_deck, "덱B")

    def test_none_passes_all(self):
        self.assertEqual(len(filter_matches(self.ms)), 3)


if __name__ == "__main__":
    unittest.main()
