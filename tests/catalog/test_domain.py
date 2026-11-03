import uuid
from datetime import datetime, timedelta, timezone

import pytest

from catalog.domain.discount_offer import DiscountOffer, OfferStatus
from catalog.domain.exceptions import (
    InsufficientStockError,
    NotStoreOwnerError,
    OfferClosedError,
    ProductAlreadyInactiveError,
    ProductHasOpenOfferError,
    ProductInactiveError,
    StoreClosedError,
    StoreNotApprovedError,
)
from catalog.domain.product import Product
from catalog.domain.stock_log import StockLog
from catalog.domain.store_ref import StoreRef

NOW = datetime(2026, 11, 3, 9, 0, tzinfo=timezone.utc)
H = timedelta(hours=1)


def product(**kw):
    kw.setdefault("store_id", uuid.uuid4())
    kw.setdefault("name", "샌드위치")
    kw.setdefault("original_price", 6000)
    return Product.register(**kw)


def offer(**kw):
    args = dict(
        original_price=6000, product_id=uuid.uuid4(), sale_price=3000, initial_stock=10,
        sales_end=NOW + 2 * H, pickup_start=NOW + H, pickup_end=NOW + 3 * H, now=NOW,
    )
    args.update(kw)
    return DiscountOffer.register(**args)


# ── StoreRef ──
def info(**kw):
    class I:
        id = uuid.uuid4()
        owner_id = uuid.uuid4()
        name = "상점"
        pickup_address = "주소"
        approval_at = NOW
        closed_at = None

    for k, v in kw.items():
        setattr(I, k, v)
    return I


def test_store_ref_flags():
    ref = StoreRef.from_info(info(approval_at=None, closed_at=NOW))
    assert not ref.approved and ref.closed


def test_store_ref_owner():
    ref = StoreRef.from_info(info())
    ref.ensure_owner(ref.owner_id, "m")
    with pytest.raises(NotStoreOwnerError, match="m"):
        ref.ensure_owner(uuid.uuid4(), "m")
    assert not ref.is_owned_by(None)


def test_store_ref_register_order_closed_first():
    with pytest.raises(StoreClosedError) as e:
        StoreRef.from_info(info(approval_at=None, closed_at=NOW)).ensure_can_register("상품")
    assert str(e.value) == "폐점된 상점에서는 상품을 등록할 수 없습니다."
    with pytest.raises(StoreNotApprovedError) as e:
        StoreRef.from_info(info(approval_at=None)).ensure_can_register("상품")
    assert str(e.value) == "승인되지 않은 상점에는 상품을 등록할 수 없습니다."
    StoreRef.from_info(info()).ensure_can_register("할인")


# ── Product ──
def test_product_register_defaults():
    p = product(product_image=["a"])
    assert p.is_active and p.product_image == ["a"] and p.id is None


@pytest.mark.parametrize("price", [0, -1, True, "5"])
def test_product_bad_price(price):
    with pytest.raises(ValueError, match="정상 가격은 0보다 커야 합니다."):
        product(original_price=price)


@pytest.mark.parametrize("name", ["", "   ", "a" * 201, None])
def test_product_bad_name(name):
    with pytest.raises(ValueError):
        product(name=name)


def test_product_name_stripped_and_category_limits():
    assert product(name="  빵 ").name == "빵"
    assert product(category="a" * 80).category == "a" * 80
    for bad in ["", "a" * 81]:
        with pytest.raises(ValueError):
            product(category=bad)


def test_product_images():
    with pytest.raises(ValueError, match="최대 10개"):
        product(product_image=["a"] * 11)
    with pytest.raises(ValueError):
        product(product_image=[" "])
    imgs = ["a"]
    p = product(product_image=imgs)
    imgs.append("b")
    assert p.product_image == ["a"]


def test_apply_changes_partial():
    p = product()
    p.apply_changes({"name": "새", "description": None, "category": None}, None)
    assert p.name == "새" and p.description is None and p.original_price == 6000


