import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 확인 필요(stores.md D27): 현행 도메인이 다르면 NAVER_MAP_GEOCODE_URL로 교체한다.
DEFAULT_GEOCODE_URL = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
DEFAULT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class NaverGeocodingSettings:
    client_id: str
    client_secret: str
    url: str = DEFAULT_GEOCODE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def __repr__(self) -> str:  # 비밀이 로그·트레이스백에 새지 않게 (R16)
        return f"NaverGeocodingSettings(url={self.url!r}, timeout_seconds={self.timeout_seconds!r})"


def _timeout(raw: str | None) -> float:
    if raw is None or not raw.strip():
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        value = 0.0
    if not value > 0 or value == float("inf"):
        logger.warning("NAVER_MAP_TIMEOUT_SECONDS 값이 올바르지 않아 기본값을 사용합니다.")
        return DEFAULT_TIMEOUT_SECONDS
    return value


def get_naver_geocoding_settings(
    env: Mapping[str, str] | None = None,
) -> NaverGeocodingSettings | None:
    """NAVER_MAP_* 를 읽는다. 키가 하나라도 없으면 None(예외 없음, D28). 값은 로그에 넣지 않는다."""
    if env is None:
        load_dotenv()
        env = os.environ
    client_id = (env.get("NAVER_MAP_CLIENT_ID") or "").strip()
    client_secret = (env.get("NAVER_MAP_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        logger.warning(
            "NAVER_MAP_CLIENT_ID/NAVER_MAP_CLIENT_SECRET이 없어 상점 개설(POST /v1/stores)은 "
            "503 GEOCODING_UNAVAILABLE로 거절됩니다."
        )
        return None
    url = (env.get("NAVER_MAP_GEOCODE_URL") or "").strip() or DEFAULT_GEOCODE_URL
    return NaverGeocodingSettings(
        client_id=client_id,
        client_secret=client_secret,
        url=url,
        timeout_seconds=_timeout(env.get("NAVER_MAP_TIMEOUT_SECONDS")),
    )
