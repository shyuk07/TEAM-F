import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from stores.domain.exceptions import StoreAlreadyExistsError, StoreNotFoundError
from stores.domain.repository import StoreRepository
from stores.domain.store import Store
from stores.infrastructure.models import StoreModel

_OWNER_UNIQUE = "uq_stores_owner_id"


class SqlAlchemyStoreRepository(StoreRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, store_id: uuid.UUID, for_update: bool = False) -> Store | None:
        stmt = select(StoreModel).where(StoreModel.id == store_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_by_ids(self, store_ids: Sequence[uuid.UUID]) -> list[Store]:
        ids = list(dict.fromkeys(store_ids))
        if not ids:
            return []
        stmt = select(StoreModel).where(StoreModel.id.in_(ids)).order_by(StoreModel.id)
        models = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(m) for m in models]

    async def find_by_owner_id(self, owner_id: uuid.UUID) -> Store | None:
        stmt = select(StoreModel).where(StoreModel.owner_id == owner_id)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

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
            )
            self.session.add(model)
            try:
                await self.session.flush()
            except IntegrityError as err:
                if _OWNER_UNIQUE in str(err.orig):
                    raise StoreAlreadyExistsError() from err
                raise
            store.id = model.id
            store.created_at = model.created_at
        else:
            model = await self.session.get(StoreModel, store.id)
            if model is None:
                raise StoreNotFoundError("저장할 상점을 찾을 수 없습니다.")
            model.approval_at = store.approval_at
            model.closed_at = store.closed_at
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
        )
