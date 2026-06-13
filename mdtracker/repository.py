"""DAO 계층 — SQL을 캡슐화하고 도메인 모델을 주고받는다.

통계 엔진이 필요로 하는 조회(필터)를 모두 노출한다.
UI는 저장·수정·삭제를 위해 이 계층만 호출하고 직접 SQL을 쓰지 않는다.
"""

from __future__ import annotations

import difflib
import sqlite3
from typing import Optional

from .models import Match, Deck


def _row_to_match(row: sqlite3.Row) -> Match:
    return Match(
        id=row["id"],
        played_at=row["played_at"],
        my_deck=row["my_deck"],
        opponent_deck=row["opponent_deck"],
        opponent_raw=row["opponent_raw"],
        coin_result=row["coin_result"],
        coin_toss=row["coin_toss"],
        result=row["result"],
        rank_label=row["rank_label"],
        season=row["season"],
        event_type=row["event_type"],
        source=row["source"],
        ocr_confidence=row["ocr_confidence"],
        confirmed=bool(row["confirmed"]),
        notes=row["notes"],
    )


class MatchRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, m: Match) -> int:
        cur = self.conn.execute(
            """INSERT INTO matches
               (played_at, my_deck, opponent_deck, opponent_raw, coin_result,
                coin_toss, result, rank_label, season, event_type, source,
                ocr_confidence, confirmed, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (m.played_at, m.my_deck, m.opponent_deck, m.opponent_raw,
             m.coin_result, m.coin_toss, m.result, m.rank_label, m.season,
             m.event_type, m.source, m.ocr_confidence, int(m.confirmed),
             m.notes),
        )
        self.conn.commit()
        m.id = cur.lastrowid
        return m.id

    def update(self, m: Match) -> None:
        if m.id is None:
            raise ValueError("update에는 id가 필요합니다")
        self.conn.execute(
            """UPDATE matches SET
               played_at=?, my_deck=?, opponent_deck=?, opponent_raw=?,
               coin_result=?, coin_toss=?, result=?, rank_label=?, season=?,
               event_type=?, source=?, ocr_confidence=?, confirmed=?, notes=?
               WHERE id=?""",
            (m.played_at, m.my_deck, m.opponent_deck, m.opponent_raw,
             m.coin_result, m.coin_toss, m.result, m.rank_label, m.season,
             m.event_type, m.source, m.ocr_confidence, int(m.confirmed),
             m.notes, m.id),
        )
        self.conn.commit()

    def delete(self, match_id: int) -> None:
        self.conn.execute("DELETE FROM matches WHERE id = ?", (match_id,))
        self.conn.commit()

    def delete_all(self) -> None:
        self.conn.execute("DELETE FROM matches")
        self.conn.commit()

    def get(self, match_id: int) -> Optional[Match]:
        row = self.conn.execute(
            "SELECT * FROM matches WHERE id = ?", (match_id,)
        ).fetchone()
        return _row_to_match(row) if row else None

    def list(self, *, my_deck: Optional[str] = None,
             opponent_deck: Optional[str] = None,
             season: Optional[str] = None,
             event_type: Optional[str] = None,
             since: Optional[str] = None,
             until: Optional[str] = None) -> list[Match]:
        clauses, params = [], []
        if my_deck is not None:
            clauses.append("my_deck = ?"); params.append(my_deck)
        if opponent_deck is not None:
            clauses.append("opponent_deck = ?"); params.append(opponent_deck)
        if season is not None:
            clauses.append("season = ?"); params.append(season)
        if event_type is not None:
            clauses.append("event_type = ?"); params.append(event_type)
        if since is not None:
            clauses.append("played_at >= ?"); params.append(since)
        if until is not None:
            clauses.append("played_at <= ?"); params.append(until)

        sql = "SELECT * FROM matches"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY played_at"
        return [_row_to_match(r) for r in self.conn.execute(sql, params)]

    def all(self) -> list[Match]:
        return self.list()

    def export_csv(self, path) -> int:
        import csv
        from pathlib import Path
        rows = self.all()
        fieldnames = [
            "id", "played_at", "my_deck", "opponent_deck", "opponent_raw",
            "coin_result", "coin_toss", "result", "rank_label", "season",
            "event_type", "source", "ocr_confidence", "confirmed", "notes",
        ]
        with open(Path(path), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            for m in rows:
                w.writerow({
                    "id": m.id, "played_at": m.played_at,
                    "my_deck": m.my_deck, "opponent_deck": m.opponent_deck,
                    "opponent_raw": m.opponent_raw, "coin_result": m.coin_result,
                    "coin_toss": m.coin_toss, "result": m.result,
                    "rank_label": m.rank_label, "season": m.season,
                    "event_type": m.event_type, "source": m.source,
                    "ocr_confidence": m.ocr_confidence,
                    "confirmed": int(m.confirmed), "notes": m.notes,
                })
        return len(rows)


class DeckRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list(self) -> list[Deck]:
        return [
            Deck(id=r["id"], name=r["name"], is_mine=bool(r["is_mine"]))
            for r in self.conn.execute(
                "SELECT * FROM decks ORDER BY is_mine DESC, name")
        ]

    def list_names(self) -> list[str]:
        return [r["name"] for r in
                self.conn.execute(
                    "SELECT name FROM decks ORDER BY is_mine DESC, name")]

    def list_mine_names(self) -> list[str]:
        """is_mine=True 덱 이름만 반환."""
        return [r["name"] for r in
                self.conn.execute(
                    "SELECT name FROM decks WHERE is_mine=1 ORDER BY name")]

    def set_mine(self, deck_id: int, is_mine: bool) -> None:
        """덱의 내 덱 여부를 토글한다."""
        self.conn.execute(
            "UPDATE decks SET is_mine=? WHERE id=?", (int(is_mine), deck_id))
        self.conn.commit()

    def add(self, name: str, is_mine: bool = False) -> int:
        self.conn.execute(
            "INSERT OR IGNORE INTO decks (name, is_mine) VALUES (?, ?)",
            (name, int(is_mine)),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM decks WHERE name = ?", (name,)
        ).fetchone()
        return row["id"]

    def rename(self, deck_id: int, new_name: str) -> None:
        """덱 이름을 변경하고 matches 테이블 참조도 일괄 갱신한다."""
        old_row = self.conn.execute(
            "SELECT name FROM decks WHERE id=?", (deck_id,)
        ).fetchone()
        if old_row is None:
            return
        old_name = old_row["name"]
        self.conn.execute(
            "UPDATE decks SET name=? WHERE id=?", (new_name, deck_id))
        self.conn.execute(
            "UPDATE matches SET my_deck=? WHERE my_deck=?", (new_name, old_name))
        sel