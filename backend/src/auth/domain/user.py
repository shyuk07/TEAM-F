import uuid
from datetime import datetime, timezone
from enum import StrEnum

from auth.domain.exceptions import (
    AccountSuspendedError,
    AdminAccountProtectedError,
    AuthenticationError,
    CurrentPasswordMismatchError,
    InvalidCredentialsError,
    InvalidSuspensionEndError,
    OwnerNotApprovedError,
    OwnerNotFoundError,
    OwnerNotPendingError,
    RoleForbiddenError,
    TokenRevokedError,
    UserAlreadySuspendedError,
    UserAlreadyWithdrawnError,
    UserNotSuspendableError,
    UserWithdrawnError,
)
from auth.domain.service import PasswordHasher

REASON_MAX_LENGTH = 500
POINT_MAX_BALANCE = 2_147_483_647  # DB INTEGER 상한 (D24)
PROFILE_TEXT_MAX_LENGTH = 100
SELF_WITHDRAWAL_REASON = "회원 본인 탈퇴"  # 자진 탈퇴 사유 (D-자진탈퇴조정)


class Role(StrEnum):
    CUSTOMER = "CUSTOMER"
    OWNER = "OWNER"  # 상점주 값 이름은 팀 확인 필요 (임시)
    ADMIN = "ADMIN"

    @classmethod
    def for_signup(cls, value: str) -> "Role":
        if value == cls.ADMIN.value:
            raise ValueError("관리자는 회원가입으로 만들 수 없습니다.")
        if value not in (cls.CUSTOMER.value, cls.OWNER.value):
            raise ValueError("role은 CUSTOMER 또는 OWNER여야 합니다.")
        return cls(value)


class UserStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    WITHDRAWN = "WITHDRAWN"


def _normalize_reason(reason: str | None, empty_message: str) -> str:
    """공백 제거 후 비면 empty_message, 500자 초과면 길이 오류 (D27)."""
    normalized = (reason or "").strip()
    if not normalized:
        raise ValueError(empty_message)
    if len(normalized) > REASON_MAX_LENGTH:
        raise ValueError(f"사유는 {REASON_MAX_LENGTH}자 이하여야 합니다.")
    return normalized


def _check_profile_text(value: str, label: str) -> None:
    """이름·전화번호 공통 검사: 공백만이거나 100자 초과면 거부 (D-가입필수)."""
    if not value.strip() or len(value) > PROFILE_TEXT_MAX_LENGTH:
        raise ValueError(f"{label}은 공백이 아닌 {PROFILE_TEXT_MAX_LENGTH}자 이하여야 합니다.")


