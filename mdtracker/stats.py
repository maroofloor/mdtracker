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


# ---- 통계 ----
def win_rate_summary(matches: Sequence[Match], *,
                     since: Optional[str] = None,
                     include_unconfirmed: bool = False) -> dict:
    """전체 / 내 덱별 / 선·후공별 승률.

    반환:
      {
        "overall": {wins, losses, draws, win_rate, n},
        "by_my_deck": {deck: {wins, losses, draws, win_rate, n}, ...},
        "by_coin": {"first": {...}, "second": {...}},        # 선/후공별 승률
        "by_coin_toss": {"win": {...}, "loss": {...}},        # 토스 승/패별 듀얼 승률
        "coin_toss_rate": {"win": int, "loss": int, "rate": float|None, "n": int},
            # 코인토스 자체를 이긴 비율 (win=토스승 게임수, loss=토스패 게임수,
            #  n=win+loss, rate=win/n). coin_toss=None인 게임은 제외.
        "toss_win_choice": {"first": int, "second": int, "n": int,
                            "by_choice": {"first": {...tally}, "second": {...tally}}},
            # 토스를 이겼을 때 선공/후공 선택 횟수 + 선택별 듀얼 승률 (coin_toss='win'만)
      }
    coin_toss가 None(미기록)인 게임은 by_coin_toss·coin_toss_rate·toss_win_choice
    집계에서 제외된다.
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
    toss_win = sum(1 for m in ms if m.coin_toss == "win")
    toss_loss = sum(1 for m in ms if m.coin_toss == "loss")
    coin_toss_rate = {
        "win": toss_win,
        "loss": toss_loss,
        "rate": _rate(toss_win, toss_win + toss_loss),
        "n": toss_win + toss_loss,
    }
    won_toss = [m for m in ms if m.coin_toss == "win"]
    toss_win_choice = {
        "first": sum(1 for m in won_toss if m.coin_result == "first"),
        "second": sum(1 for m in won_toss if m.coin_result == "second"),
        "n": len(won_toss),
        "by_choice": {
            "first": _tally([m for m in won_toss if m.coin_result == "first"]),
            "second": _tally([m for m in won_toss if m.coin_result == "second"]),
        },
    }
    return {
        "overall": _tally(ms),
        "by_my_deck": by_my_deck,
        "by_coin": by_coin,
        "by_coin_toss": by_coin_toss,
        "coin_toss_rate": coin_toss_rate,
        "toss_win_choice": toss_win_choice,
    }


def session_summary(matches: Sequence[Match], *,
                    since: str,
                    include_unconfirmed: bool = False) -> dict:
    """한 구간(세션/오늘 등)의 요약 — played_at >= since 인 판들만 집계.

    since: ISO 문자열 (세션 시작 타임스탬프 또는 'YYYY-MM-DD' 날짜).
           ISO 문자열 사전식 비교가 시간순과 일치하므로 그대로 쓴다.

    반환(_tally 키 + 스트릭):
      {wins, losses, draws, win_rate, n,
       current_streak: {type, count}, best_streak: {win, loss}}
    빈 구간이면 n=0, win_rate=None, 스트릭 0을 돌려준다(예외 없음).
    """
    ms = sorted(
        (m for m in _select(matches, include_unconfirmed) if m.played_at >= since),
        key=lambda m: m.played_at,
    )
    return {
        **_tally(ms),
        "current_streak": _current_streak(ms),
        "best_streak": _best_streak(ms),
    }


def _goal_num(value, *, as_int: bool) -> Optional[float]:
    """app_settings 문자열 목표값을 숫자로. 미설정/0/파싱실패는 None(목표 없음)."""
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num <= 0:
        return None
    return float(int(num)) if as_int else num


def goal_progress(matches: Sequence[Match], *,
                  goals: dict,
                  today: Optional[_date] = None,
                  include_unconfirmed: bool = False) -> dict:
    """일일 판수·일일 승률·연승 목표의 현재값/목표값/진행률/달성여부.

    goals: {"daily_games": <int>, "daily_winrate": <0~1 float>, "streak": <int>}
           각 값은 문자열(app_settings)이어도 되고, 미설정/0이면 그 목표는 비활성.
    today: 기준일 주입용(테스트). 기본 date.today().

    반환:
      {
        "daily_games":   {current:int,   target:int|None,   ratio:float|None, achieved:bool},
        "daily_winrate": {current:float|None, target:float|None, ratio:float|None,
                          achieved:bool, n:int},
        "streak":        {current:int,   target:int|None,   ratio:float|None, achieved:bool},
      }
    ratio는 0~1로 클램프(달성 시 1.0). target이 None이면 ratio=None(미설정).
    daily_games는 오늘 친 모든 판(결과 unknown 포함), daily_winrate의 n은 결정 게임 수.
    연승 current는 현재 연승 중일 때만 양수(연패 중이면 0).
    """
    today = today or _date.today()
    ms = _select(matches, include_unconfirmed)
    today_str = today.isoformat()
    todays = [m for m in ms if m.played_at[:10] == today_str]
    today_tally = _tally(todays)
    streak = _current_streak(sorted(ms, key=lambda m: m.played_at))
    cur_win_streak = streak["count"] if streak["type"] == "win" else 0

    def _entry(current, target) -> dict:
        if target is None:
            return {"current": current, "target": None,
                    "ratio": None, "achieved": False}
        base = current or 0
        return {"current": current, "target": target,
                "ratio": min(1.0, base / target) if target else None,
                "achieved": base >= target}

    games_target = _goal_num(goals.get("daily_games"), as_int=True)
    wr_target = _goal_num(goals.get("daily_winrate"), as_int=False)
    streak_target = _goal_num(goals.get("streak"), as_int=True)

    games = _entry(len(todays), int(games_target) if games_target else None)
    wr = _entry(today_tally["win_rate"], wr_target)
    wr["n"] = today_tally["n"]
    streak_e = _entry(cur_win_streak, int(streak_target) if streak_target else None)
    return {"daily_games": games, "daily_winrate": wr, "streak": streak_e}


def _bucket_key(played_at: str, bucket: str) -> str:
    """played_at(ISO)을 집계 버킷 키(ISO 날짜 문자열)로. week는 그 주 월요일."""
    day = played_at[:10]
    if bucket == "day":
        return day
    d = _date.fromisoformat(day)
    return (d - _timedelta(days=d.weekday())).isoformat()   # ISO 주 월요일


def trend_series(matches: Sequence[Match], *,
                 include_unconfirmed: bool = False,
                 window: int = 20,
                 bucket: str = "day") -> dict:
    """일별/주별 승률 + 누적 승률 시계열, 게임 단위 롤링 승률, 스트릭, 랭크 이력.

    인자:
      window: game_points의 롤링(이동평균) 승률 창 크기 (기본 20전).
      bucket: 'day'(기본) | 'week'(ISO 주 단위, 그 주 월요일 날짜로 표기).

    반환:
      {
        "points": [{date, win_rate, n, wins, losses, cumulative_win_rate}, ...],
            # bucket='week'이면 date는 그 주 월요일(YYYY-MM-DD)
        "game_points": [{index, result, cumulative_win_rate, rolling_win_rate}, ...],
            # 결정 게임(win/loss)만 시간순 1부터 인덱싱. rolling은 최근 window전 승률.
        "current_streak": {"type": "win"|"loss"|None, "count": int},
        "best_streak": {"win": int, "loss": int},
        "rank_history": [{date, rank_label}, ...],
      }
    """
    if bucket not in ("day", "week"):
        raise ValueError(f"알 수 없는 bucket: {bucket!r}")
    window = max(1, int(window))
    ms = sorted(_select(matches, include_unconfirmed), key=lambda m: m.played_at)

    by_date: "OrderedDict[str, list[Match]]" = OrderedDict()
    for m in ms:
        by_date.setdefault(_bucket_key(m.played_at, bucket), []).append(m)

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

    # 게임 단위 시계열 — 결정 게임만, 누적·롤링 승률
    game_points = []
    flags: list[int] = []          # 1=win, 0=loss
    g_wins = 0
    for m in ms:
        if m.result not in ("win", "loss"):
            continue
        is_win = 1 if m.result == "win" else 0
        flags.append(is_win)
        g_wins += is_win
        recent = flags[-window:]
        game_points.append({
            "index": len(flags),                       # 1-based 게임 번호
            "result": m.result,
            "cumulative_win_rate": g_wins / len(flags),
            "rolling_win_rate": sum(recent) / len(recent),
        })

    rank_history = [
        {"date": m.played_at[:10], "rank_label": m.rank_label}
        for m in ms if m.rank_label
    ]
    return {
        "points": points,
        "game_points": game_points,
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
        "cells": [[{win_rate, n, wins, losses,
                    "first": {win_rate, n, wins, losses},   # 내가 선공
                    "second": {win_rate, n, wins, losses}}, ...열], ...행],
      }
    cells[i][j]는 my_decks[i] vs opp_decks[j]. 표본 0인 셀은 win_rate=None, n=0.
    first/second는 coin_result로 분리한 선/후공별 승률. coin_result='unknown'은
    전체(win_rate/n)에는 포함되지만 first·second 어느 쪽에도 들어가지 않는다.
    """
    ms = _select(matches, include_unconfirmed)
    my_decks = sorted({m.my_deck for m in ms})
    opp_decks = sorted({m.opponent_deck for m in ms})

    # (my, opp) -> matches 로 한 번만 그룹핑 (O(N))
    grouped: dict = {}
    for m in ms:
        grouped.setdefault((m.my_deck, m.opponent_deck), []).append(m)

    def _coin_cell(group: list, coin: str) -> dict:
        st = _tally([m for m in group if m.coin_result == coin])
        return {"win_rate": st["win_rate"], "n": st["n"],
                "wins": st["wins"], "losses": st["losses"]}

    cells = []
    for my in my_decks:
        row = []
        for opp in opp_decks:
            group = grouped.get((my, opp), [])
            st = _tally(group)
            row.append({"win_rate": st["win_rate"], "n": st["n"],
                        "wins": st["wins"], "losses": st["losses"],
                        "first": _coin_cell(group, "first"),
                        "second": _coin_cell(group, "second")})
        cells.append(row)
    return {"my_decks": my_decks, "opp_decks": opp_decks, "cells": cells}