def test_apply_changes_empty_and_unknown():
    p = product()
    with pytest.raises(ValueError, match="수정할 항목이 없습니다."):
        p.apply_changes({}, None)
    with pytest.raises(ValueError):
        p.apply_changes({"is_active": False}, None)


def test_apply_changes_null_rejected_for_required():
    p = product()
    for key in ["name", "original_price", "product_image"]:  # D16
        with pytest.raises(ValueError):
            p.apply_changes({key: None}, None)
    p.apply_changes({"product_image": []}, None)


def test_apply_changes_price_vs_open_offer():
    p = product()
    with pytest.raises(ValueError, match="진행 중인 할인 가격보다 커야"):
        p.apply_changes({"original_price": 3000}, 3000)
    assert p.original_price == 6000
    p.apply_changes({"original_price": 3001}, 3000)
    assert p.original_price == 3001


def test_apply_changes_is_atomic():
    p = product()
    with pytest.raises(ValueError):
        p.apply_changes({"name": "새", "original_price": 0}, None)
    assert p.name == "샌드위치"


def test_deactivate():
    p = product()
    with pytest.raises(ProductHasOpenOfferError):
        p.deactivate(True)
    assert p.is_active
    p.deactivate(False)
    assert not p.is_active
    with pytest.raises(ProductAlreadyInactiveError, match="이미 비활성화된 상품입니다."):
        p.deactivate(True)  # 비활성 검사가 먼저
    with pytest.raises(ProductInactiveError):
        p.ensure_active_for_offer()


