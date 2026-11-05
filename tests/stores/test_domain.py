import uuid
from datetime import datetime, timedelta, timezone

import pytest

from stores.domain.exceptions import NotStoreOwnerError, StoreAlreadyClosedError
from stores.domain.store import Store
from tests.fakes import DEFAULT_COORDINATES as COORDS

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
OWNER = uuid.uuid4()


def make(**kw):
    args = dict(owner_id=OWNER, name="상호", pickup_address="서울시 강남구")
    args.update(kw)
    return Store(**args)


def test_create_trims_and_defaults():
    s = make(name="  상호  ", pickup_address="  주소 ")
    assert s.name == "상호" and s.pickup_address == "주소"
    assert s.id is None and not s.is_approved and not s.is_closed


@pytest.mark.parametrize("name", ["", "   ", "a" * 151])
def test_invalid_name(name):
    with pytest.raises(ValueError, match="상점명은 1자 이상 150자 이하여야 합니다."):
        make(name=name)


def test_name_150_ok():
    assert make(name="a" * 150)


def test_empty_address():
    with pytest.raises(ValueError, match="주소를 입력해 주세요."):
        make(pickup_address="  ")


def test_address_too_long():
    with pytest.raises(ValueError, match="픽업 주소는 500자 이하여야 합니다."):
        make(pickup_address="a" * 501)
    assert make(pickup_address="a" * 500)


@pytest.mark.parametrize(
    "lat,lng", [(1.0, None), (None, 1.0), (91, 0), (-91, 0), (0, 181), (0, -181)]
)
def test_invalid_coordinates(lat, lng):
    with pytest.raises(ValueError, match="좌표가 올바르지 않습니다."):
        make(latitude=lat, longitude=lng)


def test_valid_coordinates():
    s = make(latitude=37.5, longitude=127.0)
    assert (s.latitude, s.longitude) == (37.5, 127.0)
    assert make(latitude=90, longitude=-180)


@pytest.mark.parametrize("field", ["created_at", "approval_at"])
def test_naive_datetime_rejected(field):
    with pytest.raises(ValueError):
        make(**{field: datetime(2026, 1, 1)})


def test_closed_requires_approval():
    with pytest.raises(ValueError, match="폐점 시각은 승인 시각 이후여야 합니다."):
        make(closed_at=NOW)
    with pytest.raises(ValueError, match="폐점 시각은 승인 시각 이후여야 합니다."):
        make(approval_at=NOW, closed_at=NOW - timedelta(seconds=1))
    assert make(approval_at=NOW, closed_at=NOW).is_closed


def test_open():
    s = Store.open(OWNER, "상호", "주소", NOW, COORDS)
    assert s.approval_at == NOW and s.is_approved and s.closed_at is None


def test_open_naive_now_rejected():
    with pytest.raises(ValueError):
        Store.open(OWNER, "상호", "주소", datetime(2026, 1, 1), COORDS)


def test_open_validates():
    with pytest.raises(ValueError):
        Store.open(OWNER, "", "주소", NOW, COORDS)


def test_ownership():
    s = make()
    assert s.is_owned_by(OWNER) and not s.is_owned_by(uuid.uuid4())
    s.ensure_owned_by(OWNER)
    with pytest.raises(NotStoreOwnerError, match="본인 상점만 폐점할 수 있습니다."):
        s.ensure_owned_by(uuid.uuid4(), "본인 상점만 폐점할 수 있습니다.")
    with pytest.raises(NotStoreOwnerError, match="본인 상점만 접근할 수 있습니다."):
        s.ensure_owned_by(uuid.uuid4())


def test_approve():
    s = make()
    s.approve(NOW)
    assert s.approval_at == NOW
    with pytest.raises(ValueError, match="이미 승인된 상점입니다."):
        s.approve(NOW)
    with pytest.raises(ValueError):
        make().approve(datetime(2026, 1, 1))


