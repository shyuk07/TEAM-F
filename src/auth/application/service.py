import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from auth.domain.exceptions import (
    AuthenticationError,
    EmailDuplicatedError,
    InvalidCredentialsError,
    InvalidPageError,
    TokenRevokedError,
    UserNotFoundError,
)
from auth.domain.point_log import PointLog, PointType
from auth.domain.repository.point_log_repository import PointLogRepository
from auth.domain.repository.token_blacklist_repository import TokenBlacklistRepository
from auth.domain.repository.user_repository import UserRepository
from auth.domain.service import Clock, PasswordHasher, TokenProvider
from auth.domain.token_claims import TokenClaims
from auth.domain.user import Role, User

MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user: User
    claims: TokenClaims


@dataclass(frozen=True)
class LoginResult:
    token: str
    status: str  # 로그인 시점의 유효 상태 (D40)


@dataclass(frozen=True)
class PointHistoryPage:
    """관리자 포인트 이력 조회 결과 (1부터 시작하는 page, D25)."""

    user_id: uuid.UUID
    balance: int
    history: list[PointLog]
    page: int
    size: int
    total: int


@dataclass(frozen=True)
class PointLogPage:
    users_point: int
    logs: list[PointLog]
    page: int
    size: int
    total_elements: int


class AuthApplicationService:
    """다른 모듈은 이 서비스를 생성자 인자로 주입받아 commit=False로 호출한다 (src/container.py에서 연결)."""

    def __init__(
        self,
        session: AsyncSession,
        users: UserRepository,
        point_logs: PointLogRepository,
        blacklist: TokenBlacklistRepository,
        hasher: PasswordHasher,
        tokens: TokenProvider,
        clock: Clock,
    ):
        self.session = session
        self.users = users
        self.point_logs = point_logs
        self.blacklist = blacklist
        self.hasher = hasher
        self.tokens = tokens
        self.clock = clock

    async def signup(
        self,
        email: str,
        password: str,
        role: str,
        name: str | None = None,
        phone: str | None = None,
    ) -> User:
        User.validate_raw_password(password)
        Role.for_signup(role)  # 해싱 전에 ADMIN 등 거부
        password_hash = self.hasher.hash(password)
        user = User.register(
            email=email, password_hash=password_hash, role=role, name=name, phone=phone
        )
        if await self.users.exists_by_email(user.email):
            raise EmailDuplicatedError()
        try:
            await self.users.save(user)
        except EmailDuplicatedError:
            await self.session.rollback()
            raise
        await self.session.commit()
        return user

    async def ensure_admin(
        self, email: str, password: str, name: str | None = None
    ) -> tuple[User, bool]:
        """관리자를 보장한다. (user, 새로 만들었는지). 기존 계정은 승격·비밀번호 갱신을 하지 않는다."""
        User.validate_raw_password(password)
        existing = await self.users.find_by_email(User.normalize_email(email))
        if existing is not None:
            return self._existing_admin(existing), False
        admin = User.register_admin(
            email=email, password_hash=self.hasher.hash(password), name=name
        )
        try:
            await self.users.save(admin)
        except EmailDuplicatedError:
            await self.session.rollback()
            existing = await self.users.find_by_email(admin.email)
            if existing is None:
                raise
            return self._existing_admin(existing), False
        await self.session.commit()
        return admin, True

    @staticmethod
    def _existing_admin(user: User) -> User:
        if not user.has_role(Role.ADMIN):
            raise EmailDuplicatedError("같은 이메일의 관리자가 아닌 계정이 있어 관리자를 만들 수 없습니다.")
        return user

    async def login(self, email: str, password: str) -> LoginResult:
        user = await self.users.find_by_email(User.normalize_email(email))
        if user is None:
            self.hasher.dummy_verify(password)
            raise InvalidCredentialsError()
        if not self.hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError()
        now = self.clock.now()
        user.ensure_can_login(now)  # 비밀번호 검증 성공 뒤에만 상태를 알려 준다 (D8)
        token, _ = self.tokens.issue(user.id, user.role)
        return LoginResult(token=token, status=user.effective_status(now).value)

    async def authenticate(
        self, token: str, *, allow_suspended: bool = False
    ) -> AuthenticatedPrincipal:
        claims = self.tokens.decode(token)
        if await self.blacklist.exists(claims.jti):
            raise TokenRevokedError()
        user = await self.users.find_by_id(claims.user_id)
        if user is None:
            raise AuthenticationError("유효하지 않은 토큰입니다.")
        user.ensure_can_authenticate(self.clock.now(), allow_suspended=allow_suspended)
        return AuthenticatedPrincipal(user=user, claims=claims)

    async def logout(self, claims: TokenClaims) -> None:
        await self.blacklist.add(claims.to_blacklist_entry())
        await self.session.commit()

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self.users.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        return user

    async def list_point_logs(
        self, user: User, point_type: PointType | None, page: int, size: int
    ) -> PointLogPage:
        if page < 0:
            raise ValueError("page는 0 이상이어야 합니다.")
        if size < 1 or size > MAX_PAGE_SIZE:
            raise ValueError(f"size는 1 이상 {MAX_PAGE_SIZE} 이하여야 합니다.")
        logs = await self.point_logs.find_by_user(
            user.id, point_type=point_type, offset=page * size, limit=size
        )
        total = await self.point_logs.count_by_user(user.id, point_type=point_type)
        return PointLogPage(
            users_point=user.users_point, logs=logs, page=page, size=size, total_elements=total
        )

    async def _locked_user(self, user_id: uuid.UUID) -> User:
        user = await self.users.find_by_id(user_id, for_update=True)
        if user is None:
            raise UserNotFoundError()
        return user

    async def _finish(self, commit: bool) -> None:
        if commit:
            await self.session.commit()

    async def use_points(self, user_id: uuid.UUID, amount: int, *, commit: bool = True) -> User:
        user = await self._locked_user(user_id)
        user.use_points(amount)
        await self.users.save(user)
        await self.point_logs.add(PointLog.record(user.id, PointType.USE, -amount, user.users_point))
        await self._finish(commit)
        return user

    async def earn_points(self, user_id: uuid.UUID, amount: int, *, commit: bool = True) -> User:
        user = await self._locked_user(user_id)
        user.earn_points(amount)
        await self.users.save(user)
        await self.point_logs.add(PointLog.record(user.id, PointType.EARN, amount, user.users_point))
        await self._finish(commit)
        return user

    async def restore_points(
        self, user_id: uuid.UUID, amount: int, *, commit: bool = True
    ) -> User:
        user = await self._locked_user(user_id)
        user.restore_points(amount)
        await self.users.save(user)
        await self.point_logs.add(PointLog.record(user.id, PointType.RESTORE, amount, user.users_point))
        await self._finish(commit)
        return user

    async def revoke_points(
        self, user_id: uuid.UUID, amount: int, *, commit: bool = True
    ) -> int:
        user = await self._locked_user(user_id)
        actual = user.revoke_points(amount)
        await self.users.save(user)
        if actual > 0:
            await self.point_logs.add(PointLog.record(user.id, PointType.REVOKE, -actual, user.users_point))
        await self._finish(commit)
        return actual

    # ── 관리자용 (admin 모듈이 포트로 호출, commit=False) ──────────
    async def get_account(self, user_id: uuid.UUID) -> User:
        return await self.get_user(user_id)

    async def approve_owner(
        self, user_id: uuid.UUID, *, now: datetime, commit: bool = True
    ) -> User:
        user = await self._locked_user(user_id)
        user.approve_owner(now)
        await self.users.save(user)
        await self._finish(commit)
        return user

    async def reject_owner(
        self, user_id: uuid.UUID, reason: str, *, now: datetime, commit: bool = True
    ) -> User:
        user = await self._locked_user(user_id)
        user.reject_owner(reason, now)
        await self.users.save(user)
        await self._finish(commit)
        return user

    async def suspend_user(
        self,
        user_id: uuid.UUID,
        reason: str,
        suspended_until: datetime | None,
        *,
        now: datetime,
        commit: bool = True,
    ) -> User:
        user = await self._locked_user(user_id)
        user.suspend(reason, suspended_until, now)
        await self.users.save(user)
        await self._finish(commit)
        return user

    async def check_withdrawable(self, user_id: uuid.UUID, reason: str) -> None:
        user = await self.get_user(user_id)
        user.ensure_withdrawable(reason)

    async def withdraw_user(
        self, user_id: uuid.UUID, reason: str, *, now: datetime, commit: bool = True
    ) -> User:
        user = await self._locked_user(user_id)
        user.withdraw(reason, now)
        await self.users.save(user)
        await self._finish(commit)
        return user

    async def grant_points(
        self,
        user_id: uuid.UUID,
        amount: int,
        reason: str,
        admin_id: uuid.UUID,
        *,
        now: datetime,
        commit: bool = True,
    ) -> PointLog:
        user = await self._locked_user(user_id)
        normalized = user.grant_points(amount, reason)
        await self.users.save(user)
        log = await self.point_logs.add(
            PointLog.record(
                user.id,
                PointType.GRANT,
                amount,
                user.users_point,
                reason=normalized,
                created_by=admin_id,
            )
        )
        await self._finish(commit)
        return log

    async def list_points(self, user_id: uuid.UUID, page: int, size: int) -> PointHistoryPage:
        if page < 1 or size < 1 or size > MAX_PAGE_SIZE:
            raise InvalidPageError()
        user = await self.get_user(user_id)
        history = await self.point_logs.find_by_user(
            user.id, offset=(page - 1) * size, limit=size
        )
        total = await self.point_logs.count_by_user(user.id)
        return PointHistoryPage(
            user_id=user.id,
            balance=user.users_point,
            history=history,
            page=page,
            size=size,
            total=total,
        )

    async def purge_expired_tokens(self, now: datetime | None = None) -> int:
        deleted = await self.blacklist.delete_expired(now)
        await self.session.commit()
        return deleted
