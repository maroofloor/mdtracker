"""카드 이미지 로컬 캐시 — 다운로드·저장. Qt 비의존(파일 IO만).

개인용 캐시에만 저장하며 앱 배포물에 번들하지 않는다. card_id로 키잉한다.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Optional

_TIMEOUT = 12
_UA = "MDTracker (personal tracker)"


def _base_dir(base: Optional[Path]) -> Path:
    if base is not None:
        return Path(base)
    # 지연 import — app_paths만 의존, 단위 테스트는 base 인자로 우회 가능
    from ..app_paths import card_art_cache_dir
    return card_art_cache_dir()


def cache_path_for(card_id, *, base: Optional[Path] = None) -> Path:
    return _base_dir(base) / f"{int(card_id)}.jpg"


def cached(card_id, *, base: Optional[Path] = None) -> Optional[Path]:
    """이미 캐시된 이미지 경로(유효 파일)이면 반환, 아니면 None."""
    try:
        p = cache_path_for(card_id, base=base)
    except (TypeError, ValueError):
        return None
    return p if p.is_file() and p.stat().st_size > 0 else None


def download(card_id, url: str, *, base: Optional[Path] = None) -> Optional[Path]:
    """url 이미지를 받아 캐시에 저장하고 경로 반환. 실패 시 None.

    이미 캐시가 있으면 재다운로드하지 않는다.
    """
    if not url:
        return None
    existing = cached(card_id, base=base)
    if existing:
        return existing
    try:
        p = cache_path_for(card_id, base=base)
        p.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = resp.read()
        if not data:
            return None
        tmp = p.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(p)
        return p
    except Exception:
        return None
