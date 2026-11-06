import math
import uuid
from collections.abc import Sequence

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from stores.domain.exceptions import (
    StoreAlreadyExistsError,
    StoreDuplicatedError,
    StoreNotFoundError,
)
from stores.domain.repository import StoreRepository
from stores.domain.store import Store
from stores.infrastructure.models import StoreModel

# 제약 이름 -> 도메인 예외
_UNIQUE_VIOLATIONS = {
    "uq_stores_owner_id": StoreAlreadyExistsError,
    "uq_stores_name_address": StoreDuplicatedError,
}

_EARTH_RADIUS_KM = 6371.0


class SqlAlchemyStoreRepository(StoreRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, store_id: uuid.UUID, for_update: bool = False) -> Store | None:
        stmt = select(StoreModel).where(StoreModel.id == store_id)
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_by_ids(self, store_ids: Sequence[uuid.UUID]) -> list[Store]:
        ids = list(dict.fromkeys(store_ids))
        if not ids:
            return []
        stmt = select(StoreModel).where(StoreModel.id.in_(ids)).order_by(StoreModel.id)
        models = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(m) for m in models]

    async def find_by_owner_id(
        self, owner_id: uuid.UUID, for_update: bool = False
    ) -> Store | None:
        stmt = select(StoreModel).where(StoreModel.owner_id == owner_id)
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def exists_by_name_and_address(self, name: str, pickup_address: str) -> bool:
        stmt = select(
            exists().where(
                StoreModel.name == name, StoreModel.pickup_address == pickup_address
            )
        )
        return bool(await self.session.scalar(stmt))

    async def find_visible_near(
        self,
        *,
        latitude: float | None,
        longitude: float | None,
        radius_km: float | None,
    ) -> list[tuple[Store, float | None]]:
        if (latitude is None) != (longitude is None):
            raise ValueError("위도와 경도는 함께 지정해야 합니다.")
        visible = (
            StoreModel.approval_at.is_not(None),
            StoreModel.closed_at.is_(None),
            StoreModel.suspended_at.is_(None),
        )
        if latitude is None:
            stmt = select(StoreModel).where(*visible).order_by(StoreModel.name, StoreModel.id)
            models = (await self.session.execute(stmt)).scalars().all()
            return [(self._to_domain(m), None) for m in models]

        if radius_km is None or not radius_km >= 0:
            raise ValueError("검색 반경이 올바르지 않습니다.")
        lat1, lng1 = float(latitude), float(longitude)
        a = func.power(
            func.sin(func.radians(StoreModel.latitude - lat1) / 2), 2
        ) + math.cos(math.radians(lat1)) * func.cos(
            func.radians(StoreModel.latitude)
        ) * func.power(func.sin(func.radians(StoreModel.longitude - lng1) / 2), 2)
        distance = (2 * _EARTH_RADIUS_KM * func.asin(func.sqrt(func.least(1.0, a)))).label(
            "distance_km"
        )
        lat_delta = radius_km / 111.0
        stmt = (
            select(StoreModel, distance)
            .where(
                *visible,
                StoreModel.latitude.is_not(None),
                StoreModel.longitude.is_not(None),
                StoreModel.latitude.between(lat1 - lat_delta, lat1 + lat_delta),
            )
            .where(distance <= radius_km)
            .order_by(distance, StoreModel.id)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(self._to_domain(m), float(d)) for m, d in rows]

    async def save(self, store: Store) -> Store:
        if store.id is None:
            model = StoreModel(
                owner_id=store.owner_id,
                name=store.name,
                pickup_address=store.pickup_address,
                latitude=store.latitude,
                longitude=store.longitude,
                approval_at=store.approval_at,
                closed_at=store.closed_at,
                suspended_reason=store.suspended_reason,
                suspended_at=store.suspended_at,
                closed_reason=store.closed_reason,
            )
            self.session.add(model)
            try:
                await self.session.flush()
            except IntegrityError as err:
                for constraint, error in _UNIQUE_VIOLATIONS.items():
                    if constraint in str(err.orig):
                        raise error() from err
                raise
            store.id = model.id
            store.created_at = model.created_at
        else:
            model = await self.session.get(StoreModel, store.id)
            if model is None:
                raise StoreNotFoundError("저장할 상점을 찾을 수 없습니다.")
            model.approval_at = store.approval_at
            model.closed_at = store.closed_at
            model.suspended_reason = store.suspended_reason
            model.suspended_at = store.suspended_at
            model.closed_reason = store.closed_reason
            await self.session.flush()
        return store

    @staticmethod
    def _to_domain(model: StoreModel) -> Store:
        return Store(
            id=model.id,
            owner_id=model.owner_id,
            name=model.name,
            pickup_address=model.pickup_address,
            latitude=model.latitude,
            longitude=model.longitude,
            created_at=model.created_at,
            approval_at=model.approval_at,
            closed_at=model.closed_at,
            suspended_reason=model.suspended_reason,
            suspended_at=model.suspended_at,
            closed_reason=model.closed_reason,
        )
