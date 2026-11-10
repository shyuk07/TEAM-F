"""reservations가 외부 모듈에 요구하는 포트. catalog·payments를 import하지 않고 구조적으로 맞춘다 (R11)."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from reservations.application.views import RefundTarget


class OfferTermsInfo(Protocol):
    offer_id: uuid.UUID
    owner_id: uuid.UUID
    store_name: str
    product_name: str
    pickup_address: str
    sale_price: int
    pickup_start: datetime
    pickup_end: datetime
    cancellable_until: datetime  # 고객 취소·환불 마감 시각(Catalog 정책)


class StockPort(Protocol):
    """재고와 할인 조건. commit하지 않는다 (R13)."""

    async def get_terms(self, offer_id: uuid.UUID, *, for_update: bool = False) -> OfferTermsInfo: ...

    async def reserve(
        self, offer_id: uuid.UUID, quantity: int, *, user_id: uuid.UUID, now: datetime
    ) -> OfferTermsInfo: ...

    # 닫힌(중단) 할인은 복구하지 않고 False(D40). 복구 상한 초과(데이터 이상)는 DataInconsistentError.
    async def release(
        self, offer_id: uuid.UUID, quantity: int, *, user_id: uuid.UUID, reason: str, now: datetime
    ) -> bool: ...


class RefundPort(Protocol):
    """결제 모듈. commit하지 않는다 (R13)."""

    async def refund_for_cancelled_reservation(
        self, target: RefundTarget, *, reason: str, waive_penalty: bool = False
    ) -> None: ...

    # 예약이 PENDING_PAYMENT일 때 취소 전에 부르는 읽기 전용 확인(RD-39). 쓰기·commit 없음.
    # 결제가 없거나 PAID가 아니면 반환, PAID면 DataInconsistentError(500).
    async def ensure_no_paid_payment(self, reservation_id: uuid.UUID) -> None: ...



class StoreOffersPort(Protocol):
    """매장의 할인 ID 목록. catalog 추상 레포지토리를 쓰는 어댑터가 만족한다. commit 없음 (R13)."""

    async def list_offer_ids_of_store(
        self, store_id: uuid.UUID, *, for_update: bool = False
    ) -> list[uuid.UUID]: ...

    async def get_pickup_ends(self, offer_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, datetime]:
        """할인별 픽업 마감 시각. 없는 할인은 빠진다. 잠그지 않는다."""
        ...


class StoreOwnerInfo(Protocol):
    """상점 소유 확인에 필요한 값만. stores의 Store가 구조적으로 만족한다 (R11)."""

    owner_id: uuid.UUID


class StoreOwnerPort(Protocol):
    """상점 1건 조회. stores StoreQueryService가 구조적으로 만족한다. commit 없음 (R13)."""

    async def find_store_by_id(self, store_id: uuid.UUID) -> StoreOwnerInfo | None: ...