def _is_filled(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _require_aware(value: datetime | None, name: str) -> None:
    if value is not None and value.tzinfo is None:
        raise ValueError(f"{name}은 timezone 정보가 있어야 합니다.")


class User:
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_BYTES = 72
    POINT_USE_UNIT = 100

    def __init__(
        self,
        email: str,
        password_hash: str,
        role: Role,
        name: str | None = None,
        phone: str | None = None,
        users_point: int = 0,
        created_at: datetime | None = None,
        business_number: str | None = None,
        id: uuid.UUID | None = None,
        status: UserStatus = UserStatus.APPROVED,
        approved_at: datetime | None = None,
        rejected_reason: str | None = None,
        rejected_at: datetime | None = None,
        suspended_reason: str | None = None,
        suspended_at: datetime | None = None,
        suspended_until: datetime | None = None,
        deleted_at: datetime | None = None,
        deleted_reason: str | None = None,
        token_version: int = 0,
        token_keep_jti: str | None = None,
    ):
        email = self.normalize_email(email)
        self._validate_email(email)
        if not password_hash:
            raise ValueError("비밀번호 해시는 비어 있을 수 없습니다.")
        if not isinstance(role, Role):
            raise ValueError("role은 CUSTOMER 또는 OWNER여야 합니다.")
        if name is not None and (not name.strip() or len(name) > 100):
            raise ValueError("이름은 공백이 아닌 100자 이하여야 합니다.")
        if phone is not None and len(phone) > 100:
            raise ValueError("전화번호는 100자 이하여야 합니다.")
        if users_point < 0:
            raise ValueError("포인트는 0 이상이어야 합니다.")
        if token_version < 0:
            raise ValueError("토큰 세대는 0 이상이어야 합니다.")
        if created_at is not None and created_at.tzinfo is None:
            raise ValueError("created_at은 timezone 정보가 있어야 합니다.")
        status = UserStatus(status)
        for field, value in (
            ("approved_at", approved_at),
            ("rejected_at", rejected_at),
            ("suspended_at", suspended_at),
            ("suspended_until", suspended_until),
            ("deleted_at", deleted_at),
        ):
            _require_aware(value, field)
        if status in (UserStatus.PENDING, UserStatus.REJECTED) and role is not Role.OWNER:
            raise ValueError("승인 대기·거부 상태는 상점주만 가질 수 있습니다.")
        if status is UserStatus.REJECTED and (not rejected_reason or rejected_at is None):
            raise ValueError("거부된 계정에는 거부 사유와 시각이 필요합니다.")
        if status is UserStatus.SUSPENDED:
            if not suspended_reason or suspended_at is None:
                raise ValueError("정지된 계정에는 정지 사유와 시각이 필요합니다.")
            if suspended_until is not None and suspended_until <= suspended_at:
                raise ValueError("정지 종료 시각은 정지 시각보다 뒤여야 합니다.")
        if status is UserStatus.WITHDRAWN and deleted_at is None:
            raise ValueError("탈퇴한 계정에는 탈퇴 시각이 필요합니다.")
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.name = name
        self.phone = phone
        self.users_point = users_point
        self.created_at = created_at
        self.business_number = business_number
        self.status = status
        self.approved_at = approved_at
        self.rejected_reason = rejected_reason
        self.rejected_at = rejected_at
        self.suspended_reason = suspended_reason
        self.suspended_at = suspended_at
        self.suspended_until = suspended_until
        self.deleted_at = deleted_at
        self.deleted_reason = deleted_reason
        self.token_version = token_version
        self.token_keep_jti = token_keep_jti

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _validate_email(email: str) -> None:
        msg = "이메일 형식이 올바르지 않습니다."
        if not email or len(email) > 255 or any(c.isspace() for c in email):
            raise ValueError(msg)
        if email.count("@") != 1:
            raise ValueError(msg)
        local, domain = email.split("@")
        if not local or not domain or "." not in domain:
            raise ValueError(msg)

    @staticmethod
    def validate_raw_password(raw: str) -> None:
        if not raw.strip():
            raise ValueError("비밀번호는 공백만으로 만들 수 없습니다.")
        if len(raw) < User.PASSWORD_MIN_LENGTH:
            raise ValueError(f"비밀번호는 {User.PASSWORD_MIN_LENGTH}자 이상이어야 합니다.")
        if len(raw.encode("utf-8")) > User.PASSWORD_MAX_BYTES:
            raise ValueError(f"비밀번호는 {User.PASSWORD_MAX_BYTES}바이트 이하여야 합니다.")

    @classmethod
    def register(
        cls,
        email: str,
        password_hash: str,
        role: str,
        name: str | None = None,
        phone: str | None = None,
        business_number: str | None = None,
    ) -> "User":
        """가입 팩토리. 이름·전화번호는 필수다(DB 복원용 생성자는 기존 회원 보존을 위해 허용)."""
        signup_role = Role.for_signup(role)
        if name is None:
            raise ValueError("이름은 필수입니다.")
        if phone is None:
            raise ValueError("전화번호는 필수입니다.")
        _check_profile_text(name, "이름")
        _check_profile_text(phone, "전화번호")
        return cls(
            email=email,
            password_hash=password_hash,
            role=signup_role,
            name=name,
            phone=phone,
            users_point=0,
            created_at=datetime.now(timezone.utc),
            business_number=business_number,
            # 상점주는 관리자 승인 전까지 PENDING (D4)
            status=UserStatus.PENDING if signup_role is Role.OWNER else UserStatus.APPROVED,
        )

    @classmethod
    def register_admin(
        cls, email: str, password_hash: str, name: str | None = None
    ) -> "User":
        """관리자 계정 생성. 회원가입 경로(Role.for_signup)는 ADMIN을 계속 거부한다."""
        return cls(
            email=email,
            password_hash=password_hash,
            role=Role.ADMIN,
            name=name,
            users_point=0,
            created_at=datetime.now(timezone.utc),
        )

    def has_role(self, *roles: Role) -> bool:
        return self.role in roles

    @property
    def is_owner(self) -> bool:
        return self.role is Role.OWNER

    def require_role(self, *roles: Role) -> None:
        if not self.has_role(*roles):
            raise RoleForbiddenError()

    @staticmethod
    def _require_positive(amount: int) -> None:
        if amount <= 0:
            raise ValueError("포인트는 1 이상이어야 합니다.")

    def _add_points(self, amount: int) -> None:
        """적립·복구·지급 공통: 탈퇴 회원 거부, 잔액 상한 초과 거부(잔액 불변) (D-포인트상한)."""
        if self.status is UserStatus.WITHDRAWN:
            raise UserWithdrawnError()
        if self.users_point + amount > POINT_MAX_BALANCE:
            raise ValueError("포인트 잔액이 한도를 넘습니다.")
        self.users_point += amount

    def earn_points(self, amount: int) -> None:
        self._require_positive(amount)
        self._add_points(amount)

    def use_points(self, amount: int) -> None:
        self._require_positive(amount)
        if amount % self.POINT_USE_UNIT != 0:
            raise ValueError(f"포인트는 {self.POINT_USE_UNIT}P 단위로 사용할 수 있습니다.")
        if amount > self.users_point:
            raise ValueError("포인트 잔액이 부족합니다.")
        self.users_point -= amount

    def restore_points(self, amount: int) -> None:
        self._require_positive(amount)
        self._add_points(amount)

    def revoke_points(self, amount: int) -> int:
        self._require_positive(amount)
        actual = min(amount, self.users_point)
        self.users_point -= actual
        return actual

    # ── 계정 상태 (admin.md 3.1) ──────────────────────────
    def effective_status(self, now: datetime) -> UserStatus:
        """기간이 지난 정지는 APPROVED로 본다(조회 시 계산, D10). until == now는 만료."""
        _require_aware(now, "now")
        if (
            self.status is UserStatus.SUSPENDED
            and self.suspended_until is not None
            and self.suspended_until <= now
        ):
            return UserStatus.APPROVED
        return self.status

    def is_suspended(self, now: datetime) -> bool:
        return self.effective_status(now) is UserStatus.SUSPENDED

    def approve_owner(self, now: datetime) -> None:
        if self.role is not Role.OWNER:
            raise OwnerNotFoundError()
        if self.status is not UserStatus.PENDING:
            raise OwnerNotPendingError()
        _require_aware(now, "now")
        self.status = UserStatus.APPROVED
        self.approved_at = now

    def reject_owner(self, reason: str, now: datetime) -> None:
        normalized = _normalize_reason(reason, "거부 사유를 입력해 주세요.")
        if self.role is not Role.OWNER:
            raise OwnerNotFoundError()
        if self.status is not UserStatus.PENDING:
            raise OwnerNotPendingError()
        _require_aware(now, "now")
        self.status = UserStatus.REJECTED
        self.rejected_reason = normalized
        self.rejected_at = now

    def suspend(self, reason: str, until: datetime | None, now: datetime) -> None:
        normalized = _normalize_reason(reason, "정지 사유를 입력해 주세요.")
        _require_aware(now, "now")
        _require_aware(until, "suspended_until")
        if until is not None and until <= now:
            raise InvalidSuspensionEndError()
        if self.is_suspended(now):
            raise UserAlreadySuspendedError()
        if self.status is UserStatus.WITHDRAWN:
            raise UserWithdrawnError()
        if self.role is Role.ADMIN:
            raise AdminAccountProtectedError("관리자 계정은 정지할 수 없습니다.")
        if self.status in (UserStatus.PENDING, UserStatus.REJECTED):
            raise UserNotSuspendableError()
        self.status = UserStatus.SUSPENDED
        self.suspended_reason = normalized
        self.suspended_at = now
        self.suspended_until = until

    def ensure_withdrawable(self, reason: str) -> str:
        """부수 효과 없음. 정규화된 사유를 돌려준다."""
        normalized = _normalize_reason(reason, "탈퇴 사유를 입력해 주세요.")
        if self.status is UserStatus.WITHDRAWN:
            raise UserAlreadyWithdrawnError()
        if self.role is Role.ADMIN:
            raise AdminAccountProtectedError("관리자 계정은 탈퇴시킬 수 없습니다.")
        return normalized

    def withdraw(self, reason: str, now: datetime) -> int:
        """탈퇴 처리. 남은 포인트를 소멸(잔액 0)시키고 소멸량을 돌려준다 (D-탈퇴포인트소멸).

        거부(관리자·이미 탈퇴·사유 오류)면 잔액은 그대로다. 호출자는 포인트 복구(환불)를 먼저 끝내야 한다.
        """
        normalized = self.ensure_withdrawable(reason)
        _require_aware(now, "now")
        expired = self.users_point
        self.users_point = 0
        self.status = UserStatus.WITHDRAWN
        self.deleted_at = now
        self.deleted_reason = normalized
        return expired

    # ── 프로필·비밀번호·토큰 세대 (D-프로필변경, D-비밀번호변경, D-토큰무효화) ──
    def update_profile(self, name: str | None, phone: str | None) -> None:
        if self.status is UserStatus.WITHDRAWN:
            raise UserWithdrawnError()
        if name is None and phone is None:
            raise ValueError("변경할 항목이 없습니다.")
        if name is not None:
            _check_profile_text(name, "이름")
        if phone is not None:
            _check_profile_text(phone, "전화번호")
        new_name = self.name if name is None else name
        new_phone = self.phone if phone is None else phone
        # REQ-2: 기존 회원도 내 정보를 바꿀 때는 이름·전화번호를 둘 다 채워야 한다(관리자 예외, B-5).
        if self.role is not Role.ADMIN:
            if not _is_filled(new_name):
                raise ValueError("이름은 필수입니다.")
            if not _is_filled(new_phone):
                raise ValueError("전화번호는 필수입니다.")
        self.name = new_name
        self.phone = new_phone

    def ensure_current_password(self, raw: str, hasher: PasswordHasher) -> None:
        if not hasher.verify(raw, self.password_hash):
            raise CurrentPasswordMismatchError()

    def change_password(
        self, current: str, new: str, hasher: PasswordHasher, *, keep_jti: str | None
    ) -> None:
        """현재 비밀번호 확인 후 변경. 변경에 쓴 토큰(keep_jti) 외의 기존 토큰은 무효가 된다."""
        if self.status is UserStatus.WITHDRAWN:
            raise UserWithdrawnError()
        self.ensure_current_password(current, hasher)
        self.validate_raw_password(new)
        self.password_hash = hasher.hash(new)
        self.invalidate_tokens(keep_jti)

    def reset_password(self, new: str, hasher: PasswordHasher) -> None:
        """재설정 코드로 인증된 변경. 모든 기존 토큰이 무효가 된다."""
        if self.status is UserStatus.WITHDRAWN:
            raise UserWithdrawnError()
        self.validate_raw_password(new)
        self.password_hash = hasher.hash(new)
        self.invalidate_tokens(None)

    def invalidate_tokens(self, keep_jti: str | None = None) -> None:
        self.token_version += 1
        self.token_keep_jti = keep_jti

    def ensure_token_current(self, version: int, jti: str) -> None:
        if version == self.token_version:
            return
        if self.token_keep_jti is not None and jti == self.token_keep_jti:
            return
        raise TokenRevokedError("비밀번호가 변경되어 무효가 된 토큰입니다.")

    @property
    def can_reset_password(self) -> bool:
        return self.status is not UserStatus.WITHDRAWN

    def grant_points(self, amount: int, reason: str) -> str:
        """관리자 포인트 지급. 정규화된 사유를 돌려준다 (D24)."""
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 1:
            raise ValueError("지급 포인트는 1 이상이어야 합니다.")
        normalized = _normalize_reason(reason, "지급 사유를 입력해 주세요.")
        self._add_points(amount)
        return normalized

    def ensure_can_login(self, now: datetime) -> None:
        """탈퇴는 존재하지 않는 계정처럼(D9), 정지는 상점주 외 403(D8, D39). PENDING·REJECTED는 허용(D5)."""
        if self.status is UserStatus.WITHDRAWN:
            raise InvalidCredentialsError()
        if self.is_suspended(now) and self.role is not Role.OWNER:
            raise AccountSuspendedError()

    def ensure_can_authenticate(self, now: datetime, *, allow_suspended: bool = False) -> None:
        if self.status is UserStatus.WITHDRAWN:
            raise AuthenticationError("유효하지 않은 토큰입니다.")
        if self.is_suspended(now) and not allow_suspended:
            raise AccountSuspendedError()

    def ensure_approved_owner(self) -> None:
        """상점 개설·폐점 전 확인 (D5). 역할 검사는 require_role이 먼저 한다."""
        if self.role is not Role.OWNER:
            return
        if self.status is UserStatus.PENDING:
            raise OwnerNotApprovedError()
        if self.status is UserStatus.REJECTED:
            raise OwnerNotApprovedError("승인이 거부된 상점주 계정입니다.")
