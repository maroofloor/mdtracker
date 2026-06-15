"""번들된 메타데이터 DB(yugioh.sqlite)로 덱명 → 대표 카드 이미지 URL 해석.

- 이 DB에는 한/영/일 아키타입 이름 + 대표 카드 id + 이미지 URL만 들어있다(이미지 파일 X).
  이미지 자체는 사용자별로 URL에서 받아 로컬 캐시에 저장한다(cache.py) — 재배포·핫링크 없음.
- DB는 `assets/cardart/yugioh.sqlite`로 번들되며, 개발 시에는 형제 폴더
  `../yu-gi-oh_DB/data/yugioh.sqlite`를 우선 사용한다(최신본 편의).
- Qt 비의존.
"""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Optional

from . import archetypes

_NORM_RE = re.compile(r"[\s\-_.·•＠()\"'／/]")


def _norm(s: str) -> str:
    if not s:
        return ""
    return _NORM_RE.sub("", s.strip().lower())


def locate_db() -> Optional[Path]:
    """메타데이터 DB 경로를 찾는다(없으면 None)."""
    candidates = []
    env = os.environ.get("MDTRACKER_CARDDB")
    if env:
        candidates.append(Path(env))
    root = Path(__file__).resolve().parents[2]   # mdtracker 저장소(또는 _internal) 루트
    candidates.append(root.parent / "yu-gi-oh_DB" / "data" / "yugioh.sqlite")  # 개발 형제
    candidates.append(root / "assets" / "cardart" / "yugioh.sqlite")           # 번들
    for c in candidates:
        try:
            if c and Path(c).is_file():
                return Path(c)
        except OSError:
            continue
    return None


class LocalCardDB:
    """읽기 전용 메타데이터 DB 래퍼. 인덱스는 최초 사용 시 1회 구축."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._path = Path(db_path) if db_path else locate_db()
        self._conn: Optional[sqlite3.Connection] = None
        self._index: Optional[dict[str, int]] = None   # norm name -> archetype_id
        self._arch: dict[int, dict] = {}               # archetype_id -> info

    @property
    def available(self) -> bool:
        return self._path is not None and Path(self._path).is_file()

    def _connect(self) -> Optional[sqlite3.Connection]:
        if self._conn is None and self.available:
            try:
                self._conn = sqlite3.connect(
                    f"file:{self._path}?mode=ro", uri=True)
                self._conn.row_factory = sqlite3.Row
            except sqlite3.Error:
                self._conn = None
        return self._conn

    def _ensure_index(self) -> None:
        if self._index is not None:
            return
        self._index = {}
        conn = self._connect()
        if conn is None:
            return
        try:
            for r in conn.execute(
                "SELECT id, slug, source_en_name, representative_card_id "
                "FROM archetypes"
            ):
                self._arch[r["id"]] = {
                    "id": r["id"], "slug": r["slug"],
                    "en": r["source_en_name"],
                    "rid": r["representative_card_id"],
                }
                self._index.setdefault(_norm(r["source_en_name"]), r["id"])
            for r in conn.execute(
                "SELECT archetype_id, name FROM archetype_names"
            ):
                self._index.setdefault(_norm(r["name"]), r["archetype_id"])
        except sqlite3.Error:
            self._index = {}

    def _image_url(self, card_id) -> Optional[str]:
        if not card_id:
            return None
        conn = self._connect()
        if conn is None:
            return None
        row = conn.execute(
            "SELECT image_url_cropped, image_url FROM card_images "
            "WHERE card_id = ? ORDER BY image_id LIMIT 1", (card_id,),
        ).fetchone()
        if not row:
            return None
        return row["image_url_cropped"] or row["image_url"]

    def resolve(self, deck_name: str) -> Optional[dict]:
        """덱명 → {slug, en_name, card_id, image_url}. 매칭 실패 시 None.

        우선순위: 사용자 별칭표(archetypes.py) → DB 이름(영/한/일) 정확 일치.
        """
        self._ensure_index()
        if not self._index:
            return None
        aid = None
        alias = archetypes.resolve_archetype(deck_name)
        if alias:
            aid = self._index.get(_norm(alias))
        if aid is None:
            aid = self._index.get(_norm(deck_name))
        if aid is None:
            return None
        a = self._arch.get(aid)
        if not a:
            return None
        return {
            "slug": a["slug"], "en_name": a["en"],
            "card_id": a["rid"], "image_url": self._image_url(a["rid"]),
        }

    def all_display_names(self) -> list[str]:
        """자동완성 후보용 아키타입 이름 목록(한국어·영어). 정렬·중복 제거."""
        conn = self._connect()
        if conn is None:
            return []
        names: set[str] = set()
        try:
            for r in conn.execute(
                "SELECT name FROM archetype_names WHERE lang IN ('ko','en')"
            ):
                if r["name"]:
                    names.add(r["name"])
        except sqlite3.Error:
            return []
        return sorted(names)

    def search_archetypes(self, term: str, limit: int = 30) -> list[dict]:
        """이름(한/영/일)에 term이 포함된 아키타입 목록(수동 지정 다이얼로그용)."""
        conn = self._connect()
        if conn is None:
            return []
        nt = _norm(term)
        if not nt:
            return []
        out: list[dict] = []
        seen: set[int] = set()
        try:
            rows = conn.execute(
                "SELECT a.id aid, a.slug, a.source_en_name en, "
                "a.representative_card_id rid, n.lang, n.name "
                "FROM archetype_names n JOIN archetypes a ON a.id = n.archetype_id "
                "ORDER BY (n.lang='ko') DESC, a.source_en_name"
            )
            for r in rows:
                if r["aid"] in seen or nt not in _norm(r["name"]):
                    continue
                seen.add(r["aid"])
                disp = (r["name"] if r["lang"] == "en"
                        else f'{r["name"]} ({r["en"]})')
                out.append({
                    "id": r["rid"], "name": disp, "slug": r["slug"],
                    "image_url": self._image_url(r["rid"]),
                })
                if len(out) >= limit:
                    break
        except sqlite3.Error:
            return out
        return out