def test_close():
    s = Store.open(OWNER, "상호", "주소", NOW, COORDS)
    later = NOW + timedelta(days=1)
    s.close(later)
    assert s.closed_at == later and s.is_closed
    with pytest.raises(StoreAlreadyClosedError, match="이미 폐점된 상점입니다."):
        s.close(later)


def test_close_unapproved():
    with pytest.raises(ValueError, match="승인되지 않은 상점은 폐점할 수 없습니다."):
        make().close(NOW)


def test_close_before_approval_and_naive():
    s = Store.open(OWNER, "상호", "주소", NOW, COORDS)
    with pytest.raises(ValueError):
        s.close(NOW - timedelta(seconds=1))
    with pytest.raises(ValueError):
        s.close(datetime(2026, 1, 1))
    assert not s.is_closed


def test_store_info_attributes():
    s = make()
    for attr in ("id", "owner_id", "name", "pickup_address", "approval_at", "closed_at"):
        assert hasattr(s, attr)


# ── close 플래그 ──
from stores.domain.exceptions import (  # noqa: E402
    StoreHasOpenOffersError,
    StoreHasReservedReservationsError,
    StoreSuspendedError,
)


def _open():
    return Store.open(OWNER, "상호", "주소", NOW, COORDS)


def test_close_default_flags_ok():
    s = _open()
    later = NOW + timedelta(days=1)
    s.close(later)
    assert s.closed_at == later and s.closed_reason is None and s.status == "CLOSED"


def test_close_open_offers():
    s = _open()
    with pytest.raises(StoreHasOpenOffersError) as e:
        s.close(NOW, has_open_offers=True)
    assert e.value.error_code == "STORE_HAS_OPEN_OFFERS"
    assert str(e.value) == "진행 중이거나 예정된 할인 판매가 있어 폐점할 수 없습니다."
    assert s.closed_at is None


def test_close_pickup_pending():
    s = _open()
    with pytest.raises(StoreHasReservedReservationsError) as e:
        s.close(NOW, has_pickup_pending=True)
    assert e.value.error_code == "STORE_HAS_RESERVED_RESERVATIONS"
    assert str(e.value) == "픽업 대기 중인 예약이 있어 폐점할 수 없습니다."
    assert s.closed_at is None


def test_close_both_flags_offers_first():
    s = _open()
    with pytest.raises(StoreHasOpenOffersError):
        s.close(NOW, has_open_offers=True, has_pickup_pending=True)


def test_close_suspended_ignores_flags():
    s = _open()
    s.suspend("사유", NOW)
    with pytest.raises(StoreSuspendedError):
        s.close(NOW, has_open_offers=True, has_pickup_pending=True)
    assert s.closed_at is None


def test_close_already_closed_ignores_flags_and_suspension():
    s = _open()
    s.close(NOW)
    with pytest.raises(StoreAlreadyClosedError):
        s.close(NOW, has_open_offers=True, has_pickup_pending=True)
    s2 = Store(
        owner_id=OWNER, name="a", pickup_address="b", approval_at=NOW,
        closed_at=NOW, suspended_reason="x", suspended_at=NOW,
    )
    with pytest.raises(StoreAlreadyClosedError):
        s2.close(NOW)


def test_close_unapproved_with_flags_false_still_value_error():
    with pytest.raises(ValueError, match="승인되지 않은 상점은 폐점할 수 없습니다."):
        make().close(NOW)


# ── 개설 완성 (stores.md 14.1) ──
import unicodedata  # noqa: E402

from stores.domain.coordinates import Coordinates  # noqa: E402
from stores.domain.exceptions import (  # noqa: E402
    AddressNotFoundError,
    GeocodingUnavailableError,
    StoreAlreadyExistsError,
    StoreDuplicatedError,
)


def test_open_fills_coordinates_from_value_object():
    s = Store.open(OWNER, "상호", "주소", NOW, Coordinates(37.5, 127.1))
    assert (s.latitude, s.longitude) == (37.5, 127.1) and s.approval_at == NOW


