import logging
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
from auth.domain.repository.password_reset_code_repository import PasswordResetCodeRepository
from auth.domain.repository.point_log_repository import PointLogRepository
from auth.domain.repository.token_blacklist_repository import TokenBlacklistRepository
from auth.domain.repository.user_repository import UserRepository
from auth.domain.service import Clock, PasswordHasher, TokenProvider
from auth.domain.token_claims import TokenClaims
from auth.domain.user import SELF_WITHDRAWAL_REASON, Role, User
from auth.domain.user_list_query import DEFAULT_PAGE, DEFAULT_SIZE, UserListQuery

MAX_PAGE_SIZE = 100

logger = logging.getLogger("auth.login")


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


@dataclass(frozen=True)
class UserSummary:
    """관리자 회원 목록 항목. 민감 정보(해시·전화번호·사유)를 담지 않는다. status는 실효 상태."""

    id: uuid.UUID
    email: str
    name: str | None
    role: str
    status: str
    created_at: datetime

    @classmethod
    def from_user(cls, user: User, now: datetime) -> "UserSummary":
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role.value,
            status=user.effective_status(now).value,
            created_at=user.created_at,
        )


@dataclass(frozen=True)
class UserPage:
    items: list[UserSummary]
    page: int
    size: int
    total: int


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
        codes: PasswordResetCodeRepository,
    ):
        self.session = session
        self.users = users
        self.point_logs = point_logs
        self.blacklist = blacklist
        self.hasher = hasher
        self.tokens = tokens
        self.clock = clock
        self.codes = codes

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
        snapshot = await self.users.find_by_email(User.normalize_email(email))  # 행 잠금 없음
        if snapshot is None:  # 가입되지 않음: 잠금·저장 없음
            self.hasher.dummy_verify(password)
            raise InvalidCredentialsError()
        verified = self.hasher.verify(password, snapshot.password_hash)  # bcrypt는 행 잠금 밖 (D-잠금판정순서)
        now = self.clock.now()
        user = await self.users.find_by_id(snapshot.id, for_update=True)  # D-잠금경합
        if user is None or user.password_hash != snapshot.password_hash:
            raise InvalidCredentialsError()
        if not verified:
            if user.record_login_failure(now):  # 탈퇴·잠금 중이면 False
                await self.users.save(user)
                await self.session.commit()  # 횟수를 남기려고 커밋한 뒤 예외 (R5)
                if user.is_login_locked(now):
                    logger.warning("로그인 연속 실패로 계정 잠금: user_id=%s", user.id)
            raise InvalidCredentialsError()
        user.ensure_can_login(now)  # 탈퇴 401 -> 잠금 429 -> 정지 403 (비밀번호가 맞을 때만 알린다, D8)
        if user.clear_login_failures():
            await self.users.save(user)
            await self.session.commit()
        token, _ = self.tokens.issue(user.id, user.role, token_version=user.token_version)
        return LoginResult(token=token, status=user.effective_status(now).value)

    async def authenticate(
        self, token: str, *, allow_suspended: bool = False, allow_suspended_owner: bool = False
    ) -> AuthenticatedPrincipal:
        claims = self.tokens.decode(token)
        if await self.blacklist.exists(claims.jti):
            raise TokenRevokedError()
        user = await self.users.find_by_id(claims.user_id)
        if user is None:
            raise AuthenticationError("유효하지 않은 토큰입니다.")
        user.ensure_can_authenticate(
            self.clock.now(),
            allow_suspended=allow_suspended,
            allow_suspended_owner=allow_suspended_owner,
        )
        user.ensure_token_current(claims.token_version, claims.jti)  # 비밀번호 변경·재설정 뒤 이전 토큰 무효
        return AuthenticatedPrincipal(user=user, claims=claims)

    async def logout(self, claims: TokenClaims) -> None:
        await self.blacklist.add(claims.to_blacklist_entry())
        await self.session.commit()

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self.users.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        return user

    async def update_profile(
        self, user_id: uuid.UUID, name: str | None, phone: str | None
    ) -> User:
        user = await self._locked_user(user_id)
        user.update_profile(name, phone)
        await self.users.save(user)
        await self.session.commit()
        return user

    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str,
        *,
        keep_jti: str | None,
    ) -> None:
        user = await self._locked_user(user_id)
        user.change_password(current_password, new_password, self.hasher, keep_jti=keep_jti)
        await self.users.save(user)
        await self.session.commit()

    async def check_self_withdrawable(self, user_id: uuid.UUID, password: str) -> User:
        """자진 탈퇴 사전 확인(읽기 전용): 비밀번호 확인 → 탈퇴 가능 여부."""
        user = await self.get_user(user_id)
        user.ensure_current_password(password, self.hasher)
        user.ensure_withdrawable(SELF_WITHDRAWAL_REASON)
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
        expired = user.withdraw(reason, now)  # 남은 포인트는 소멸(잔액 0). 복구(환불)가 먼저 끝나 있어야 한다
        await self.users.save(user)
        if expired > 0:
            await self.point_logs.add(PointLog.record(user.id, PointType.EXPIRE, -expired, 0))
        await self.codes.delete(user.id)  # REQ-35: 탈퇴하면 재설정 코드도 지운다 (회원 행 -> 코드 행 순)
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

    async def list_users(
        self,
        *,
        role: str | None = None,
        status: str | None = None,
        email: str | None = None,
        page: int = DEFAULT_PAGE,
        size: int = DEFAULT_SIZE,
    ) -> UserPage:
        """관리자 회원 목록(읽기 전용, commit 없음). status 필터·응답은 실효 상태."""
        query = UserListQuery.create(role=role, status=status, email=email, page=page, size=size)
        now = self.clock.now()
        users = await self.users.find_all(query, now)
        total = await self.users.count_all(query, now)
        return UserPage(
            items=[UserSummary.from_user(u, now) for u in users],
            page=query.page,
            size=query.size,
            total=total,
        )

    async def purge_expired_tokens(self, now: datetime | None = None) -> int:
        deleted = await self.blacklist.delete_expired(now)
        await self.session.commit()
        return deleted
