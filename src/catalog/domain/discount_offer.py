import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from catalog.domain.exceptions import (
    InsufficientStockError,
    OfferAlreadyActiveError,
    OfferClosedError,
    OfferEndedError,
    OfferHasReservationsError,
    OpenOfferExistsError,
    ProductInactiveError,
)

MAX_INITIAL_STOCK = 9999

# 취소 가능 시각 = pickup_start - CANCEL_LEAD_TIME (D55). payments 위약금 기준도 이 값을 따른다 (C14).
CANCEL_LEAD_TIME = timedelta(hours=1)

# 고정 문구 (D54, D55). 문구는 사용자 확인 대기 중(Q30, Q31)이라 이 두 상수에만 둔다.
OFFER_NOTICE = (
    "마감 시간이 가까운 상품으로 수량이 한정되어 있습니다. "
    "픽업 시간 안에 매장을 방문해 예약 확인 코드를 보여주세요. "
    "픽업 시간이 지나면 수령할 수 없습니다."
)
CANCEL_POLICY_DESCRIPTION = (
    "픽업 시작 1시간 전까지 취소할 수 있습니다. "
    "이후에는 취소가 제한되거나 위약금이 부과될 수 있습니다."
)


@dataclass(frozen=True)
class CancelPolicy:
    cancellable_until: datetime
    description: str


class OfferStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    ON_SALE = "ON_SALE"
    SOLD_OUT = "SOLD_OUT"
    CLOSED = "CLOSED"


_EDIT_LABELS = {
    "sale_price": "할인 가격",
    "initial_stock": "최초 수량",
    "sales_start": "판매 시작 시간",
    "sales_end": "판매 마감 시간",
    "pickup_start": "픽업 시작 시간",
    "pickup_end": "픽업 마감 시간",
    "is_active": "활성 여부",
}
_EDITABLE_KEYS = frozenset(_EDIT_LABELS) - {"is_active"}


def _aware(value: datetime, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label}에는 시간대 정보가 필요합니다.")
    return value


# 기본 목록 상태 집합. is_open(D4: is_active 이고 마감 전)과 같은 집합이다.
OPEN_OFFER_STATUSES: tuple[OfferStatus, ...] = (
    OfferStatus.SCHEDULED,
    OfferStatus.ON_SALE,
    OfferStatus.SOLD_OUT,
)


