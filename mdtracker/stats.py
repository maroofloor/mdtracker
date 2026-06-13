"""통계 엔진 — match 레코드를 UI 친화적 통계 구조로 변환한다.

설계 결정(확정):
- win_rate = wins / (wins + losses).  무승부는 분모에서 제외하고 draws로 별도 보고.
  결정난 게임이 0이면 win_rate = None (0 나누기 방어).
- 모든 집계는 sample_size(n)를 함께 반환한다. n = wins + losses + draws.
- result='unknown'(OCR 복구가 놓친 듀얼)은 win/loss/draw 어디에도 집계되지 않아
  승률 분모·표본(n)에서 자연히 빠진다 — 의도된 동작 (설계 §6).
  coin_result='unknown'도 같은 이유로 by_coin 집계에서 제외된다.
- confirmed=False(미확정 OCR 데이터)는 기본 제외. include_unconfirmed=True로 포함.
- 빈 데이터셋에서도 빈 구조를 반환하고 예외를 던지지 않는다.

함수는 순수 함수다 — DAO에서 받은 list[Match]를 입력으로 받아 계산만 한다.
"""

from __future__ import annotations

from collections import Counter, OrderedDict
from datetime import date as _date, timedelta as _timedelta
from typing import Optional, Sequence

from .models import Match

# filter_matches()의 period 허용값 — UI 필터바와 공유한다
FILTER_PERIODS = ("all", "today", "7d", "30d", "month")


# ---- 내부 헬퍼 ----
def _select(matches: Sequence[Match], include_unconfirmed: bool) -> list[Match]:
    if include_unconfirmed:
        return list(matches)
    return [m for m in matches if m.confirmed]


def _rate(wins: int, decided: int) -> Optional[float]:
    return (wins / decided) if decided else None


def _tally(matches: Sequence[Match]) -> dict:
    wins = losses = draws = 0
    for m in matches:
        if m.result == "win":
            wins += 1
        elif m.result == "loss":
            losses += 1
        elif m.result == "draw":
            draws += 1
    return {
        "wins": wins, "losses": losses, "draws": draws,
        "win_rate": _rate(wins, wins + losses),
        "n": wins + losses + draws,
    }


def _current_streak(matches_sorted: Sequence[Match]) -> dict:
    """최신 결정 게임부터 연속 동일 결과 카운트(무승부는 건너뜀)."""
    streak_type = None
    count = 0
    for m in reversed(matches_sorted):
        if m.result == "draw":
            continue
        if streak_type is None:
            streak_type, count = m.result, 1
        elif m.result == streak_type:
            count += 1
        else:
            break
    return {"type": streak_type, "count": count}



def _best_streak(matches_sorted: Sequence[Match]) -> dict:
    """역대 최장 연승/연패. {win: int, loss: int}"""
    best_win = best_loss = 0
    cur_type: Optional[str] = None
    cur_count = 0
    for m in matches_sorted:
        if m.result == "draw":
            continue
        if cur_type == m.result:
            cur_count += 1
        else:
            cur_type, cur_count = m.result, 1
        if cur_type == "win":
            best_win = max(best_win, cur_count)
        elif cur_type == "loss":
            best_loss = max(best_loss, cur_count)
    return {"win": best_win, "loss": best_loss}


# ---- 필터 ----
def filter_matches(matches: Sequence[Match], *,
                   period: str = "all",
                   my_deck: Optional[str] = None,
                   opponent_deck: Optional[str] = None,
                   event_type: Optional[str] = None,
                   result: Optional[str] = None,
                   coin_result: Optional[str] = None,
                   coin_toss: Optional[str] = None,
                   season: Optional[str] = None,
                   today: Optional[_date] = None) -> list[Match]:
    """UI 필터바 공용 순수 필터 — 조건이 None이면 해당 축은 거르지 않는다.

    period: 'all' | 'today' | '7d' | '30d' | 'month' (이번 달).
    today는 테스트 주입용 기준일 (기본 date.today()).
    coin_toss 필터 지정 시 미기록(None)인 게임은 제외된다.
    """
    if period not in FILTER_PERIODS:
        raise ValueError(f"알 수 없는 period: {period!r}")
    ms = list(matches)
    if period != "all":
        t = today or _date.today()
        if period == "today":
            since = t.isoformat()
        elif period == "7d":
            since = (t - _timedelta(days=6)).isoformat()
        elif period == "30d":
            since = (t - _timedelta(days=29)).isoformat()
        else:  # 'month'
            since = t.isoformat()[:7] + "-01"
        ms = [m for m in ms if m.played_at[:10] >= since]
    if my_deck is not None:
        ms = [m for m in ms if m.my_deck == my_deck]
    if opponent_deck is not None:
        ms = [m for m in ms if m.opponent_deck == opponent_deck]
    if event_type is not None:
        ms = [m for m in ms if m.event_type == event_type]
    if result is not None:
        ms = [m for m in ms if m.result == result]
    if coin_result is not None:
        ms = [m for m in ms if m.coin_result == coin_result]
    if coin_toss is not None:
        ms = [m for m in ms if m.coin_toss == coin_toss]
    if season is not None:
        ms = [m for m in ms if m.season == season]
    return ms


