from abc import ABC, abstractmethod
from datetime import datetime

from stores.domain.coordinates import Coordinates


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        """항상 timezone이 있는 현재 시각(UTC)"""


class Geocoder(ABC):
    @abstractmethod
    async def geocode(self, address: str) -> Coordinates:
        """정규화된 주소를 좌표로 바꾼다.
        결과 없음 -> AddressNotFoundError. 그 외 모든 실패(네트워크, 타임아웃, 업스트림 오류,
        응답 형식 오류, 자격증명 없음) -> GeocodingUnavailableError."""
