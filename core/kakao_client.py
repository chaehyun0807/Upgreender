"""Thin wrapper around Kakao's Local keyword-search REST API, used to turn a
building/place name (e.g. "공학관") into map coordinates."""
from __future__ import annotations

import requests

from core.config import KAKAO_KEYWORD_SEARCH_URL, KAKAO_REST_API_KEY


class KakaoError(RuntimeError):
    pass


def geocode_place(query: str) -> tuple[float, float] | None:
    """Look up a place by keyword. Returns (lat, lng) of the top match, or
    None if nothing was found. Kakao's API returns x=longitude, y=latitude."""
    if not KAKAO_REST_API_KEY:
        raise KakaoError("KAKAO_REST_API_KEY가 설정되지 않았습니다.")
    response = requests.get(
        KAKAO_KEYWORD_SEARCH_URL,
        headers={"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"},
        params={"query": query, "size": 1},
        timeout=15,
    )
    if response.status_code != 200:
        raise KakaoError(f"카카오 장소 검색 실패 ({response.status_code}): {response.text[:300]}")
    documents = response.json().get("documents", [])
    if not documents:
        return None
    doc = documents[0]
    return float(doc["y"]), float(doc["x"])


def geocode_place_fuzzy(query: str) -> tuple[float, float, str] | None:
    """Individual campus buildings (e.g. "공학5호관 606호") are often not
    registered as their own POI in Kakao's database, even though the school
    itself is. Try the full query first, then progressively drop trailing
    words (room number, building name, ...) until something matches.
    Returns (lat, lng, matched_query) so the caller can tell the result apart
    from an exact match, or None if nothing matched at all."""
    tokens = query.split()
    for end in range(len(tokens), 0, -1):
        attempt = " ".join(tokens[:end])
        coords = geocode_place(attempt)
        if coords:
            return coords[0], coords[1], attempt
    return None
