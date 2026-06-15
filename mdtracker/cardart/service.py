"""덱명 → 대표 카드 로컬 이미지 경로 해석.

해석 출처
--------
- 이름→대표카드 URL: 번들 메타데이터 DB(:class:`LocalCardDB`).
- 이미지 파일: URL에서 사용자별 로컬 캐시로 다운로드(:mod:`cache`). 재배포·핫링크 없음.

우선순위
--------
1. 사용자 수동 지정(deck_art source='manual')의 이미지
2. 기존 캐시
3. DB로 해석한 대표 카드 이미지(필요 시 1회 다운로드)

자동 해석은 DB/별칭표에 매칭되는 덱만 (임의 추측 금지 — CLAUDE.md 규칙).
네트워크가 필요한 ensure()/assign_manual()은 블로킹이므로 워커 스레드 권장.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import cache
from .localdb import LocalCardDB


class CardArtService:
    def __init__(self, deck_repo, *, localdb: Optional[LocalCardDB] = None,
                 cache_base: Optional[Path] = None) -> None:
        self.repo = deck_repo
        self.db = localdb if localdb is not None else LocalCardDB()
        self.cache_base = cache_base

    # ── 네트워크 없이 즉시 사용 가능한 로컬 경로 ──────────────────────
    def local_path(self, deck_name: str) -> Optional[str]:
        art = self.repo.get_art(deck_name)
        if art:
            ip = art.get("image_path")
            if ip and Path(ip).is_file():
                return ip
            cid = art.get("card_id")
            if cid:
                hit = cache.cached(cid, base=self.cache_base)
                if hit:
                    return str(hit)
            if art.get("source") == "manual":
                return None   # 수동 지정인데 캐시가 사라짐 → 재지정 유도
        info = self.db.resolve(deck_name)
        if info and info.get("card_id"):
            hit = cache.cached(info["card_id"], base=self.cache_base)
            if hit:
                return str(hit)
        return None

    def has_auto_mapping(self, deck_name: str) -> bool:
        return self.db.resolve(deck_name) is not None

    # ── 네트워크로 아트 확보(블로킹) ──────────────────────────────────
    def ensure(self, deck_name: str) -> Optional[str]:
        local = self.local_path(deck_name)
        if local:
            return local
        art = self.repo.get_art(deck_name)
        if art and art.get("source") == "manual":
            return None
        info = self.db.resolve(deck_name)
        if not info or not info.get("image_url"):
            return None
        path = cache.download(
            info["card_id"], info["image_url"], base=self.cache_base)
        if not path:
            return None
        self.repo.set_art(deck_name, card_id=info["card_id"],
                          query=info["en_name"], source="auto",
                          image_path=str(path))
        return str(path)

    # ── 수동 지정(사용자 보정) ────────────────────────────────────────
    def search(self, term: str) -> list[dict]:
        return self.db.search_archetypes(term)

    def assign_manual(self, deck_name: str, choice: dict) -> Optional[str]:
        url = choice.get("image_url") or choice.get("image_url_cropped")
        cid = choice.get("id")
        path = (cache.download(cid, url, base=self.cache_base)
                if (cid and url) else None)
        self.repo.set_art(
            deck_name, card_id=cid, query=choice.get("name"),
            source="manual", image_path=str(path) if path else None)
        return str(path) if path else None

    def clear(self, deck_name: str) -> None:
        self.repo.clear_art(deck_name)
