import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.domain.exceptions import EmailDuplicatedError, UserNotFoundError
from auth.domain.password_reset_code import PasswordResetCode
from auth.domain.point_log import PointLog, PointType
from auth.domain.repository.password_reset_code_repository import PasswordResetCodeRepository
from auth.domain.repository.point_log_repository import PointLogRepository
from auth.domain.repository.token_blacklist_repository import TokenBlacklistRepository
from auth.domain.repository.user_repository import UserRepository
from auth.domain.token_blacklist import BlacklistedToken
from auth.domain.user import Role, User, UserStatus
from auth.domain.user_list_query import UserListQuery
from auth.infrastructure.models import (
    PasswordResetCodeModel,
    PointLogModel,
    TokenBlacklistModel,
    UserModel,
)


def _status_clause(status: UserStatus, now: datetime):
    """실효 상태 필터. User.effective_status와 같은 규칙이다(until <= now는 만료).
    한쪽을 고치면 다른 쪽도 함께 고친다(일관성 테스트: tests/auth/test_user_list_repository_db.py)."""
    expired = and_(
        UserModel.status == "SUSPENDED",
        UserModel.suspended_until.is_not(None),
        UserModel.suspended_until <= now,
    )
    if status is UserStatus.APPROVED:
        return or_(UserModel.status == "APPROVED", expired)
    if status is UserStatus.SUSPENDED:
        return and_(
            UserModel.status == "SUSPENDED",
            or_(UserModel.suspended_until.is_(None), UserModel.suspended_until > now),
        )
    return UserModel.status == status.value


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, user_id: uuid.UUID, for_update: bool = False) -> User | None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        if for_update:
            # 잠금 대기 뒤 최신 행을 반영한다(identity map의 오래된 상태 방지)
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
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
                token_version=user.token_version,
                token_keep_jti=user.token_keep_jti,
            )
            self._write_status(model, user)
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
            model.token_version = user.token_version
            model.token_keep_jti = user.token_keep_jti
            self._write_status(model, user)
            await self.session.flush()
        return user

    async def find_all(self, query: UserListQuery, now: datetime) -> list[User]:
        stmt = (
            select(UserModel)
            .where(*self._conditions(query, now))
            .order_by(UserModel.created_at.asc(), UserModel.id.asc())
            .offset(query.offset)
            .limit(query.size)
        )
        models = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(m) for m in models]

    async def count_all(self, query: UserListQuery, now: datetime) -> int:
        stmt = select(func.count()).select_from(UserModel).where(*self._conditions(query, now))
        return (await self.session.execute(stmt)).scalar_one()

    @staticmethod
    def _conditions(query: UserListQuery, now: datetime) -> list:
        conditions = []
        if query.role is not None:
            conditions.append(UserModel.role == query.role.value)
        if query.status is not None:
            conditions.append(_status_clause(query.status, now))
        if query.email is not None:
            # ILIKE ... ESCAPE '/': %, _ 는 글자 그대로
            conditions.append(UserModel.email.icontains(query.email, autoescape=True))
        return conditions

    @staticmethod
    def _write_status(model: UserModel, user: User) -> None:
        model.status = str(user.status)
        model.approved_at = user.approved_at
        model.rejected_reason = user.rejected_reason
        model.rejected_at = user.rejected_at
        model.suspended_reason = user.suspended_reason
        model.suspended_at = user.suspended_at
        model.suspended_until = user.suspended_until
        model.deleted_at = user.deleted_at
        model.deleted_reason = user.deleted_reason

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
            status=UserStatus(model.status),
            approved_at=model.approved_at,
            rejected_reason=model.rejected_reason,
            rejected_at=model.rejected_at,
            suspended_reason=model.suspended_reason,
            suspended_at=model.suspended_at,
            suspended_until=model.suspended_until,
            deleted_at=model.deleted_at,
            deleted_reason=model.deleted_reason,
            token_version=model.token_version,
            token_keep_jti=model.token_keep_jti,
        )


class SqlAlchemyPointLogRepository(PointLogRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, log: PointLog) -> PointLog:
        model = PointLogModel(
            user_id=log.user_id,
            amount=log.amount,
            point_type=str(log.point_type),
            reason=log.reason,
            balance_after=log.balance_after,
            created_by=log.created_by,
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
            reason=model.reason,
            balance_after=model.balance_after,
            created_by=model.created_by,
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


class SqlAlchemyPasswordResetCodeRepository(PasswordResetCodeRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_user_id(
        self, user_id: uuid.UUID, for_update: bool = False
    ) -> PasswordResetCode | None:
        stmt = select(PasswordResetCodeModel).where(PasswordResetCodeModel.user_id == user_id)
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def save(self, code: PasswordResetCode) -> PasswordResetCode:
        values = {
            "code_hash": code.code_hash,
            "expires_at": code.expires_at,
            "failed_attempts": code.failed_attempts,
        }
        if code.created_at is not None:
            values["created_at"] = code.created_at
        stmt = (
            pg_insert(PasswordResetCodeModel)
            .values(user_id=code.user_id, **values)
            .on_conflict_do_update(index_elements=["user_id"], set_=values)
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return code

    async def delete(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(PasswordResetCodeModel).where(PasswordResetCodeModel.user_id == user_id)
        )
        await self.session.flush()

    @staticmethod
    def _to_domain(model: PasswordResetCodeModel) -> PasswordResetCode:
        return PasswordResetCode(
            user_id=model.user_id,
            code_hash=model.code_hash,
            expires_at=model.expires_at,
            failed_attempts=model.failed_attempts,
            created_at=model.created_at,
        )