# ---- 통계 4종 ----
def win_rate_summary(matches: Sequence[Match], *,
                     since: Optional[str] = None,
                     include_unconfirmed: bool = False) -> dict:
    """전체 / 내 덱별 / 선·후공별 승률.

    반환:
      {
        "overall": {wins, losses, draws, win_rate, n},
        "by_my_deck": {deck: {wins, losses, draws, win_rate, n}, ...},
        "by_coin": {"first": {...}, "second": {...}},        # 선/후공별 승률
        "by_coin_toss": {"win": {...}, "loss": {...}},        # 토스 승/패별 승률
        "toss_win_choice": {"first": int, "second": int, "n": int},
            # 토스를 이겼을 때 선공/후공 선택 횟수 (coin_toss='win'인 게임만)
      }
    coin_toss가 None(미기록)인 게임은 by_coin_toss·toss_win_choice 집계에서 제외된다.
    """
    ms = _select(matches, include_unconfirmed)
    if since is not None:
        ms = [m for m in ms if m.played_at >= since]
    by_my_deck = {
        deck: _tally([m for m in ms if m.my_deck == deck])
        for deck in sorted({m.my_deck for m in ms})
    }
    by_coin = {
        coin: _tally([m for m in ms if m.coin_result == coin])
        for coin in ("first", "second")
    }
    by_coin_toss = {
        toss: _tally([m for m in ms if m.coin_toss == toss])
        for toss in ("win", "loss")
    }
    won_toss = [m for m in ms if m.coin_toss == "win"]
    toss_win_choice = {
        "first": sum(1 for m in won_toss if m.coin_result == "first"),
        "second": sum(1 for m in won_toss if m.coin_result == "second"),
        "n": len(won_toss),
    }
    return {
        "overall": _tally(ms),
        "by_my_deck": by_my_deck,
        "by_coin": by_coin,
        "by_coin_toss": by_coin_toss,
        "toss_win_choice": toss_win_choice,
    }


def trend_series(matches: Sequence[Match], *,
                 include_unconfirmed: bool = False) -> dict:
    """일별 승률 + 누적 승률 시계열, 현재 스트릭, 랭크 이력.

    반환:
      {
        "points": [{date, win_rate, n, wins, losses, cumulative_win_rate}, ...],
        "current_streak": {"type": "win"|"loss"|None, "count": int},
        "rank_history": [{date, rank_label}, ...],
      }
    """
    ms = sorted(_select(matches, include_unconfirmed), key=lambda m: m.played_at)

    by_date: "OrderedDict[str, list[Match]]" = OrderedDict()
    for m in ms:
        by_date.setdefault(m.played_at[:10], []).append(m)

    points = []
    cum_wins = cum_decided = 0
    for date, day_ms in by_date.items():
        st = _tally(day_ms)
        cum_wins += st["wins"]
        cum_decided += st["wins"] + st["losses"]
        points.append({
            "date": date, "win_rate": st["win_rate"], "n": st["n"],
            "wins": st["wins"], "losses": st["losses"],
            "cumulative_win_rate": _rate(cum_wins, cum_decided),
        })

    rank_history = [
        {"date": m.played_at[:10], "rank_label": m.rank_label}
        for m in ms if m.rank_label
    ]
    return {
        "points": points,
        "current_streak": _current_streak(ms),
        "best_streak": _best_streak(ms),
        "rank_history": rank_history,
    }


def matchup_matrix(matches: Sequence[Match], *,
                   include_unconfirmed: bool = False) -> dict:
    """내 덱 × 상대 덱 조합별 승률 (히트맵용 2D 리스트).

    반환:
      {
        "my_decks": [row labels],
        "opp_decks": [col labels],
        "cells": [[{win_rate, n, wins, losses}, ...열], ...행],  # cells[i][j]
      }
    cells[i][j]는 my_decks[i] vs opp_decks[j]. 표본 0인 셀은 win_rate=None, n=0.
    """
    ms = _select(matches, include_unconfirmed)
    my_decks = sorted({m.my_deck for m in ms})
    opp_decks = sorted({m.opponent_deck for m in ms})

    # (my, opp) -> matches 로 한 번만 그룹핑 (O(N))
    grouped: dict = {}
    for m in ms:
        grouped.setdefault((m.my_deck, m.opponent_deck), []).append(m)

    cells = []
    for my in my_decks:
        row = []
        for opp in opp_decks:
            st = _tally(grouped.get((my, opp), []))
            row.append({"win_rate": st["win_rate"], "n": st["n"],
                        "wins": st["wins"], "losses": st["losses"]})
        cells.append(row)
    return {"my_decks": my_decks, "opp_decks": opp_decks, "cells": cells}


def opponent_meta(matches: Sequence[Match], *, season: Optional[str] = None,
                  include_unconfirmed: bool = False) -> dict:
    """마주친 상대 덱 분포 (파이/바 차트용).

    반환:
      {
        "distribution": [{deck, count, share}, ...],  # count 내림차순, share 0~1
        "total": int,
      }
    """
    ms = _select(matches, include_unconfirmed)
    if season is not None:
        ms = [m for m in ms if m.season == season]

    counts = Counter(m.opponent_deck for m in ms)
    total = sum(counts.values())
    distribution = [
        {"deck": deck, "count": count,
         "share": (count / total if total else 0.0)}
        for deck, count in counts.most_common()
    ]
    return {"distribution": distribution, "total": total}
