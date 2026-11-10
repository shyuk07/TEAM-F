from stores.domain.coordinates import Coordinates
from stores.infrastructure.geocoder import KakaoGeocoder

DEFAULT_COORDINATES = Coordinates(37.4979, 127.0276)


class MockGeocoder(KakaoGeocoder):
    """로컬 개발용 모의 지오코더.

    카카오 API 키가 설정되지 않은 로컬 환경에서 기본 좌표(강남역 부근)를 반환한다.
    KakaoGeocoder를 상속하여 기존 wiring 테스트 및 타입 검사를 100% 만족한다.
    """

    def __init__(self, default: Coordinates = DEFAULT_COORDINATES) -> None:
        super().__init__(settings=None)
        self._default = default

    async def geocode(self, address: str) -> Coordinates:
        return self._default
