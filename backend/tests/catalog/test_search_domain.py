import math

import pytest

from catalog.domain.search import (
    DEFAULT_RADIUS_KM,
    OfferSort,
    SearchArea,
    normalize_keyword,
    round_distance,
)


def test_area_none_when_no_location_and_radius_ignored():
    assert SearchArea.of(None, None, None) is None
    assert SearchArea.of(None, None, 999) is None


@pytest.mark.parametrize("lat,lng", [(1.0, None), (None, 1.0)])
def test_area_pair_required(lat, lng):
    with pytest.raises(ValueError, match="lat과 lng는 함께 입력해야 합니다."):
        SearchArea.of(lat, lng, None)


def test_area_default_radius_and_boundaries():
    assert SearchArea.of(0, 0, None).radius_km == DEFAULT_RADIUS_KM == 3.0
    for lat, lng, r in [(-90, -180, 0.1), (90, 180, 20)]:
        assert SearchArea.of(lat, lng, r) is not None


@pytest.mark.parametrize(
    "lat,lng,r,msg",
    [
        (90.1, 0, 1, "위도는 -90~90 범위여야 합니다."),
        (-91, 0, 1, "위도는 -90~90 범위여야 합니다."),
        (math.nan, 0, 1, "위도는 -90~90 범위여야 합니다."),
        (math.inf, 0, 1, "위도는 -90~90 범위여야 합니다."),
        (0, 180.1, 1, "경도는 -180~180 범위여야 합니다."),
        (0, -181, 1, "경도는 -180~180 범위여야 합니다."),
        (0, 0, 0.09, "검색 반경은 0.1~20km여야 합니다."),
        (0, 0, 20.1, "검색 반경은 0.1~20km여야 합니다."),
        (0, 0, math.nan, "검색 반경은 0.1~20km여야 합니다."),
    ],
)
def test_area_invalid(lat, lng, r, msg):
    with pytest.raises(ValueError, match=msg):
        SearchArea.of(lat, lng, r)


def test_sort_distance_needs_area():
    with pytest.raises(ValueError, match="distance 정렬은 위치 정보가 필요합니다."):
        OfferSort.DISTANCE.ensure_usable(None)
    OfferSort.DISTANCE.ensure_usable(SearchArea.of(0, 0, None))
    OfferSort.PRICE.ensure_usable(None)


def test_normalize_keyword():
    assert normalize_keyword(None) is None
    assert normalize_keyword("   ") is None
    assert normalize_keyword("  빵 ") == "빵"
    assert normalize_keyword("a" * 100) == "a" * 100
    with pytest.raises(ValueError, match="검색어는 100자 이하여야 합니다."):
        normalize_keyword("a" * 101)


def test_round_distance():
    assert round_distance(None) is None
    assert round_distance(1.23456) == 1.23
