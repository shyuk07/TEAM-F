"""관리자 정지·종료 도메인 규칙 (admin.md 3.3: D17~D22, C6, C8)."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from catalog.domain.discount_offer import OPEN_OFFER_STATUSES, DiscountOffer, OfferStatus
from catalog.domain.exceptions import (
    OfferAlreadySuspendedError,
    OfferSalesEndedError,
    OfferSuspendedError,
    StoreClosedError,
    StoreNotApprovedError,
    StoreNotFoundError,
    StoreSuspendedError,
)
from catalog.domain.store_ref import StoreRef

NOW = datetime(2026, 11, 3, 9, 0, tzinfo=timezone.utc)
H = timedelta(hours=1)


def offer(**kw):
    args = dict(
        original_price=6000, product_id=uuid.uuid4(), sale_price=3000, initial_stock=10,
        sales_end=NOW + 2 * H, pickup_start=NOW + H, pickup_end=NOW + 3 * H, now=NOW,
    )
    args.update(kw)
    return DiscountOffer.register(**args)


def suspended_offer(**kw):
    o = offer(**kw)
    o.suspend("위생 문제", NOW)
    return o


def edit(o, changes, **kw):
    args = dict(original_price=6000, has_reservations=False, now=NOW)
    args.update(kw)
    return o.apply_changes(changes, **args)


def info(**kw):
    class I:
        id = uuid.uuid4()
        owner_id = uuid.uuid4()
        name = "상점"
        pickup_address = "주소"
        latitude = None
        longitude = None
        approval_at = NOW
        closed_at = None
        suspended_at = None

    for k, v in kw.items():
        setattr(I, k, v)
    return I


# ── suspend ──
def test_suspend_sets_fields_and_keeps_is_active():
    o = offer()
    o.suspend("  위생 문제  ", NOW)
    assert o.status == OfferStatus.SUSPENDED and o.is_suspended
    assert o.suspended_reason == "위생 문제" and o.suspended_at == NOW
    assert o.is_active is True  # D19


def test_suspend_error_order():
    o = offer()
    for blank in ("", "   ", None):
        with pytest.raises(ValueError, match="정지 사유를 입력해 주세요."):
            o.suspend(blank, NOW)
    with pytest.raises(ValueError, match="사유는 500자 이하여야 합니다."):
        o.suspend("a" * 501, NOW)
    o.suspend("a" * 500, NOW)
    # 사유 -> 이미 정지 -> 판매 종료
    with pytest.raises(ValueError, match="정지 사유를 입력해 주세요."):
        o.suspend(" ", NOW)
    with pytest.raises(OfferAlreadySuspendedError) as e:
        o.suspend("다시", NOW)
    assert str(e.value) == "이미 정지된 상품입니다." and e.value.error_code == "OFFER_ALREADY_SUSPENDED"
    ended = offer()
    ended.is_active = False
    with pytest.raises(OfferSalesEndedError) as e:
        ended.suspend("x", NOW)
    assert str(e.value) == "판매가 종료된 상품입니다." and e.value.error_code == "OFFER_SALES_ENDED"
    with pytest.raises(OfferSalesEndedError):
        offer().suspend("x", NOW + 2 * H)  # now >= sales_end 경계
    offer().suspend("x", NOW + 2 * H - timedelta(seconds=1))
    with pytest.raises(ValueError, match="시간대"):
        offer().suspend("x", datetime(2026, 11, 3, 9, 0))


def test_suspend_allowed_for_scheduled_and_sold_out():  # D21
    sched = offer(sales_start=NOW + H // 2)
    sched.suspend("x", NOW)
    assert sched.status == OfferStatus.SUSPENDED
    sold = offer()
    sold.adjust_stock(-10, NOW)
    sold.suspend("x", NOW)
    assert sold.is_suspended and sold.remaining_stock == 0


def test_suspend_failure_leaves_state():
    o = offer()
    o.is_active = False
    with pytest.raises(OfferSalesEndedError):
        o.suspend("x", NOW)
    assert o.suspended_at is None and o.suspended_reason is None and o.status == OfferStatus.ON_SALE


# ── effective_status / is_open ──
def test_effective_status_six_level_priority():
    # 1 비활성 > 2 정지 > 3 마감 경과 > 4 시작 전 > 5 품절 > 6 판매 중
    o = suspended_offer(sales_start=NOW + H // 2)
    assert o.effective_status(NOW) == OfferStatus.SUSPENDED  # 정지 > 시작 전
    assert o.effective_status(NOW + 2 * H) == OfferStatus.SUSPENDED  # 정지 > 마감 경과
    o.remaining_stock = 0
    assert o.effective_status(NOW + H) == OfferStatus.SUSPENDED  # 정지 > 품절
    o.is_active = False
    assert o.effective_status(NOW) == OfferStatus.CLOSED  # 비활성 > 정지
    n = offer(sales_start=NOW + H // 2)  # 정지 아님: 기존 우선순위 유지
    assert n.effective_status(NOW) == OfferStatus.SCHEDULED
    assert n.effective_status(NOW + 2 * H) == OfferStatus.CLOSED
    n.remaining_stock = 0
    assert n.effective_status(NOW + H) == OfferStatus.SOLD_OUT
    n.remaining_stock = 5
    assert n.effective_status(NOW + H) == OfferStatus.ON_SALE


def test_is_open_counts_suspended_offer_as_open():  # D22
    o = suspended_offer()
    assert o.is_open(NOW) and not o.is_open(NOW + 2 * H)


def test_suspended_is_not_in_default_list_statuses():  # C6, D20
    assert OfferStatus.SUSPENDED not in OPEN_OFFER_STATUSES
    o = suspended_offer()
    assert o.effective_status(NOW) not in OPEN_OFFER_STATUSES


def test_open_statuses_identity_with_suspended_exception():
    """C6: is_open 참 집합 - {SUSPENDED} == OPEN_OFFER_STATUSES.

    설계 불일치(보고): 마감이 지난 정지 할인은 effective_status가 SUSPENDED(우선순위 2)인데 is_open은 거짓이다.
    """
    cases = [offer(), offer(sales_start=NOW + H // 2)]
    sold = offer()
    sold.adjust_stock(-10, NOW)
    closed = offer()
    closed.close(NOW)
    cases += [sold, closed]
    for o in cases:
        for now in (NOW, NOW + 5 * H):
            assert (o.effective_status(now) in OPEN_OFFER_STATUSES) == o.is_open(now)
    s = suspended_offer()
    assert s.effective_status(NOW + 5 * H) == OfferStatus.SUSPENDED and not s.is_open(NOW + 5 * H)


# ── end_sale ──
def test_end_sale_is_idempotent():  # D18
    o = offer()
    assert o.end_sale(NOW) is True
    assert not o.is_active and o.status == OfferStatus.CLOSED
    assert (o.initial_stock, o.remaining_stock) == (10, 10)
    assert o.end_sale(NOW) is False
    assert not o.is_active and o.status == OfferStatus.CLOSED


def test_end_sale_ends_suspended_offer_and_keeps_history():
    o = suspended_offer()
    assert o.end_sale(NOW + H) is True
    assert not o.is_active and o.status == OfferStatus.CLOSED
    assert o.suspended_reason == "위생 문제" and o.suspended_at == NOW
    assert o.effective_status(NOW + H) == OfferStatus.CLOSED
    assert o.end_sale(NOW + H) is False


def test_end_sale_on_expired_active_offer_still_ends():
    o = offer()
    assert o.end_sale(NOW + 5 * H) is True and not o.is_active


# ── 상점주 조작 가드 ──
def test_owner_operations_rejected_on_suspended_offer():  # D20
    calls = {
        "pause": lambda o: o.pause(NOW),
        "resume": lambda o: o.resume(NOW, product_active=True, has_other_open_offer=False),
        "close": lambda o: o.close(NOW),
        "apply_changes": lambda o: edit(o, {"sale_price": 2000}),
        "apply_changes_empty": lambda o: edit(o, {}),  # 가드가 빈 변경 검사보다 먼저
        "adjust_stock": lambda o: o.adjust_stock(1, NOW),
        "adjust_stock_zero": lambda o: o.adjust_stock(0, NOW),  # 가드가 0 검사보다 먼저
        "relist": lambda o: o.ensure_relistable(),
    }
    for name, call in calls.items():
        o = suspended_offer()
        before = (o.is_active, o.status, o.sale_price, o.initial_stock, o.remaining_stock)
        with pytest.raises(OfferSuspendedError) as e:
            call(o)
        assert str(e.value) == "관리자에 의해 정지된 상품입니다.", name
        assert e.value.error_code == "OFFER_SUSPENDED", name
        assert before == (o.is_active, o.status, o.sale_price, o.initial_stock, o.remaining_stock), name


def test_suspended_guard_comes_before_other_errors():
    o = suspended_offer()
    with pytest.raises(OfferSuspendedError):  # 마감 경과여도 정지 가드가 먼저
        o.pause(NOW + 5 * H)
    with pytest.raises(OfferSuspendedError):
        edit(o, {"sale_price": 2000}, has_reservations=True)


def test_new_error_classes_are_value_errors():
    for cls in (OfferSuspendedError, OfferAlreadySuspendedError, OfferSalesEndedError, StoreSuspendedError):
        assert issubclass(cls, ValueError)


# ── 생성자 불변식 ──
def test_offer_constructor_suspension_invariants():
    base = dict(
        product_id=uuid.uuid4(), sale_price=100, initial_stock=5,
        sales_start=NOW, sales_end=NOW + H, pickup_start=NOW, pickup_end=NOW + H,
    )
    with pytest.raises(ValueError, match="함께"):
        DiscountOffer(**base, suspended_reason="x")
    with pytest.raises(ValueError, match="함께"):
        DiscountOffer(**base, suspended_at=NOW)
    with pytest.raises(ValueError, match="시간대"):
        DiscountOffer(**base, suspended_reason="x", suspended_at=datetime(2026, 11, 3, 9))
    with pytest.raises(ValueError, match="정지"):
        DiscountOffer(**base, status=OfferStatus.SUSPENDED)
    ok = DiscountOffer(**base, status=OfferStatus.SUSPENDED, suspended_reason="x", suspended_at=NOW)
    assert ok.is_suspended


def test_is_visible_hides_suspended_from_non_owner():
    o = suspended_offer()
    assert not o.is_visible(NOW, viewer_is_owner=False)
    assert o.is_visible(NOW, viewer_is_owner=True)
    assert offer().is_visible(NOW, viewer_is_owner=False)
    ended = suspended_offer()
    ended.end_sale(NOW)
    assert ended.is_visible(NOW, viewer_is_owner=False)  # CLOSED가 SUSPENDED보다 우선


# ── StoreRef 정지 ──
def test_store_ref_suspended_flag_from_info():
    assert StoreRef.from_info(info(suspended_at=NOW)).suspended
    assert not StoreRef.from_info(info()).suspended
    assert not StoreRef(uuid.uuid4(), uuid.uuid4(), "s", "a", approved=True, closed=False).suspended


def test_store_ref_ensure_visible_to():  # D17, C8
    ref = StoreRef.from_info(info(suspended_at=NOW))
    ref.ensure_visible_to(ref.owner_id)
    for viewer in (None, uuid.uuid4()):
        with pytest.raises(StoreNotFoundError, match="상점을 찾을 수 없습니다."):
            ref.ensure_visible_to(viewer)
    normal = StoreRef.from_info(info())
    normal.ensure_visible_to(None)
    normal.ensure_visible_to(uuid.uuid4())
    assert ref.is_visible_to(ref.owner_id) and not ref.is_visible_to(None)


def test_store_ref_precedence_closed_over_suspended():  # admin.md D16
    both = StoreRef.from_info(info(suspended_at=NOW, closed_at=NOW))
    assert both.closed and not both.suspended
    # 닫힌 상점은 일반 폐점 상점처럼 모두에게 보인다
    assert both.is_visible_to(None) and both.is_visible_to(uuid.uuid4())
    both.ensure_visible_to(None)
    only_susp = StoreRef.from_info(info(suspended_at=NOW))
    assert only_susp.suspended and not only_susp.closed
    only_closed = StoreRef.from_info(info(closed_at=NOW))
    assert only_closed.closed and not only_closed.suspended
    # 생성자 직접 지정도 같은 우선순위
    direct = StoreRef(uuid.uuid4(), uuid.uuid4(), "s", "a", approved=True, closed=True, suspended=True)
    assert direct.closed and not direct.suspended


def test_store_ref_register_order_closed_suspended_not_approved():
    with pytest.raises(StoreClosedError):
        StoreRef.from_info(info(approval_at=None, closed_at=NOW, suspended_at=NOW)).ensure_can_register("상품")
    with pytest.raises(StoreSuspendedError) as e:
        StoreRef.from_info(info(approval_at=None, suspended_at=NOW)).ensure_can_register("할인")
    assert e.value.error_code == "STORE_SUSPENDED"
    assert str(e.value) == "관리자에 의해 정지된 상점입니다."
    with pytest.raises(StoreNotApprovedError):
        StoreRef.from_info(info(approval_at=None)).ensure_can_register("상품")
    StoreRef.from_info(info()).ensure_can_register("상품")