def test_open_requires_coordinates():
    with pytest.raises(TypeError):
        Store.open(OWNER, "상호", "주소", NOW)


def test_normalize_text_nfc_and_whitespace():
    nfd = unicodedata.normalize("NFD", "서울")
    assert nfd != "서울"
    s = make(name=f"  {nfd}\u3000  카페 ", pickup_address=f"\t{nfd}   강남구\u3000 1 ")
    assert s.name == "서울 카페" and s.pickup_address == "서울 강남구 1"
    assert unicodedata.is_normalized("NFC", s.name)


def test_normalize_address():
    assert Store.normalize_address("  서울   강남 ") == "서울 강남"
    for bad in (None, "", "  \u3000 "):
        with pytest.raises(ValueError, match="주소를 입력해 주세요."):
            Store.normalize_address(bad)
    assert len(Store.normalize_address("가" * 500)) == 500
    with pytest.raises(ValueError, match="픽업 주소는 500자 이하여야 합니다."):
        Store.normalize_address("가" * 501)
    # 내부 공백 정리 후 길이로 판정
    assert Store.normalize_address("가" * 250 + "     " + "나" * 249) == "가" * 250 + " " + "나" * 249


def test_normalize_name():
    assert Store.normalize_name(" a  b ") == "a b"
    for bad in (None, "", "   "):
        with pytest.raises(ValueError, match="상점명은 1자 이상 150자 이하여야 합니다."):
            Store.normalize_name(bad)
    assert len(Store.normalize_name("a" * 150)) == 150
    with pytest.raises(ValueError, match="상점명은 1자 이상 150자 이하여야 합니다."):
        Store.normalize_name("a" * 151)


def test_constructor_checks_address_before_name():
    with pytest.raises(ValueError, match="주소를 입력해 주세요."):
        make(name="", pickup_address="")


@pytest.mark.parametrize("lat,lng", [(90, 180), (-90, -180), (0, 0)])
def test_coordinates_boundaries_ok(lat, lng):
    assert Coordinates(lat, lng).latitude == lat


@pytest.mark.parametrize(
    "lat,lng",
    [(90.1, 0), (-90.1, 0), (0, 180.1), (0, -180.1), (float("nan"), 0), (0, float("inf")), (None, 0)],
)
def test_coordinates_invalid(lat, lng):
    with pytest.raises(ValueError, match="좌표가 올바르지 않습니다."):
        Coordinates(lat, lng)


def test_coordinates_frozen_and_equal():
    c = Coordinates(1.0, 2.0)
    assert c == Coordinates(1.0, 2.0)
    with pytest.raises(Exception):
        c.latitude = 3.0


def test_ensure_can_open_matrix():
    Store.ensure_can_open(owner_already_has_store=False, duplicate_exists=False)
    with pytest.raises(StoreAlreadyExistsError):
        Store.ensure_can_open(owner_already_has_store=True, duplicate_exists=False)
    with pytest.raises(StoreDuplicatedError):
        Store.ensure_can_open(owner_already_has_store=False, duplicate_exists=True)
    with pytest.raises(StoreAlreadyExistsError):  # 둘 다면 이미 개설이 먼저
        Store.ensure_can_open(owner_already_has_store=True, duplicate_exists=True)


def test_new_exceptions():
    e = AddressNotFoundError()
    assert e.error_code == "ADDRESS_NOT_FOUND" and str(e) == "주소를 찾을 수 없습니다."
    assert isinstance(e, ValueError)
    d = StoreDuplicatedError()
    assert d.error_code == "STORE_DUPLICATED" and isinstance(d, ValueError)
    assert str(d) == "동일한 상점명과 주소의 상점이 이미 존재합니다."
    g = GeocodingUnavailableError()
    assert g.error_code == "GEOCODING_UNAVAILABLE" and not isinstance(g, ValueError)
    assert str(g) == "주소 변환 서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해 주세요."
