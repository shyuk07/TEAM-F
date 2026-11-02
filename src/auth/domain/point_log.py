import uuid
from datetime import datetime, timezone
from enum import StrEnum


class PointType(StrEnum):
    EARN = "EARN"
    USE = "USE"
    RESTORE = "RESTORE"
    REVOKE = "REVOKE"


class PointLog:
    """포인트 변경 내역. 생성 후 변경할 수 없다."""

    def __init__(
        self,
        user_id: uuid.UUID,
        amount: int,
        point_type: PointType,
        created_at: datetime | None = None,
        id: uuid.UUID | None = None,
    ):
        if not isinstance(point_type, PointType):
            raise ValueError("point_type은 EARN, USE, RESTORE, REVOKE 중 하나여야 합니다.")
        if amount == 0:
            raise ValueError("포인트 변동량은 0일 수 없습니다.")
        if point_type in (PointType.EARN, PointType.RESTORE) and amount < 0:
            raise ValueError("적립·복구 내역의 금액은 양수여야 합니다.")
        if point_type in (PointType.USE, PointType.REVOKE) and amount > 0:
            raise ValueError("사용·회수 내역의 금액은 음수여야 합니다.")
        if created_at is not None and created_at.tzinfo is None:
            raise ValueError("created_at은 timezone 정보가 있어야 합니다.")
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "user_id", user_id)
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "point_type", point_type)
        object.__setattr__(self, "created_at", created_at)

    def __setattr__(self, name, value):
        # 영속화 시 id·created_at 채우기만 허용
        if name in ("id", "created_at") and getattr(self, name, None) is None:
            object.__setattr__(self, name, value)
            return
        raise AttributeError("PointLog는 변경할 수 없습니다.")

    @classmethod
    def record(cls, user_id: uuid.UUID, point_type: PointType, amount: int) -> "PointLog":
        return cls(user_id, amount, point_type, created_at=datetime.now(timezone.utc))
