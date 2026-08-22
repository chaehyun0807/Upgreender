import pytest

from core.kakao_client import KakaoError, geocode_place, geocode_place_fuzzy


def test_geocode_place_raises_without_rest_key(monkeypatch):
    monkeypatch.setattr("core.kakao_client.KAKAO_REST_API_KEY", "")
    with pytest.raises(KakaoError):
        geocode_place("공학관")


def test_geocode_place_returns_lat_lng_from_first_document(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "documents": [
                    {"place_name": "공학관", "x": "129.3435", "y": "36.0138"},
                    {"place_name": "다른 공학관", "x": "127.0", "y": "37.5"},
                ]
            }

    monkeypatch.setattr("core.kakao_client.KAKAO_REST_API_KEY", "fake-key")
    monkeypatch.setattr("core.kakao_client.requests.get", lambda *a, **k: FakeResponse())

    lat, lng = geocode_place("공학관")
    assert lat == pytest.approx(36.0138)
    assert lng == pytest.approx(129.3435)


def test_geocode_place_returns_none_when_no_documents(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"documents": []}

    monkeypatch.setattr("core.kakao_client.KAKAO_REST_API_KEY", "fake-key")
    monkeypatch.setattr("core.kakao_client.requests.get", lambda *a, **k: FakeResponse())

    assert geocode_place("존재하지않는장소") is None


def test_geocode_place_raises_on_non_200(monkeypatch):
    class FakeResponse:
        status_code = 401
        text = "unauthorized"

    monkeypatch.setattr("core.kakao_client.KAKAO_REST_API_KEY", "bad-key")
    monkeypatch.setattr("core.kakao_client.requests.get", lambda *a, **k: FakeResponse())

    with pytest.raises(KakaoError):
        geocode_place("공학관")


def test_geocode_place_fuzzy_falls_back_to_shorter_query(monkeypatch):
    # "동아대 공학5호관 606" 자체는 없지만 "동아대"는 찾을 수 있는 상황을 흉내낸다.
    known = {"동아대": (35.1, 128.9)}

    def fake_geocode_place(query):
        return known.get(query)

    monkeypatch.setattr("core.kakao_client.geocode_place", fake_geocode_place)

    result = geocode_place_fuzzy("동아대 공학5호관 606")
    assert result == (35.1, 128.9, "동아대")


def test_geocode_place_fuzzy_returns_exact_match_first(monkeypatch):
    known = {"동아대 공학5호관 606": (35.2, 129.0), "동아대": (35.1, 128.9)}
    monkeypatch.setattr("core.kakao_client.geocode_place", lambda query: known.get(query))

    result = geocode_place_fuzzy("동아대 공학5호관 606")
    assert result == (35.2, 129.0, "동아대 공학5호관 606")


def test_geocode_place_fuzzy_returns_none_when_nothing_matches(monkeypatch):
    monkeypatch.setattr("core.kakao_client.geocode_place", lambda query: None)
    assert geocode_place_fuzzy("존재하지 않는 어딘가") is None
