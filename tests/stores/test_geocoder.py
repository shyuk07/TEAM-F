"""NaverGeocoder·설정 단위 테스트 (stores.md 14.8). httpx.MockTransport만 쓴다: 네트워크 금지(R16)."""

import logging

import httpx
import pytest

from stores.domain.coordinates import Coordinates
from stores.domain.exceptions import AddressNotFoundError, GeocodingUnavailableError
from stores.infrastructure.geocoder import NaverGeocoder
from stores.infrastructure.settings import (
    DEFAULT_GEOCODE_URL,
    NaverGeocodingSettings,
    get_naver_geocoding_settings,
)

pytestmark = pytest.mark.anyio

SECRET = "super-secret-value-xyz"
SETTINGS = NaverGeocodingSettings(
    client_id="the-key-id", client_secret=SECRET, url="https://geo.example.test/geocode"
)
OK_BODY = {
    "status": "OK",
    "meta": {"totalCount": 1, "page": 1, "count": 1},
    "addresses": [{"roadAddress": "r", "x": "127.0276", "y": "37.4979"}],
    "errorMessage": "",
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


class Recorder:
    def __init__(self, handler):
        self.handler = handler
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        result = self.handler(request)
        if isinstance(result, Exception):
            raise result
        return result


def geocoder_for(handler, settings=SETTINGS):
    rec = Recorder(handler)
    return NaverGeocoder(settings, transport=httpx.MockTransport(rec)), rec


def json_response(body, status=200):
    return lambda request: httpx.Response(status, json=body)


async def test_success_parses_x_as_longitude_and_y_as_latitude():
    g, rec = geocoder_for(json_response(OK_BODY))
    result = await g.geocode("서울 강남구")
    assert result == Coordinates(latitude=37.4979, longitude=127.0276)
    assert result.latitude == 37.4979 and result.longitude == 127.0276  # x/y 바뀜 방지
    assert len(rec.requests) == 1


async def test_request_shape():
    g, rec = geocoder_for(json_response(OK_BODY))
    address = "서울 강남구 테헤란로 123 & 4층 #5"
    await g.geocode(address)
    req = rec.requests[0]
    assert req.method == "GET"
    assert str(req.url).startswith("https://geo.example.test/geocode?")
    assert req.url.params["query"] == address  # 한글·공백·&·# 이 쿼리 값으로 온전히 인코딩
    assert list(req.url.params.keys()) == ["query"]
    assert req.headers["x-ncp-apigw-api-key-id"] == "the-key-id"
    assert req.headers["x-ncp-apigw-api-key"] == SECRET
    assert req.headers["accept"] == "application/json"


async def test_multiple_results_use_first():
    body = dict(OK_BODY, addresses=[{"x": "127.0", "y": "37.0"}, {"x": "128.0", "y": "38.0"}])
    body["meta"] = {"totalCount": 2}
    g, _ = geocoder_for(json_response(body))
    assert await g.geocode("a") == Coordinates(37.0, 127.0)


@pytest.mark.parametrize(
    "body",
    [
        {"status": "OK", "meta": {"totalCount": 0}, "addresses": []},
        {"status": "OK", "addresses": []},
        {"status": "OK", "meta": {"totalCount": 0}, "addresses": [{"x": "1", "y": "2"}]},
    ],
)
async def test_zero_results_is_address_not_found(body):
    g, _ = geocoder_for(json_response(body))
    with pytest.raises(AddressNotFoundError):
        await g.geocode("없는 주소")


@pytest.mark.parametrize("status", [400, 401, 403, 429, 500, 503])
async def test_upstream_http_errors_are_unavailable_not_not_found(status):
    g, _ = geocoder_for(json_response({"errorMessage": "x"}, status))
    with pytest.raises(GeocodingUnavailableError) as e:
        await g.geocode("a")
    assert not isinstance(e.value, AddressNotFoundError)
    assert not isinstance(e.value, ValueError)


async def test_redirect_is_not_followed():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://evil.example.test/"})

    g, _ = geocoder_for(handler)
    with pytest.raises(GeocodingUnavailableError):
        await g.geocode("a")
    assert calls == ["https://geo.example.test/geocode?query=a"]


@pytest.mark.parametrize(
    "error",
    [
        httpx.ReadTimeout("slow"),
        httpx.ConnectTimeout("slow"),
        httpx.ConnectError("refused"),
        httpx.RemoteProtocolError("bad"),
    ],
)
async def test_network_errors_are_unavailable(error):
    g, _ = geocoder_for(lambda request: error)
    with pytest.raises(GeocodingUnavailableError):
        await g.geocode("a")


def _with_address(**item):
    return {"status": "OK", "meta": {"totalCount": 1}, "addresses": [item]}


@pytest.mark.parametrize(
    "response",
    [
        lambda r: httpx.Response(200, content=b"<html>not json</html>"),
        lambda r: httpx.Response(200, content=b""),
        lambda r: httpx.Response(200, json=["list"]),
        lambda r: httpx.Response(200, json={"status": "INVALID_REQUEST", "addresses": []}),
        lambda r: httpx.Response(200, json={"status": "OK"}),
        lambda r: httpx.Response(200, json={"status": "OK", "addresses": "nope"}),
        lambda r: httpx.Response(200, json={"status": "OK", "meta": {"totalCount": "1"}, "addresses": []}),
        lambda r: httpx.Response(200, json=_with_address(y="37.0")),  # x 없음
        lambda r: httpx.Response(200, json=_with_address(x="127.0")),  # y 없음
        lambda r: httpx.Response(200, json=_with_address(x="abc", y="37.0")),
        lambda r: httpx.Response(200, json=_with_address(x=None, y="37.0")),
        lambda r: httpx.Response(200, json=_with_address(x="nan", y="37.0")),
        lambda r: httpx.Response(200, json=_with_address(x="127.0", y="91")),
        lambda r: httpx.Response(200, json=_with_address(x="181", y="37.0")),
        lambda r: httpx.Response(200, json={"status": "OK", "addresses": ["str"]}),
    ],
)
async def test_malformed_responses_are_unavailable_not_validation_error(response):
    g, _ = geocoder_for(response)
    with pytest.raises(GeocodingUnavailableError) as e:
        await g.geocode("a")
    assert not isinstance(e.value, ValueError)  # 400 VALIDATION_ERROR로 새면 안 된다


async def test_no_settings_makes_no_http_call():
    g, rec = geocoder_for(json_response(OK_BODY), settings=None)
    with pytest.raises(GeocodingUnavailableError):
        await g.geocode("a")
    assert rec.requests == []


async def test_failures_do_not_leak_secret(caplog):
    caplog.set_level(logging.DEBUG)
    cases = [
        json_response({"errorMessage": SECRET}, 401),
        json_response({"errorMessage": SECRET}, 500),
        lambda r: httpx.ConnectError(f"cannot connect with {SECRET}"),
        lambda r: httpx.Response(200, content=SECRET.encode()),
        json_response(_with_address(x=SECRET, y="1")),
    ]
    for handler in cases:
        g, _ = geocoder_for(handler)
        with pytest.raises(GeocodingUnavailableError) as e:
            await g.geocode("a-secret-free-address")
        assert SECRET not in str(e.value)
    assert SECRET not in caplog.text and "the-key-id" not in caplog.text
    # 우리 코드는 주소 본문도 기록하지 않는다. (httpx 자체 INFO 로그는 요청 URL=주소를 남긴다: 보고서 참고)
    ours = " | ".join(r.getMessage() for r in caplog.records if r.name.startswith("stores."))
    assert ours and "a-secret-free-address" not in ours
    assert SECRET not in repr(SETTINGS)


# ── 설정 ──
def test_settings_complete():
    s = get_naver_geocoding_settings(
        {"NAVER_MAP_CLIENT_ID": "id", "NAVER_MAP_CLIENT_SECRET": "sec"}
    )
    assert s == NaverGeocodingSettings("id", "sec", DEFAULT_GEOCODE_URL, 5.0)


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"NAVER_MAP_CLIENT_ID": "id"},
        {"NAVER_MAP_CLIENT_SECRET": "sec"},
        {"NAVER_MAP_CLIENT_ID": "id", "NAVER_MAP_CLIENT_SECRET": "  "},
        {"NAVER_MAP_CLIENT_ID": "", "NAVER_MAP_CLIENT_SECRET": ""},
    ],
)
def test_settings_missing_keys_returns_none_without_raising(env):
    assert get_naver_geocoding_settings(env) is None


def test_settings_missing_keys_logs_warning_without_values(caplog):
    with caplog.at_level(logging.WARNING):
        get_naver_geocoding_settings({"NAVER_MAP_CLIENT_ID": "only-id-value"})
    assert "NAVER_MAP_CLIENT_SECRET" in caplog.text
    assert "only-id-value" not in caplog.text


@pytest.mark.parametrize("raw", ["abc", "0", "-3", "inf", "nan", ""])
def test_settings_invalid_timeout_uses_default(raw):
    s = get_naver_geocoding_settings(
        {"NAVER_MAP_CLIENT_ID": "id", "NAVER_MAP_CLIENT_SECRET": "sec", "NAVER_MAP_TIMEOUT_SECONDS": raw}
    )
    assert s.timeout_seconds == 5.0


def test_settings_custom_timeout_and_url():
    s = get_naver_geocoding_settings(
        {
            "NAVER_MAP_CLIENT_ID": "id",
            "NAVER_MAP_CLIENT_SECRET": "sec",
            "NAVER_MAP_TIMEOUT_SECONDS": "2.5",
            "NAVER_MAP_GEOCODE_URL": "https://other.example.test/g",
        }
    )
    assert s.timeout_seconds == 2.5 and s.url == "https://other.example.test/g"
