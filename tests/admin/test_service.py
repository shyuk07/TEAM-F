"""AdminApplicationService 단위 테스트 (fake 포트 4개 + fake Clock, DB 없음). admin.md 5.4, 9절.

fake는 Protocol에 선언된 메서드만 구현한다(R10): 포트에 없는 메서드를 부르면 AttributeError.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from admin.application.service import AdminApplicationService
from admin.domain.service import Clock
from auth.domain.exceptions import UserNotFoundError
from stores.domain.exceptions import StoreHasReservedReservationsError

pytestmark = pytest.mark.anyio

NOW = datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc)
ADMIN_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
STORE_ID = uuid.uuid4()
OFFER_ID = uuid.uuid4()


@pytest.fixture
def anyio_backend():
    return "asyncio"


class Recorder:
    def __init__(self):
        self.events: list[str] = []
        self.calls: list[tuple[str, dict]] = []

    def record(self, name, **kw):
        self.events.append(name)
        self.calls.append((name, kw))

    def kwargs_of(self, name):
        return [kw for n, kw in self.calls if n == name]


class FakeSession:
    def __init__(self, rec: Recorder):
        self.rec = rec
        self.commits = 0

    async def commit(self):
        self.commits += 1
        self.rec.events.append("commit")


class FakeClock(Clock):
    def __init__(self):
        self.reads = 0

    def now(self):
        self.reads += 1
        return NOW


def user_info(**kw):
    base = dict(
        id=USER_ID, email="u@t.com", name="n", role="CUSTOMER", status="APPROVED",
        approved_at=None, rejected_reason=None, rejected_at=None, suspended_reason=None,
        suspended_at=None, suspended_until=None, deleted_at=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def store_info(status="ACTIVE", is_closed=False, **kw):
    base = dict(
        id=STORE_ID, owner_id=USER_ID, name="상점", status=status, suspended_reason=None,
        suspended_at=None, closed_reason=None, closed_at=None, is_closed=is_closed,
    )
    base.update(kw)
    return SimpleNamespace(**base)


class FakeAccounts:
    def __init__(self, rec, role="CUSTOMER", is_owner=None):
        self.rec = rec
        self.role = role
        # 서비스는 role 문자열이 아니라 is_owner만 본다. 명시하지 않으면 role에서 파생한다.
        self.is_owner = (role == "OWNER") if is_owner is None else is_owner
        self.fail_on: dict[str, Exception] = {}

    def _maybe_fail(self, name):
        if name in self.fail_on:
            raise self.fail_on[name]

    async def get_account(self, user_id):
        self.rec.record("get_account", user_id=user_id)
        self._maybe_fail("get_account")
        return SimpleNamespace(
            id=user_id, role=self.role, status="APPROVED", is_owner=self.is_owner
        )

    async def approve_owner(self, user_id, *, now, commit=True):
        self.rec.record("approve_owner", user_id=user_id, now=now, commit=commit)
        self._maybe_fail("approve_owner")
        return user_info(role="OWNER", status="APPROVED", approved_at=now)

    async def reject_owner(self, user_id, reason, *, now, commit=True):
        self.rec.record("reject_owner", user_id=user_id, reason=reason, now=now, commit=commit)
        self._maybe_fail("reject_owner")
        return user_info(role="OWNER", status="REJECTED", rejected_reason=reason, rejected_at=now)

    async def suspend_user(self, user_id, reason, suspended_until, *, now, commit=True):
        self.rec.record(
            "suspend_user", user_id=user_id, reason=reason, until=suspended_until, now=now,
            commit=commit,
        )
        self._maybe_fail("suspend_user")
        return user_info(status="SUSPENDED", suspended_reason=reason, suspended_at=now)

    async def check_withdrawable(self, user_id, reason):
        self.rec.record("check_withdrawable", user_id=user_id, reason=reason)
        self._maybe_fail("check_withdrawable")

    async def withdraw_user(self, user_id, reason, *, now, commit=True):
        self.rec.record("withdraw_user", user_id=user_id, reason=reason, now=now, commit=commit)
        self._maybe_fail("withdraw_user")
        return user_info(status="WITHDRAWN", deleted_at=now)

    async def grant_points(self, user_id, amount, reason, admin_id, *, now, commit=True):
        self.rec.record(
            "grant_points", user_id=user_id, amount=amount, reason=reason, admin_id=admin_id,
            now=now, commit=commit,
        )
        self._maybe_fail("grant_points")
        return SimpleNamespace(
            id=uuid.uuid4(), user_id=user_id, amount=amount, point_type="GRANT", reason=reason,
            balance_after=amount, created_by=admin_id, created_at=now,
        )

    async def list_points(self, user_id, page, size):
        self.rec.record("list_points", user_id=user_id, page=page, size=size)
        self._maybe_fail("list_points")
        return SimpleNamespace(
            user_id=user_id, balance=0, history=[], page=page, size=size, total=0
        )


class FakeStores:
    def __init__(self, rec, store=None):
        self.rec = rec
        self.store = store
        self.fail_on: dict[str, Exception] = {}

    def _maybe_fail(self, name):
        if name in self.fail_on:
            raise self.fail_on[name]

    async def lock_store(self, store_id):
        self.rec.record("lock_store", store_id=store_id)
        return self.store

    async def lock_store_of_owner(self, owner_id):
        self.rec.record("lock_store_of_owner", owner_id=owner_id)
        return self.store

    async def suspend_store(self, store_id, reason, *, now, commit=True):
        self.rec.record("suspend_store", store_id=store_id, reason=reason, now=now, commit=commit)
        self._maybe_fail("suspend_store")
        return store_info("SUSPENDED", suspended_reason=reason, suspended_at=now)

    async def suspend_stores_of_owner(self, owner_id, reason, *, now, commit=True):
        self.rec.record(
            "suspend_stores_of_owner", owner_id=owner_id, reason=reason, now=now, commit=commit
        )
        self._maybe_fail("suspend_stores_of_owner")
        return self.store

    async def check_force_closable(self, store_id, reason):
        self.rec.record("check_force_closable", store_id=store_id, reason=reason)
        self._maybe_fail("check_force_closable")

    async def close_store_by_admin(
        self, store_id, reason, *, has_reserved_reservations, now, commit=True
    ):
        self.rec.record(
            "close_store_by_admin", store_id=store_id, reason=reason,
            reserved=has_reserved_reservations, now=now, commit=commit,
        )
        self._maybe_fail("close_store_by_admin")
        if has_reserved_reservations:
            raise StoreHasReservedReservationsError()
        return store_info("CLOSED", is_closed=True, closed_reason=reason, closed_at=now)


class FakeOffers:
    def __init__(self, rec):
        self.rec = rec
        self.fail_on: dict[str, Exception] = {}

    async def suspend_offer(self, offer_id, reason, *, now, commit=True):
        self.rec.record("suspend_offer", offer_id=offer_id, reason=reason, now=now, commit=commit)
        if "suspend_offer" in self.fail_on:
            raise self.fail_on["suspend_offer"]
        return SimpleNamespace(
            id=offer_id, store_id=STORE_ID, title="상품", status="SUSPENDED",
            suspended_reason=reason, suspended_at=now,
        )

    async def end_all_sales_of_store(self, store_id, *, now, commit=True):
        self.rec.record("end_all_sales_of_store", store_id=store_id, now=now, commit=commit)
        return 2


class FakeReservations:
    def __init__(self, rec, cancelled=0, reserved=False):
        self.rec = rec
        self.cancelled = cancelled
        self.reserved = reserved

    async def cancel_reserved_for_user(self, user_id, *, reason):
        self.rec.record("cancel_reserved_for_user", user_id=user_id, reason=reason)
        return self.cancelled

    async def has_reserved_for_store(self, store_id):
        self.rec.record("has_reserved_for_store", store_id=store_id)
        return self.reserved


class Ctx:
    def __init__(
        self, role="CUSTOMER", store=None, cancelled=0, reserved=False, is_owner=None
    ):
        self.rec = Recorder()
        self.session = FakeSession(self.rec)
        self.clock = FakeClock()
        self.accounts = FakeAccounts(self.rec, role, is_owner)
        self.stores = FakeStores(self.rec, store)
        self.offers = FakeOffers(self.rec)
        self.reservations = FakeReservations(self.rec, cancelled, reserved)
        self.service = AdminApplicationService(
            session=self.session,
            accounts=self.accounts,
            stores=self.stores,
            offers=self.offers,
            reservations=self.reservations,
            clock=self.clock,
        )

    def assert_no_commit_flag_true(self):
        for name, kw in self.rec.calls:
            if "commit" in kw:
                assert kw["commit"] is False, f"{name}이 commit=False가 아닙니다."

    def assert_single_now(self):
        assert self.clock.reads == 1
        for name, kw in self.rec.calls:
            if "now" in kw:
                assert kw["now"] == NOW, name


def test_constructor_requires_all_args():
    with pytest.raises(TypeError):
        AdminApplicationService()  # type: ignore[call-arg]


# ── EP 1, 2 ──
async def test_approve_owner_commits_once_after_call():
    ctx = Ctx()
    user = await ctx.service.approve_owner(USER_ID)
    assert user.status == "APPROVED" and user.approved_at == NOW
    assert ctx.rec.events == ["approve_owner", "commit"]
    assert ctx.session.commits == 1
    ctx.assert_no_commit_flag_true()
    ctx.assert_single_now()


async def test_approve_owner_failure_never_commits():
    ctx = Ctx()
    ctx.accounts.fail_on["approve_owner"] = ValueError("승인 대기 중인 상점주가 아닙니다.")
    with pytest.raises(ValueError):
        await ctx.service.approve_owner(USER_ID)
    assert ctx.session.commits == 0


async def test_reject_owner_passes_reason_and_commits_once():
    ctx = Ctx()
    user = await ctx.service.reject_owner(USER_ID, "서류 미비")
    assert user.status == "REJECTED"
    assert ctx.rec.events == ["reject_owner", "commit"]
    assert ctx.rec.kwargs_of("reject_owner")[0]["reason"] == "서류 미비"
    ctx.assert_no_commit_flag_true()


async def test_reject_owner_failure_never_commits():
    ctx = Ctx()
    ctx.accounts.fail_on["reject_owner"] = ValueError("거부 사유를 입력해 주세요.")
    with pytest.raises(ValueError):
        await ctx.service.reject_owner(USER_ID, " ")
    assert ctx.session.commits == 0


# ── EP 3 ──
async def test_suspend_customer_does_not_touch_stores():
    ctx = Ctx(role="CUSTOMER")
    await ctx.service.suspend_user(USER_ID, "스팸", None)
    assert ctx.rec.events == ["get_account", "suspend_user", "commit"]
    ctx.assert_no_commit_flag_true()
    ctx.assert_single_now()


async def test_suspend_owner_locks_store_first_then_cascades():
    until = datetime(2026, 12, 1, tzinfo=timezone.utc)
    ctx = Ctx(role="OWNER", store=store_info())
    user = await ctx.service.suspend_user(USER_ID, "위반", until)
    assert user.status == "SUSPENDED"
    assert ctx.rec.events == [
        "get_account", "lock_store_of_owner", "suspend_user", "suspend_stores_of_owner", "commit",
    ]
    assert ctx.rec.kwargs_of("suspend_user")[0]["until"] == until
    assert ctx.rec.kwargs_of("suspend_stores_of_owner")[0]["reason"] == "위반"
    assert ctx.session.commits == 1
    ctx.assert_no_commit_flag_true()
    ctx.assert_single_now()


async def test_suspend_owner_without_store_still_succeeds():
    ctx = Ctx(role="OWNER", store=None)
    await ctx.service.suspend_user(USER_ID, "위반", None)
    assert ctx.session.commits == 1
    assert "suspend_stores_of_owner" in ctx.rec.events


async def test_suspend_user_failure_skips_store_cascade_and_commit():
    ctx = Ctx(role="OWNER", store=store_info())
    ctx.accounts.fail_on["suspend_user"] = ValueError("이미 정지된 회원입니다.")
    with pytest.raises(ValueError):
        await ctx.service.suspend_user(USER_ID, "위반", None)
    assert "suspend_stores_of_owner" not in ctx.rec.events
    assert ctx.session.commits == 0


async def test_suspend_store_cascade_failure_never_commits():
    ctx = Ctx(role="OWNER", store=store_info())
    ctx.stores.fail_on["suspend_stores_of_owner"] = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        await ctx.service.suspend_user(USER_ID, "위반", None)
    assert ctx.session.commits == 0


async def test_suspend_unknown_user_stops_at_get_account():
    ctx = Ctx(role="OWNER", store=store_info())
    ctx.accounts.fail_on["get_account"] = UserNotFoundError()
    with pytest.raises(UserNotFoundError):
        await ctx.service.suspend_user(USER_ID, "x", None)
    assert ctx.rec.events == ["get_account"]
    assert ctx.session.commits == 0


# ── EP 4 ──
async def test_withdraw_owner_full_call_order():
    ctx = Ctx(role="OWNER", store=store_info(), cancelled=0)
    result = await ctx.service.withdraw_user(USER_ID, "약관 위반")
    assert ctx.rec.events == [
        "get_account",
        "check_withdrawable",
        "lock_store_of_owner",
        "end_all_sales_of_store",
        "cancel_reserved_for_user",
        "has_reserved_for_store",
        "close_store_by_admin",
        "withdraw_user",
        "commit",
    ]
    assert result.status == "WITHDRAWN" and result.deleted_at == NOW
    assert result.cancelled_reservation_count == 0
    assert ctx.rec.kwargs_of("cancel_reserved_for_user")[0]["reason"] == "약관 위반"
    assert ctx.rec.kwargs_of("close_store_by_admin")[0]["reserved"] is False
    assert ctx.session.commits == 1
    ctx.assert_no_commit_flag_true()
    ctx.assert_single_now()


async def test_withdraw_customer_skips_store_steps_but_cancels_reservations():
    ctx = Ctx(role="CUSTOMER", cancelled=3)
    result = await ctx.service.withdraw_user(USER_ID, "약관 위반")
    assert ctx.rec.events == [
        "get_account", "check_withdrawable", "cancel_reserved_for_user", "withdraw_user", "commit",
    ]
    assert result.cancelled_reservation_count == 3


async def test_withdraw_owner_without_store_skips_store_steps():
    ctx = Ctx(role="OWNER", store=None)
    await ctx.service.withdraw_user(USER_ID, "x")
    assert ctx.rec.events == [
        "get_account", "check_withdrawable", "lock_store_of_owner",
        "cancel_reserved_for_user", "withdraw_user", "commit",
    ]


async def test_withdraw_owner_with_closed_store_skips_close_and_end_sales():
    ctx = Ctx(role="OWNER", store=store_info("CLOSED", is_closed=True))
    await ctx.service.withdraw_user(USER_ID, "x")
    assert "end_all_sales_of_store" not in ctx.rec.events
    assert "close_store_by_admin" not in ctx.rec.events
    assert "has_reserved_for_store" not in ctx.rec.events
    assert ctx.session.commits == 1


async def test_withdraw_store_with_is_closed_false_counts_as_open_store():
    # status 문자열이 CLOSED여도 is_closed가 False면 서비스는 열린 상점으로 본다.
    ctx = Ctx(role="OWNER", store=store_info("CLOSED", is_closed=False))
    await ctx.service.withdraw_user(USER_ID, "x")
    assert "end_all_sales_of_store" in ctx.rec.events
    assert "close_store_by_admin" in ctx.rec.events


async def test_withdraw_store_with_is_closed_true_is_not_open_store():
    # status가 ACTIVE여도 is_closed가 True면 닫힌 상점으로 본다.
    ctx = Ctx(role="OWNER", store=store_info("ACTIVE", is_closed=True))
    await ctx.service.withdraw_user(USER_ID, "x")
    assert "end_all_sales_of_store" not in ctx.rec.events
    assert "close_store_by_admin" not in ctx.rec.events


async def test_withdraw_owner_path_is_driven_by_is_owner_not_role_string():
    ctx = Ctx(role="OWNER", is_owner=False, store=store_info())
    await ctx.service.withdraw_user(USER_ID, "x")
    assert "lock_store_of_owner" not in ctx.rec.events
    assert "close_store_by_admin" not in ctx.rec.events

    ctx = Ctx(role="CUSTOMER", is_owner=True, store=store_info())
    await ctx.service.withdraw_user(USER_ID, "x")
    assert "lock_store_of_owner" in ctx.rec.events
    assert "close_store_by_admin" in ctx.rec.events


async def test_suspend_user_owner_path_is_driven_by_is_owner():
    ctx = Ctx(role="CUSTOMER", is_owner=True, store=store_info())
    await ctx.service.suspend_user(USER_ID, "x", None)
    assert "lock_store_of_owner" in ctx.rec.events
    assert "suspend_stores_of_owner" in ctx.rec.events


async def test_withdraw_with_reserved_reservations_rolls_back_everything():
    ctx = Ctx(role="OWNER", store=store_info(), reserved=True)
    with pytest.raises(StoreHasReservedReservationsError):
        await ctx.service.withdraw_user(USER_ID, "x")
    assert ctx.session.commits == 0
    assert "withdraw_user" not in ctx.rec.events


async def test_withdraw_not_withdrawable_fails_before_heavy_work():
    ctx = Ctx(role="OWNER", store=store_info())
    ctx.accounts.fail_on["check_withdrawable"] = ValueError("이미 탈퇴한 회원입니다.")
    with pytest.raises(ValueError):
        await ctx.service.withdraw_user(USER_ID, "x")
    assert ctx.rec.events == ["get_account", "check_withdrawable"]
    assert ctx.session.commits == 0


# ── EP 5 ──
async def test_suspend_store_commits_once():
    ctx = Ctx()
    store = await ctx.service.suspend_store(STORE_ID, "위생")
    assert store.status == "SUSPENDED"
    assert ctx.rec.events == ["suspend_store", "commit"]
    ctx.assert_no_commit_flag_true()
    ctx.assert_single_now()


async def test_suspend_store_failure_never_commits():
    ctx = Ctx()
    ctx.stores.fail_on["suspend_store"] = ValueError("이미 정지된 상점입니다.")
    with pytest.raises(ValueError):
        await ctx.service.suspend_store(STORE_ID, "위생")
    assert ctx.session.commits == 0


# ── EP 6 ──
async def test_close_store_call_order():
    ctx = Ctx()
    store = await ctx.service.close_store(STORE_ID, "폐업")
    assert store.status == "CLOSED"
    assert ctx.rec.events == [
        "check_force_closable", "end_all_sales_of_store", "has_reserved_for_store",
        "close_store_by_admin", "commit",
    ]
    assert ctx.session.commits == 1
    ctx.assert_no_commit_flag_true()
    ctx.assert_single_now()


async def test_close_store_precheck_failure_stops_everything():
    ctx = Ctx()
    ctx.stores.fail_on["check_force_closable"] = ValueError("이미 폐점된 상점입니다.")
    with pytest.raises(ValueError):
        await ctx.service.close_store(STORE_ID, "폐업")
    assert ctx.rec.events == ["check_force_closable"]
    assert ctx.session.commits == 0


async def test_close_store_with_reserved_reservations_does_not_commit():
    ctx = Ctx(reserved=True)
    with pytest.raises(StoreHasReservedReservationsError):
        await ctx.service.close_store(STORE_ID, "폐업")
    assert ctx.rec.kwargs_of("close_store_by_admin")[0]["reserved"] is True
    assert ctx.session.commits == 0


# ── EP 7 ──
async def test_suspend_offer_commits_once():
    ctx = Ctx()
    offer = await ctx.service.suspend_offer(OFFER_ID, "위생")
    assert offer.status == "SUSPENDED" and offer.title == "상품"
    assert ctx.rec.events == ["suspend_offer", "commit"]
    ctx.assert_no_commit_flag_true()
    ctx.assert_single_now()


async def test_suspend_offer_failure_never_commits():
    ctx = Ctx()
    ctx.offers.fail_on["suspend_offer"] = ValueError("이미 정지된 상품입니다.")
    with pytest.raises(ValueError):
        await ctx.service.suspend_offer(OFFER_ID, "위생")
    assert ctx.session.commits == 0


# ── EP 8, 9 ──
async def test_get_user_points_is_read_only():
    ctx = Ctx()
    page = await ctx.service.get_user_points(USER_ID, 2, 10)
    assert (page.page, page.size) == (2, 10)
    assert ctx.rec.events == ["list_points"]
    assert ctx.session.commits == 0
    assert ctx.clock.reads == 0


async def test_grant_points_passes_admin_id_and_commits_once():
    ctx = Ctx()
    log = await ctx.service.grant_points(ADMIN_ID, USER_ID, 500, "이벤트")
    assert log.point_type == "GRANT" and log.created_by == ADMIN_ID
    assert ctx.rec.events == ["grant_points", "commit"]
    kw = ctx.rec.kwargs_of("grant_points")[0]
    assert kw["admin_id"] == ADMIN_ID and kw["amount"] == 500 and kw["reason"] == "이벤트"
    ctx.assert_no_commit_flag_true()
    ctx.assert_single_now()


async def test_grant_points_failure_never_commits():
    ctx = Ctx()
    ctx.accounts.fail_on["grant_points"] = ValueError("지급 포인트는 1 이상이어야 합니다.")
    with pytest.raises(ValueError):
        await ctx.service.grant_points(ADMIN_ID, USER_ID, 0, "x")
    assert ctx.session.commits == 0
