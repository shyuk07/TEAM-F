import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.domain.exceptions import EmailDuplicatedError, UserNotFoundError
from auth.domain.point_log import PointLog, PointType
from auth.domain.repository.point_log_repository import PointLogRepository
from auth.domain.repository.token_blacklist_repository import TokenBlacklistRepository
from auth.domain.repository.user_repository import UserRepository
from auth.domain.token_blacklist import BlacklistedToken
from auth.domain.user import Role, User
from auth.infrastructure.models import PointLogModel, TokenBlacklistModel, UserModel


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, user_id: uuid.UUID, for_update: bool = False) -> User | None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == User.normalize_email(email))
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def exists_by_email(self, email: str) -> bool:
        stmt = select(UserModel.id).where(UserModel.email == User.normalize_email(email))
        return (await self.session.execute(stmt)).first() is not None

    async def save(self, user: User) -> User:
        if user.id is None:
            model = UserModel(
                email=user.email,
                password_hash=user.password_hash,
                role=str(user.role),
                name=user.name,
                phone=user.phone,
                users_point=user.users_point,
                business_number=user.business_number,
            )
            if user.created_at is not None:
                model.created_at = user.created_at
            self.session.add(model)
            try:
                await self.session.flush()
            except IntegrityError as err:
                raise EmailDuplicatedError() from err
            user.id = model.id
            user.created_at = model.created_at
        else:
            model = await self.session.get(UserModel, user.id)
            if model is None:
                raise UserNotFoundError("저장할 회원을 찾을 수 없습니다.")
            model.users_point = user.users_point
            model.name = user.name
            model.phone = user.phone
            model.password_hash = user.password_hash
            await self.session.flush()
        return user

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            password_hash=model.password_hash,
            role=Role(model.role),
            name=model.name,
            phone=model.phone,
            users_point=model.users_point,
            created_at=model.created_at,
            business_number=model.business_number,
        )


class SqlAlchemyPointLogRepository(PointLogRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, log: PointLog) -> PointLog:
        model = PointLogModel(
            user_id=log.user_id,
            amount=log.amount,
            point_type=str(log.point_type),
        )
        if log.created_at is not None:
            model.created_at = log.created_at
        self.session.add(model)
        await self.session.flush()
        log.id = model.id
        if log.created_at is None:
            log.created_at = model.created_at
        return log

    async def find_by_user(
        self,
        user_id: uuid.UUID,
        *,
        point_type: PointType | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[PointLog]:
        stmt = select(PointLogModel).where(PointLogModel.user_id == user_id)
        if point_type is not None:
            stmt = stmt.where(PointLogModel.point_type == str(point_type))
        stmt = (
            stmt.order_by(PointLogModel.created_at.desc(), PointLogModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        models = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(m) for m in models]

    async def count_by_user(
        self, user_id: uuid.UUID, *, point_type: PointType | None = None
    ) -> int:
        stmt = select(func.count()).select_from(PointLogModel).where(
            PointLogModel.user_id == user_id
        )
        if point_type is not None:
            stmt = stmt.where(PointLogModel.point_type == str(point_type))
        return (await self.session.execute(stmt)).scalar_one()

    @staticmethod
    def _to_domain(model: PointLogModel) -> PointLog:
        return PointLog(
            id=model.id,
            user_id=model.user_id,
            amount=model.amount,
            point_type=PointType(model.point_type),
            created_at=model.created_at,
        )


class SqlAlchemyTokenBlacklistRepository(TokenBlacklistRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, token: BlacklistedToken) -> None:
        stmt = (
            pg_insert(TokenBlacklistModel)
            .values(jti=token.jti, expires_at=token.expires_at)
            .on_conflict_do_nothing(index_elements=["jti"])
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def exists(self, jti: str) -> bool:
        stmt = select(TokenBlacklistModel.jti).where(TokenBlacklistModel.jti == jti)
        return (await self.session.execute(stmt)).first() is not None

    async def delete_expired(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        result = await self.session.execute(
            delete(TokenBlacklistModel).where(TokenBlacklistModel.expires_at <= now)
        )
        return result.rowcount or 0
