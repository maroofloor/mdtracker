"""YGOPRODeck API 클라이언트 (stdlib urllib, 키 불필요).

네트워크 호출은 함수 실행 시에만 발생하며, 실패 시 빈 리스트를 반환한다
(앱이 오프라인이어도 폴백 동작). UI 스레드를 막지 않도록 워커에서 호출 권장.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
_TIMEOUT = 8
_UA = "MDTracker (personal tracker)"


def _get(params: dict) -> list[dict]:
    url = _API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if isinstance(payload, dict):
        return payload.get("data", []) or []
    return []


def _simplify(card: dict) -> dict:
    imgs = card.get("card_images") or [{}]
    first = imgs[0] if imgs else {}
    return {
        "id": card.get("id"),
        "name": card.get("name", ""),
        "image_url": first.get("image_url", ""),
        "image_url_cropped": first.get("image_url_cropped", ""),
    }


def archetype_cards(archetype: str, limit: int = 20) -> list[dict]:
    """아키타입에 속한 카드들을 반환(대표 카드 선택용). 실패 시 []."""
    if not archetype:
        return []
    try:
        cards = _get({"archetype": archetype})
    except Exception:
        return []
    return [_simplify(c) for c in cards[:limit]]


def search_by_name(term: str, limit: int = 24) -> list[dict]:
    """카드명 부분검색(수동 지정용). 실패 시 []."""
    if not term or not term.strip():
        return []
    try:
        cards = _get({"fname": term.strip(), "num": limit, "offset": 0})
    except Exception:
        # num/offset 미지원 폴백
        try:
            cards = _get({"fname": term.strip()})
        except Exception:
            return []
    return [_simplify(c) for c in cards[:limit]]