def opponent_meta(matches: Sequence[Match], *, season: Optional[str] = None,
                  include_unconfirmed: bool = False) -> dict:
    """마주친 상대 덱 분포 (파이/바 차트용).

    반환:
      {
        "distribution": [
            {deck, count, share,
             wins, losses, win_rate,   # 그 덱 상대로 내 전적·승률(decided=0이면 None)
             threat},                  # share * (1 - (win_rate or 0)) — 빈도×약점
            ...],                      # count 내림차순, share 0~1
        "total": int,
      }
    threat(위협 지수)는 자주 만나면서(높은 share) 내가 약한(낮은 win_rate) 덱일수록
    크다. win_rate=None(전적 미결정)이면 (1-0)=1로 보아 빈도만큼 위협으로 본다.
    """
    ms = _select(matches, include_unconfirmed)
    if season is not None:
        ms = [m for m in ms if m.season == season]

    counts = Counter(m.opponent_deck for m in ms)
    total = sum(counts.values())
    by_deck: dict = {}
    for m in ms:
        by_deck.setdefault(m.opponent_deck, []).append(m)

    distribution = []
    for deck, count in counts.most_common():
        st = _tally(by_deck[deck])
        share = count / total if total else 0.0
        wr = st["win_rate"]
        distribution.append({
            "deck": deck, "count": count, "share": share,
            "wins": st["wins"], "losses": st["losses"], "win_rate": wr,
            "threat": share * (1 - (wr or 0.0)),
        })
    return {"distribution": distribution, "total": total}


def meta_delta(matches: Sequence[Match], *, season: str, prev_season: str,
               include_unconfirmed: bool = False) -> dict:
    """두 시즌 간 상대 덱 점유율(share) 변화.

    반환:
      {deck: {"share": float, "prev_share": float, "delta": float}, ...}
        share      = 현재 시즌 점유율
        prev_share = 직전 시즌 점유율
        delta      = share - prev_share
    두 시즌 중 한쪽에만 등장한 덱은 없는 쪽 share를 0.0으로 본다.
    UI는 계산하지 말고 이 함수 결과만 표시한다 (순수 함수).
    """
    cur = {d["deck"]: d["share"] for d in opponent_meta(
        matches, season=season, include_unconfirmed=include_unconfirmed
    )["distribution"]}
    prev = {d["deck"]: d["share"] for d in opponent_meta(
        matches, season=prev_season, include_unconfirmed=include_unconfirmed
    )["distribution"]}
    out: dict = {}
    for deck in set(cur) | set(prev):
        c = cur.get(deck, 0.0)
        p = prev.get(deck, 0.0)
        out[deck] = {"share": c, "prev_share": p, "delta": c - p}
    return out
