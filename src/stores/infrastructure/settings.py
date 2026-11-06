import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# stores.md D42: 다르면 KAKAO_GEOCODE_URL로 교체한다.
DEFAULT_GEOCODE_URL = "https://dapi.kakao.com/v2/local/search/address.json"
DEFAULT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class KakaoGeocodingSettings:
    rest_api_key: str = field(repr=False)
    url: str = DEFAULT_GEOCODE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def __repr__(self) -> str:  # 비밀이 로그·트레이스백에 새지 않게 (R16)
        return f"KakaoGeocodingSettings(url={self.url!r}, timeout_seconds={self.timeout_seconds!r})"


def _timeout(raw: str | None) -> float:
    if raw is None or not raw.strip():
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        value = 0.0
    if not value > 0 or value == float("inf"):
        logger.warning("KAKAO_TIMEOUT_SECONDS 값이 올바르지 않아 기본값을 사용합니다.")
        return DEFAULT_TIMEOUT_SECONDS
    return value


def get_kakao_geocoding_settings(
    env: Mapping[str, str] | None = None,
) -> KakaoGeocodingSettings | None:
    """KAKAO_* 를 읽는다. 키가 없으면 None(예외 없음, D28·D43). 값은 로그에 넣지 않는다."""
    if env is None:
        load_dotenv()
        env = os.environ
    rest_api_key = (env.get("KAKAO_REST_API_KEY") or "").strip()
    if not rest_api_key:
        logger.warning(
            "KAKAO_REST_API_KEY이 없어 상점 개설(POST /v1/stores)은 "
            "503 GEOCODING_UNAVAILABLE로 거절됩니다."
        )
        return None
    url = (env.get("KAKAO_GEOCODE_URL") or "").strip() or DEFAULT_GEOCODE_URL
    return KakaoGeocodingSettings(
        rest_api_key=rest_api_key,
        url=url,
        timeout_seconds=_timeout(env.get("KAKAO_TIMEOUT_SECONDS")),
    )
