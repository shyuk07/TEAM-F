import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Coordinates:
    latitude: float
    longitude: float

    def __post_init__(self):
        lat, lng = self.latitude, self.longitude
        if (
            isinstance(lat, bool)
            or isinstance(lng, bool)
            or not isinstance(lat, (int, float))
            or not isinstance(lng, (int, float))
            or not (math.isfinite(lat) and math.isfinite(lng))
            or not (-90 <= lat <= 90 and -180 <= lng <= 180)
        ):
            raise ValueError("좌표가 올바르지 않습니다.")
