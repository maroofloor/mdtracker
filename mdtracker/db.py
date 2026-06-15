"""SQLite 스키마·연결·초기화. 데이터 계약의 저장소 측.

Database 파사드가 연결을 소유하고 MatchRepository/DeckRepository를 노출한다.
단일 연결을 공유하므로 :memory: 테스트에서도 일관된 상태를 유지한다.
"""

import sqlite3
from pathlib import Path
from typing import Union

from .repository import MatchRepository, DeckRepository

SCHEMA_VERSION = "3"

SCHEMA_SQL = """
-- 정식 덱(아키타입) 명칭 룩업
CREATE TABLE IF NOT EXISTS decks (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL UNIQUE,          -- canonical 명칭
    is_mine  INTEGER NOT NULL DEFAULT 0
);

-- 대전 기록 (핵심 테이블)
CREATE TABLE IF NOT EXISTS matches (
    id              INTEGER PRIMARY KEY,
    played_at       TEXT NOT NULL,          -- ISO8601
    my_deck         TEXT NOT NULL,
    opponent_deck   TEXT NOT NULL,
    opponent_raw    TEXT,                   -- OCR 원문(미확정 시 보존)
    coin_result     TEXT NOT NULL,          -- 'first' | 'second' | 'unknown' (토스 승자의 선택 결과)
    coin_toss       TEXT,                   -- 'win' | 'loss' — 내가 토스를 이겼는지(미기록 NULL)
    result          TEXT NOT NULL,          -- 'win' | 'loss' | 'draw' | 'unknown' (OCR 복구 미상)
    rank_label      TEXT,
    season          TEXT,
    event_type      TEXT NOT NULL DEFAULT 'ranked',
    source          TEXT NOT NULL DEFAULT 'manual',
    ocr_confidence  REAL,                   -- 0~1, manual이면 NULL
    confirmed       INTEGER NOT NULL DEFAULT 1,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_matches_played_at ON matches(played_at);
CREATE INDEX IF NOT EXISTS idx_matches_matchup   ON matches(my_deck, opponent_deck);

-- 덱별 대표 카드 아트 매핑 (덱명 문자열 키 — decks 테이블 등록 여부와 무관)
CREATE TABLE IF NOT EXISTS deck_art (
    deck_name   TEXT PRIMARY KEY,
    card_id     INTEGER,                -- YGOPRODeck 카드 id
    query       TEXT,                   -- 조회에 쓴 영문 아키타입/카드명
    source      TEXT NOT NULL DEFAULT 'auto',  -- 'auto' | 'manual'
    image_path  TEXT,                   -- 로컬 캐시 경로(없으면 NULL)
    updated_at  TEXT
);

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- 앱 UI 설정(세션 내 덱·타입 등) 영속 저장 (재시작 시 복원)
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def connect(db_path: Union[str, Path]) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return any(r["name"] == column
               for r in conn.execute(f"PRAGMA table_info({table})"))


def _migrate(conn: sqlite3.Connection) -> None:
    # v1 → v2: matches.coin_toss 추가 (기존 DB는 컬럼이 없으므로 ALTER)
    if not _column_exists(conn, "matches", "coin_toss"):
        conn.execute("ALTER TABLE matches ADD COLUMN coin_toss TEXT")


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)   # 신규 DB는 coin_toss 포함해 생성
    _migrate(conn)                   # 기존 DB는 누락 컬럼만 보강
    conn.execute(
        "INSERT INTO schema_meta (key, value) VALUES ('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (SCHEMA_VERSION,),
    )
    conn.commit()


class Database:
    """앱 전역에서 사용하는 DB 파사드."""

    def __init__(self, db_path: Union[str, Path] = ":memory:"):
        self.conn = connect(db_path)
        init_db(self.conn)
        self.matches = MatchRepository(self.conn)
        self.decks = DeckRepository(self.conn)

    # ---- 앱 설정 (세션 내 덱·타입 등 UI 상태 영속) ----
    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
