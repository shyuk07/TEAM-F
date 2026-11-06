import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from reservations.domain.exceptions import ReservationNotFoundError
from reservations.domain.pickup_reservation import PickupReservation, ReservationStatus
from reservations.domain.repository import ReservationRepository
from reservations.infrastructure.models import PickupReservationModel


class SqlAlchemyReservationRepository(ReservationRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(
        self, reservation_id: uuid.UUID, for_update: bool = False
    ) -> PickupReservation | None:
        stmt = select(PickupReservationModel).where(PickupReservationModel.id == reservation_id)
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_by_user(
        self,
        user_id: uuid.UUID,
        *,
        status: ReservationStatus | None,
        page: int,
        size: int,
    ) -> tuple[list[PickupReservation], int]:
        conditions = [PickupReservationModel.user_id == user_id]
        if status is not None:
            conditions.append(PickupReservationModel.status == str(status))
        total = await self.session.scalar(
            select(func.count()).select_from(PickupReservationModel).where(*conditions)
        )
        stmt = (
            select(PickupReservationModel)
            .where(*conditions)
            .order_by(PickupReservationModel.created_at.desc(), PickupReservationModel.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        models = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(m) for m in models], int(total or 0)

    async def find_by_offer(
        self, offer_id: uuid.UUID, *, for_update: bool = False
    ) -> list[PickupReservation]:
        stmt = (
            select(PickupReservationModel)
            .where(PickupReservationModel.offer_id == offer_id)
            .order_by(PickupReservationModel.id)  # 잠금 순서 고정(교착 방지)
        )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        models = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(m) for m in models]

    async def exists_by_offer(self, offer_id: uuid.UUID) -> bool:
        found = await self.session.scalar(
            select(PickupReservationModel.id)
            .where(PickupReservationModel.offer_id == offer_id)
            .limit(1)
        )
        return found is not None

    async def find_by_user_and_statuses(
        self,
        user_id: uuid.UUID,
        statuses: Sequence[ReservationStatus],
        *,
        for_update: bool = False,
    ) -> list[PickupReservation]:
        stmt = (
            select(PickupReservationModel)
            .where(
                PickupReservationModel.user_id == user_id,
                PickupReservationModel.status.in_([str(s) for s in statuses]),
            )
            .order_by(PickupReservationModel.offer_id, PickupReservationModel.id)  # 잠금 순서 고정(교착 방지)
        )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        models = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(m) for m in models]

    async def exists_by_offers_and_status(
        self,
        offer_ids: Sequence[uuid.UUID],
        status: ReservationStatus,
        *,
        excluding_user_id: uuid.UUID | None = None,
    ) -> bool:
        if not offer_ids:
            return False
        conditions = [
            PickupReservationModel.offer_id.in_(list(offer_ids)),
            PickupReservationModel.status == str(status),
        ]
        if excluding_user_id is not None:
            conditions.append(PickupReservationModel.user_id != excluding_user_id)
        found = await self.session.scalar(
            select(PickupReservationModel.id).where(*conditions).limit(1)
        )
        return found is not None

    async def find_by_offers(
        self,
        offer_ids: Sequence[uuid.UUID],
        *,
        status: ReservationStatus | None,
        page: int,
        size: int,
    ) -> tuple[list[PickupReservation], int]:
        if not offer_ids:
            return [], 0
        conditions = [PickupReservationModel.offer_id.in_(list(offer_ids))]
        if status is not None:
            conditions.append(PickupReservationModel.status == str(status))
        total = await self.session.scalar(
            select(func.count()).select_from(PickupReservationModel).where(*conditions)
        )
        stmt = (
            select(PickupReservationModel)
            .where(*conditions)
            .order_by(PickupReservationModel.created_at.desc(), PickupReservationModel.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        models = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(m) for m in models], int(total or 0)

    async def save(self, reservation: PickupReservation) -> PickupReservation:
        if reservation.id is None:
            model = PickupReservationModel(
                user_id=reservation.user_id,
                offer_id=reservation.offer_id,
                quantity=reservation.quantity,
                unit_price=reservation.unit_price,
                total_price=reservation.total_price,
                status=str(reservation.status),
                pickup_code=reservation.pickup_code,
                store_name=reservation.store_name,
                pickup_address=reservation.pickup_address,
                product_name=reservation.product_name,
                cancelled_at=reservation.cancelled_at,
                picked_up_at=reservation.picked_up_at,
            )
            if reservation.created_at is not None:
                model.created_at = reservation.created_at
            self.session.add(model)
            await self.session.flush()
            reservation.id = model.id
            reservation.created_at = model.created_at
        else:
            model = await self.session.get(PickupReservationModel, reservation.id)
            if model is None:
                raise ReservationNotFoundError("저장할 예약을 찾을 수 없습니다.")
            model.status = str(reservation.status)
            model.cancelled_at = reservation.cancelled_at
            model.picked_up_at = reservation.picked_up_at
            await self.session.flush()
        return reservation

    @staticmethod
    def _to_domain(model: PickupReservationModel) -> PickupReservation:
        return PickupReservation(
            id=model.id,
            user_id=model.user_id,
            offer_id=model.offer_id,
            quantity=model.quantity,
            unit_price=model.unit_price,  # type: ignore[arg-type]  # NULL이면 데이터 이상 -> 도메인 검증이 실패시킴
            total_price=model.total_price,  # type: ignore[arg-type]
            status=ReservationStatus(model.status),  # type: ignore[arg-type]
            pickup_code=model.pickup_code,  # type: ignore[arg-type]
            store_name=model.store_name,  # type: ignore[arg-type]
            pickup_address=model.pickup_address,  # type: ignore[arg-type]
            product_name=model.product_name,  # type: ignore[arg-type]
            created_at=model.created_at,
            cancelled_at=model.cancelled_at,
            picked_up_at=model.picked_up_at,
        )
