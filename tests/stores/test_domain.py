import uuid
from datetime import datetime, timedelta, timezone

import pytest

from stores.domain.exceptions import NotStoreOwnerError, StoreAlreadyClosedError
from stores.domain.store import Store

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
    s = Store.open(OWNER, "상호", "주소", NOW)
    assert s.approval_at == NOW and s.is_approved and s.closed_at is None


def test_open_naive_now_rejected():
    with pytest.raises(ValueError):
        Store.open(OWNER, "상호", "주소", datetime(2026, 1, 1))


def test_open_validates():
    with pytest.raises(ValueError):
        Store.open(OWNER, "", "주소", NOW)


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
    s = Store.open(OWNER, "상호", "주소", NOW)
    later = NOW + timedelta(days=1)
    s.close(later)
    assert s.closed_at == later and s.is_closed
    with pytest.raises(StoreAlreadyClosedError, match="이미 폐점된 상점입니다."):
        s.close(later)


def test_close_unapproved():
    with pytest.raises(ValueError, match="승인되지 않은 상점은 폐점할 수 없습니다."):
        make().close(NOW)


def test_close_before_approval_and_naive():
    s = Store.open(OWNER, "상호", "주소", NOW)
    with pytest.raises(ValueError):
        s.close(NOW - timedelta(seconds=1))
    with pytest.raises(ValueError):
        s.close(datetime(2026, 1, 1))
    assert not s.is_closed


def test_store_info_attributes():
    s = make()
    for attr in ("id", "owner_id", "name", "pickup_address", "approval_at", "closed_at"):
        assert hasattr(s, attr)