class DiscountOffer:
    def __init__(
        self,
        product_id: uuid.UUID,
        sale_price: int,
        initial_stock: int,
        sales_start: datetime,
        sales_end: datetime,
        pickup_start: datetime,
        pickup_end: datetime,
        remaining_stock: int | None = None,
        status: OfferStatus = OfferStatus.ON_SALE,
        is_active: bool = True,
        id: uuid.UUID | None = None,
    ):
        if isinstance(sale_price, bool) or not isinstance(sale_price, int) or sale_price <= 0:
            raise ValueError("할인 가격은 0보다 커야 합니다.")
        if isinstance(initial_stock, bool) or not isinstance(initial_stock, int) or initial_stock < 0:
            raise ValueError("재고는 0개 이상이어야 합니다.")
        remaining = initial_stock if remaining_stock is None else remaining_stock
        if not 0 <= remaining <= initial_stock:
            raise ValueError("남은 재고가 범위를 벗어났습니다.")
        _aware(sales_start, "판매 시작 시간")
        _aware(sales_end, "판매 마감 시간")
        _aware(pickup_start, "픽업 시작 시간")
        _aware(pickup_end, "픽업 마감 시간")
        if sales_end <= sales_start:
            raise ValueError("판매 마감 시간은 판매 시작 시간 이후여야 합니다.")
        if pickup_end <= pickup_start:
            raise ValueError("픽업 마감 시간은 픽업 시작 시간 이후여야 합니다.")
        self.id = id
        self.product_id = product_id
        self.sale_price = sale_price
        self.initial_stock = initial_stock
        self.remaining_stock = remaining
        self.sales_start = sales_start
        self.sales_end = sales_end
        self.pickup_start = pickup_start
        self.pickup_end = pickup_end
        self.status = OfferStatus(status)
        self.is_active = is_active

    @classmethod
    def register(
        cls,
        original_price: int,
        product_id: uuid.UUID,
        sale_price: int,
        initial_stock: int,
        sales_end: datetime,
        pickup_start: datetime,
        pickup_end: datetime,
        now: datetime,
        sales_start: datetime | None = None,
    ) -> "DiscountOffer":
        if (
            isinstance(initial_stock, bool)
            or not isinstance(initial_stock, int)
            or not 1 <= initial_stock <= MAX_INITIAL_STOCK
        ):
            raise ValueError("수량은 1개 이상 9999개 이하여야 합니다.")
        if isinstance(sale_price, bool) or not isinstance(sale_price, int) or sale_price <= 0:
            raise ValueError("할인 가격은 0보다 커야 합니다.")
        if sale_price >= original_price:
            raise ValueError("할인 가격은 정상 가격보다 낮아야 합니다.")
        start = now if sales_start is None else _aware(sales_start, "판매 시작 시간")
        _aware(sales_end, "판매 마감 시간")
        if sales_end <= start:
            raise ValueError("판매 마감 시간은 판매 시작 시간 이후여야 합니다.")
        if sales_end <= now:  # D10
            raise ValueError("판매 마감 시간은 현재 시각 이후여야 합니다.")
        _aware(pickup_end, "픽업 마감 시간")
        if pickup_end < sales_end:  # D10: 같아도 허용
            raise ValueError("픽업 마감 시간은 판매 마감 시간 이후여야 합니다.")
        _aware(pickup_start, "픽업 시작 시간")
        if pickup_end <= pickup_start:
            raise ValueError("픽업 마감 시간은 픽업 시작 시간 이후여야 합니다.")
        return cls(
            product_id=product_id,
            sale_price=sale_price,
            initial_stock=initial_stock,
            sales_start=start,
            sales_end=sales_end,
            pickup_start=pickup_start,
            pickup_end=pickup_end,
            status=OfferStatus.SCHEDULED if start > now else OfferStatus.ON_SALE,
            is_active=True,
        )

    def effective_status(self, now: datetime) -> OfferStatus:
        """시간 경과를 반영한 상태 (D3). 레포지토리 _status_clause와 같은 우선순위."""
        if not self.is_active:
            return OfferStatus.CLOSED
        if now >= self.sales_end:
            return OfferStatus.CLOSED
        if now < self.sales_start:
            return OfferStatus.SCHEDULED
        if self.remaining_stock == 0:
            return OfferStatus.SOLD_OUT
        return OfferStatus.ON_SALE

    def is_open(self, now: datetime) -> bool:
        """진행 중 (D4)."""
        return self.is_active and now < self.sales_end

    @property
    def is_sold_out(self) -> bool:
        return self.remaining_stock == 0

    def cancel_policy(self) -> CancelPolicy:
        return CancelPolicy(
            cancellable_until=self.pickup_start - CANCEL_LEAD_TIME,
            description=CANCEL_POLICY_DESCRIPTION,
        )

    def discount_rate(self, original_price: int) -> int:
        """할인율(%) 정수 버림 (D1)."""
        return (original_price - self.sale_price) * 100 // original_price

    def ensure_relistable(self) -> None:
        if not self.is_active:
            raise OfferClosedError("이미 중단된 할인은 재등록할 수 없습니다.")

    def close(self, now: datetime) -> None:
        if not self.is_active:
            raise OfferClosedError("이미 중단된 할인입니다.")
        self.is_active = False
        self.status = OfferStatus.CLOSED

    def pause(self, now: datetime) -> None:
        if not self.is_active:
            raise OfferClosedError("이미 중단된 할인입니다.")
        if now >= self.sales_end:
            raise OfferEndedError("판매가 끝난 할인은 중단할 수 없습니다.")
        self.is_active = False
        self.status = OfferStatus.CLOSED

    def resume(self, now: datetime, *, product_active: bool, has_other_open_offer: bool) -> None:
        if self.is_active:
            raise OfferAlreadyActiveError("이미 활성화된 할인입니다.")
        if now >= self.sales_end:
            raise OfferEndedError("판매가 끝난 할인은 재개할 수 없습니다.")
        if not product_active:
            raise ProductInactiveError("비활성화된 상품의 할인은 재개할 수 없습니다.")
        if has_other_open_offer:
            raise OpenOfferExistsError("이미 진행 중인 할인 판매가 있습니다.")
        self.is_active = True
        self._sync_status(now)

    def apply_changes(
        self,
        changes: dict,
        *,
        original_price: int,
        has_reservations: bool,
        now: datetime,
    ) -> int:
        """필드 수정. 모두 검증한 뒤 한꺼번에 반영하고 initial_stock 증감량을 돌려준다 (D26~D29)."""
        if not changes:
            raise ValueError("수정할 항목이 없습니다.")
        for key, value in changes.items():
            if value is None:
                raise ValueError(f"{_EDIT_LABELS.get(key, key)}은(는) null일 수 없습니다.")
        unknown = set(changes) - _EDITABLE_KEYS
        if unknown:
            raise ValueError(f"수정할 수 없는 항목입니다: {', '.join(sorted(unknown))}")
        if not self.is_active or now >= self.sales_end:
            raise OfferClosedError("종료된 할인은 수정할 수 없습니다.")
        if has_reservations:
            raise OfferHasReservationsError("예약이 있는 할인은 수정할 수 없습니다. 재등록을 이용하세요.")

        sale_price = changes.get("sale_price", self.sale_price)
        initial_stock = changes.get("initial_stock", self.initial_stock)
        sales_start = changes.get("sales_start", self.sales_start)
        sales_end = changes.get("sales_end", self.sales_end)
        pickup_start = changes.get("pickup_start", self.pickup_start)
        pickup_end = changes.get("pickup_end", self.pickup_end)

        if isinstance(sale_price, bool) or not isinstance(sale_price, int) or sale_price <= 0:
            raise ValueError("할인 가격은 0보다 커야 합니다.")
        if sale_price >= original_price:
            raise ValueError("할인 가격은 정상 가격보다 낮아야 합니다.")
        if (
            isinstance(initial_stock, bool)
            or not isinstance(initial_stock, int)
            or not 1 <= initial_stock <= MAX_INITIAL_STOCK
        ):
            raise ValueError("수량은 1개 이상 9999개 이하여야 합니다.")
        _aware(sales_start, "판매 시작 시간")
        _aware(sales_end, "판매 마감 시간")
        _aware(pickup_start, "픽업 시작 시간")
        _aware(pickup_end, "픽업 마감 시간")
        if sales_end <= sales_start:
            raise ValueError("판매 마감 시간은 판매 시작 시간 이후여야 합니다.")
        if sales_end <= now:
            raise ValueError("판매 마감 시간은 현재 시각 이후여야 합니다.")
        if pickup_end < sales_end:
            raise ValueError("픽업 마감 시간은 판매 마감 시간 이후여야 합니다.")
        if pickup_end <= pickup_start:
            raise ValueError("픽업 마감 시간은 픽업 시작 시간 이후여야 합니다.")
        delta = initial_stock - self.initial_stock
        if self.remaining_stock + delta < 0:
            sold = self.initial_stock - self.remaining_stock
            raise ValueError(f"최초 수량은 현재까지 줄어든 수량({sold}개)보다 작을 수 없습니다.")

        self.sale_price = sale_price
        self.initial_stock = initial_stock
        self.remaining_stock += delta
        self.sales_start = sales_start
        self.sales_end = sales_end
        self.pickup_start = pickup_start
        self.pickup_end = pickup_end
        self._sync_status(now)
        return delta

    def adjust_stock(self, amount: int, now: datetime) -> None:
        if isinstance(amount, bool) or not isinstance(amount, int) or amount == 0:
            raise ValueError("조정 수량은 0이 될 수 없습니다.")
        if not self.is_active:
            raise OfferClosedError("중단된 할인은 재고를 조정할 수 없습니다.")
        if amount < 0:
            if -amount > self.remaining_stock:
                raise InsufficientStockError("차감할 수량이 남은 재고보다 많습니다.")
            self.remaining_stock += amount
        else:
            if self.initial_stock + amount > MAX_INITIAL_STOCK:
                raise ValueError("최초 수량은 9999개를 넘을 수 없습니다.")
            self.initial_stock += amount
            self.remaining_stock += amount
        self._sync_status(now)

    def _sync_status(self, now: datetime) -> None:
        self.status = self.effective_status(now)
