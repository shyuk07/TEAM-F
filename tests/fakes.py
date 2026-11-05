"""테스트 공용 fake (네트워크 금지, R16)."""

from stores.domain.coordinates import Coordinates
from stores.domain.service import Geocoder

DEFAULT_COORDINATES = Coordinates(37.4979, 127.0276)


class FakeGeocoder(Geocoder):
    """호출 인자를 기록한다. results[주소]가 Exception이면 raise, Coordinates면 반환, 없으면 기본 좌표."""

    def __init__(self, default: Coordinates = DEFAULT_COORDINATES, results=None, events=None):
        self.default = default
        self.results: dict[str, Coordinates | Exception] = dict(results or {})
        self.events = events if events is not None else []
        self.calls: list[str] = []

    async def geocode(self, address: str) -> Coordinates:
        self.calls.append(address)
        self.events.append("geocode")
        result = self.results.get(address, self.default)
        if isinstance(result, Exception):
            raise result
        return result
