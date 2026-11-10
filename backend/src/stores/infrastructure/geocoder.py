import logging

import httpx

from stores.domain.coordinates import Coordinates
from stores.domain.exceptions import AddressNotFoundError, GeocodingUnavailableError
from stores.domain.service import Geocoder
from stores.infrastructure.settings import KakaoGeocodingSettings

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_SECONDS = 3.0


class KakaoGeocoder(Geocoder):
    """카카오 로컬 API 주소 검색. 엔드포인트·헤더·응답 필드는 stores.md D49 기준."""

    def __init__(
        self,
        settings: KakaoGeocodingSettings | None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._settings = settings
        self._transport = transport  # 테스트용 이음새(httpx.MockTransport)

    async def geocode(self, address: str) -> Coordinates:
        settings = self._settings
        if settings is None:
            logger.warning("geocoding unavailable: reason=no_credentials")
            raise GeocodingUnavailableError()
        timeout = httpx.Timeout(settings.timeout_seconds, connect=CONNECT_TIMEOUT_SECONDS)
        headers = {
            "Authorization": f"KakaoAK {settings.rest_api_key}",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                timeout=timeout, follow_redirects=False, transport=self._transport
            ) as client:
                response = await client.get(
                    settings.url, params={"query": address, "size": 1}, headers=headers
                )
        except (httpx.HTTPError, httpx.InvalidURL, httpx.StreamError) as err:
            logger.warning("geocoding unavailable: reason=%s", type(err).__name__)
            raise GeocodingUnavailableError() from err
        if response.status_code != 200:
            logger.warning("geocoding unavailable: reason=http_%s", response.status_code)
            raise GeocodingUnavailableError()
        return self._parse(response)

    @staticmethod
    def _parse(response: httpx.Response) -> Coordinates:
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise TypeError("body is not an object")
            documents = data["documents"]
            if not isinstance(documents, list):
                raise TypeError("documents is not a list")
            total = (data.get("meta") or {}).get("total_count")
            if total is not None and (isinstance(total, bool) or not isinstance(total, int)):
                raise TypeError("total_count is not an int")
            if total == 0 or not documents:
                not_found = True
            else:
                not_found = False
                first = documents[0]
                # x = 경도, y = 위도 (둘 다 문자열)
                coordinates = Coordinates(
                    latitude=float(first["y"]), longitude=float(first["x"])
                )
        except (ValueError, TypeError, KeyError, AttributeError) as err:
            logger.warning("geocoding unavailable: reason=malformed_response")
            raise GeocodingUnavailableError() from err
        if not_found:
            raise AddressNotFoundError()
        return coordinates
