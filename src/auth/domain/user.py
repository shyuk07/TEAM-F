import uuid
from datetime import datetime, timezone
from enum import StrEnum

from auth.domain.exceptions import RoleForbiddenError


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
        if created_at is not None and created_at.tzinfo is None:
            raise ValueError("created_at은 timezone 정보가 있어야 합니다.")
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.name = name
        self.phone = phone
        self.users_point = users_point
        self.created_at = created_at
        self.business_number = business_number

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
        return cls(
            email=email,
            password_hash=password_hash,
            role=Role.for_signup(role),
            name=name,
            phone=phone,
            users_point=0,
            created_at=datetime.now(timezone.utc),
            business_number=business_number,
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

    def require_role(self, *roles: Role) -> None:
        if not self.has_role(*roles):
            raise RoleForbiddenError()

    @staticmethod
    def _require_positive(amount: int) -> None:
        if amount <= 0:
            raise ValueError("포인트는 1 이상이어야 합니다.")

    def earn_points(self, amount: int) -> None:
        self._require_positive(amount)
        self.users_point += amount

    def use_points(self, amount: int) -> None:
        self._require_positive(amount)
        if amount % self.POINT_USE_UNIT != 0:
            raise ValueError(f"포인트는 {self.POINT_USE_UNIT}P 단위로 사용할 수 있습니다.")
        if amount > self.users_point:
            raise ValueError("포인트 잔액이 부족합니다.")
        self.users_point -= amount

    def restore_points(self, amount: int) -> None:
        self._require_positive(amount)
        self.users_point += amount

    def revoke_points(self, amount: int) -> int:
        self._require_positive(amount)
        actual = min(amount, self.users_point)
        self.users_point -= actual
        return actual
