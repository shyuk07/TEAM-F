import math
from dataclasses import dataclass
from enum import StrEnum

DEFAULT_RADIUS_KM = 3.0
MIN_RADIUS_KM = 0.1
MAX_RADIUS_KM = 20.0
DISTANCE_UNIT = "km"
DISTANCE_DECIMALS = 2
KEYWORD_MAX_LENGTH = 100


@dataclass(frozen=True)
class SearchArea:
    lat: float
    lng: float
    radius_km: float

    @classmethod
    def of(
        cls, lat: float | None, lng: float | None, radius_km: float | None
    ) -> "SearchArea | None":
        if lat is None and lng is None:
            return None  # 위치 없음: radius_km는 무시 (D67)
        if lat is None or lng is None:
            raise ValueError("lat과 lng는 함께 입력해야 합니다.")
        if not math.isfinite(lat) or not -90 <= lat <= 90:
            raise ValueError("위도는 -90~90 범위여야 합니다.")
        if not math.isfinite(lng) or not -180 <= lng <= 180:
            raise ValueError("경도는 -180~180 범위여야 합니다.")
        radius = DEFAULT_RADIUS_KM if radius_km is None else radius_km
        if not math.isfinite(radius) or not MIN_RADIUS_KM <= radius <= MAX_RADIUS_KM:
            raise ValueError("검색 반경은 0.1~20km여야 합니다.")
        return cls(lat=lat, lng=lng, radius_km=radius)


class OfferSort(StrEnum):
    DISTANCE = "distance"
    PRICE = "price"
    SALES_END = "sales_end"
    DISCOUNT_RATE = "discount_rate"

    def ensure_usable(self, area: SearchArea | None) -> None:
        if self == OfferSort.DISTANCE and area is None:
            raise ValueError("distance 정렬은 위치 정보가 필요합니다.")


def normalize_keyword(raw: str | None) -> str | None:
    if raw is None:
        return None
    keyword = raw.strip()
    if not keyword:
        return None
    if len(keyword) > KEYWORD_MAX_LENGTH:
        raise ValueError("검색어는 100자 이하여야 합니다.")
    return keyword


def round_distance(km: float | None) -> float | None:
    return None if km is None else round(km, DISTANCE_DECIMALS)
