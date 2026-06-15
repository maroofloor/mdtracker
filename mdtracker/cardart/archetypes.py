"""한글 덱명 ↔ YGOPRODeck 영문 아키타입 시드 매핑표.

자동 매핑은 이 표에 있는 덱에만 적용된다. 표에 없으면 사용자가 수동으로
대표 카드를 지정하거나(deck_art source='manual'), 색 그라디언트+이니셜 폴백을 쓴다.
표는 점진적으로 보강할 수 있다.
"""

from __future__ import annotations

# 한글 덱명(또는 흔한 표기) → YGOPRODeck `archetype` 파라미터 영문명
ARCHETYPE_KR_TO_EN: dict[str, str] = {
    "스네이크아이": "Snake-Eye",
    "스네이크아이즈": "Snake-Eye",
    "티아라멘츠": "Tearlaments",
    "엘드리치": "Eldlich",
    "크샤트리라": "Kashtira",
    "비스테드": "Bystial",
    "라뷰린스": "Labrynth",
    "퓨어리": "Purrely",
    "푸어리": "Purrely",
    "센츄리온": "Centur-Ion",
    "룬": "Runick",
    "루닉": "Runick",
    "마나둠": "Mannadium",
    "유벨": "Yubel",
    "드라이트론": "Drytron",
    "엑소시스터": "Exosister",
    "블루아이즈": "Blue-Eyes",
    "푸른눈": "Blue-Eyes",
    "레드아이즈": "Red-Eyes",
    "붉은눈": "Red-Eyes",
    "십이수": "Zoodiac",
    "라이트로드": "Lightsworn",
    "섬도희": "Sky Striker",
    "코드토커": "Code Talker",
    "마돌체": "Madolche",
    "아다마시아": "Adamancipator",
    "드래그마": "Dogmatika",
    "누메론": "Numeron",
    "천위": "Tenyi",
    "마요괴": "Mayakashi",
    "데먼스미스": "Fiendsmith",
    "데몬스미스": "Fiendsmith",
    "디노몰피아": "Dinomorphia",
    "메멘토": "Memento",
    "보옥수": "Crystal Beast",
    "인페르노이드": "Infernoid",
    "트라이브리게이드": "Tri-Brigade",
    "엘리멘틀히어로": "Elemental HERO",
    "엘히": "Elemental HERO",
    "히어로": "HERO",
    "마술사": "Performapal",
    "낙인": "Despia",
    "데스피아": "Despia",
    "프랭키즈": "Frightfur",
    "프랑키즈": "Frightfur",
    "운영": "Runick",
    "백염": "Ice Barrier",
    "용병": "Mercenary",
    "야미": "Yummy",
    "여행": "Adventurer",
}


def _normalize(name: str) -> str:
    """매칭용 정규화 — 공백·하이픈·점 제거, 소문자."""
    if not name:
        return ""
    out = []
    for ch in name.strip().lower():
        if ch.isspace() or ch in "-_.·•":
            continue
        out.append(ch)
    return "".join(out)


_NORMALIZED = {_normalize(k): v for k, v in ARCHETYPE_KR_TO_EN.items()}


def resolve_archetype(deck_name: str) -> str | None:
    """덱명을 영문 아키타입으로 해석. 표에 없으면 None."""
    return _NORMALIZED.get(_normalize(deck_name))