# ── DiscountOffer.register ──
def test_register_on_sale_and_scheduled():
    o = offer()
    assert o.status == OfferStatus.ON_SALE and o.sales_start == NOW and o.remaining_stock == 10
    s = offer(sales_start=NOW + H // 2)
    assert s.status == OfferStatus.SCHEDULED


@pytest.mark.parametrize(
    "kw,msg",
    [
        (dict(initial_stock=0), "수량은 1개 이상 9999개 이하"),
        (dict(initial_stock=10000), "수량은 1개 이상 9999개 이하"),
        (dict(sale_price=0), "할인 가격은 0보다"),
        (dict(sale_price=6000), "할인 가격은 정상 가격보다 낮아야 합니다."),
        (dict(sales_start=NOW + 3 * H), "판매 마감 시간은 판매 시작 시간 이후여야 합니다."),
        (dict(sales_end=NOW), "판매 마감 시간은 판매 시작 시간 이후여야 합니다."),
        (dict(sales_start=NOW - 2 * H, sales_end=NOW - H, pickup_end=NOW + H),
         "판매 마감 시간은 현재 시각 이후여야 합니다."),
        (dict(pickup_end=NOW + H), "픽업 마감 시간은 판매 마감 시간 이후여야 합니다."),
        (dict(pickup_start=NOW + 3 * H), "픽업 마감 시간은 픽업 시작 시간 이후여야 합니다."),
        (dict(sales_end=datetime(2026, 11, 3, 12)), "시간대"),
    ],
)
def test_register_errors(kw, msg):
    with pytest.raises(ValueError, match=msg):
        offer(**kw)


def test_register_pickup_end_equal_sales_end_allowed():
    offer(pickup_start=NOW, pickup_end=NOW + 2 * H)


def test_stock_boundaries():
    assert offer(initial_stock=1).initial_stock == 1
    assert offer(initial_stock=9999).initial_stock == 9999


def test_discount_rate_floor():
    assert offer(sale_price=3000).discount_rate(6000) == 50
    assert offer(sale_price=4001).discount_rate(6000) == 33  # 33.3 버림
    assert offer(sale_price=1).discount_rate(6000) == 99  # 99.98 버림


# ── effective_status ──
def test_effective_status_priority():
    o = offer(sales_start=NOW + H // 2)
    assert o.effective_status(NOW) == OfferStatus.SCHEDULED
    assert o.effective_status(NOW + H) == OfferStatus.ON_SALE
    o.remaining_stock = 0
    assert o.effective_status(NOW + H) == OfferStatus.SOLD_OUT
    assert o.effective_status(NOW) == OfferStatus.SCHEDULED  # 시작 전이면 재고 0이어도 SCHEDULED
    assert o.effective_status(NOW + 2 * H) == OfferStatus.CLOSED  # now >= sales_end
    o2 = offer()
    o2.is_active = False
    assert o2.effective_status(NOW) == OfferStatus.CLOSED


def test_is_open():
    o = offer()
    assert o.is_open(NOW) and o.is_open(NOW + 2 * H - timedelta(seconds=1))
    assert not o.is_open(NOW + 2 * H)
    o.is_active = False
    assert not o.is_open(NOW)


# ── close / relist ──
def test_close_and_relistable():
    o = offer()
    o.ensure_relistable()
    o.close(NOW)
    assert o.status == OfferStatus.CLOSED and not o.is_active
    with pytest.raises(OfferClosedError, match="이미 중단된 할인은 재등록할 수 없습니다."):
        o.ensure_relistable()
    with pytest.raises(OfferClosedError):
        o.close(NOW)


# ── adjust_stock ──
def test_adjust_increase_raises_initial():
    o = offer(initial_stock=10)
    o.adjust_stock(5, NOW)
    assert (o.initial_stock, o.remaining_stock) == (15, 15)


def test_adjust_decrease_keeps_initial():
    o = offer(initial_stock=10)
    o.adjust_stock(-3, NOW)
    assert (o.initial_stock, o.remaining_stock) == (10, 7)


def test_adjust_to_zero_sold_out_then_restock():
    o = offer(initial_stock=2)
    o.adjust_stock(-2, NOW)
    assert o.status == OfferStatus.SOLD_OUT and o.is_sold_out
    o.adjust_stock(1, NOW)
    assert o.status == OfferStatus.ON_SALE and o.remaining_stock == 1


def test_adjust_scheduled_stays_scheduled():
    o = offer(sales_start=NOW + H // 2, initial_stock=1)
    o.adjust_stock(-1, NOW)
    assert o.status == OfferStatus.SCHEDULED
    o.adjust_stock(1, NOW)
    assert o.status == OfferStatus.SCHEDULED


def test_adjust_errors_leave_state():
    o = offer(initial_stock=2)
    with pytest.raises(ValueError, match="0이 될 수 없습니다"):
        o.adjust_stock(0, NOW)
    with pytest.raises(InsufficientStockError):
        o.adjust_stock(-3, NOW)
    o.adjust_stock(9997, NOW)  # 9999까지 허용
    assert o.initial_stock == 9999
    with pytest.raises(ValueError, match="9999개를 넘을 수 없습니다"):
        o.adjust_stock(1, NOW)
    assert (o.initial_stock, o.remaining_stock) == (9999, 9999)


def test_adjust_closed_rejected_but_time_expired_allowed():
    o = offer()
    o.adjust_stock(1, NOW + 5 * H)  # 시간만 지난 건 허용 (D8)
    assert o.status == OfferStatus.CLOSED
    o.close(NOW)
    with pytest.raises(OfferClosedError):
        o.adjust_stock(1, NOW)


def test_constructor_invariants():
    with pytest.raises(ValueError):
        DiscountOffer(uuid.uuid4(), 100, 5, NOW, NOW + H, NOW, NOW + H, remaining_stock=6)
    with pytest.raises(ValueError):
        DiscountOffer(uuid.uuid4(), 100, 5, NOW, NOW - H, NOW, NOW + H)


# ── StockLog ──
def test_stock_log():
    oid = uuid.uuid4()
    assert StockLog.initial_stock(oid, None, 5).reason == "최초 입고"
    log = StockLog.manual_adjustment(oid, uuid.uuid4(), -2, "  파손 ")
    assert log.amount == -2 and log.reason == "파손"
    assert StockLog.manual_adjustment(oid, None, 1, "  ").reason is None
    with pytest.raises(ValueError):
        StockLog.manual_adjustment(oid, None, 0, None)
    with pytest.raises(ValueError):
        StockLog.manual_adjustment(oid, None, 1, "a" * 201)
