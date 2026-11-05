import logging

import httpx

from stores.domain.coordinates import Coordinates
from stores.domain.exceptions import AddressNotFoundError, GeocodingUnavailableError
from stores.domain.service import Geocoder
from stores.infrastructure.settings import NaverGeocodingSettings

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_SECONDS = 3.0


class NaverGeocoder(Geocoder):
    """네이버 지도 Geocoding. 엔드포인트·헤더·응답 필드는 가정이다(stores.md D27, 확인 필요)."""

    def __init__(
        self,
        settings: NaverGeocodingSettings | None,
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
            "x-ncp-apigw-api-key-id": settings.client_id,
            "x-ncp-apigw-api-key": settings.client_secret,
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                timeout=timeout, follow_redirects=False, transport=self._transport
            ) as client:
                response = await client.get(
                    settings.url, params={"query": address}, headers=headers
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
            status = data.get("status")
            if status is not None and status != "OK":
                raise ValueError("status is not OK")
            addresses = data["addresses"]
            if not isinstance(addresses, list):
                raise TypeError("addresses is not a list")
            total = (data.get("meta") or {}).get("totalCount")
            if total is not None and (isinstance(total, bool) or not isinstance(total, int)):
                raise TypeError("totalCount is not an int")
            if total == 0 or not addresses:
                not_found = True
            else:
                not_found = False
                first = addresses[0]
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
