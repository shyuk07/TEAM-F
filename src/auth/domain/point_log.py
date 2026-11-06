import uuid
from datetime import datetime, timezone
from enum import StrEnum


class PointType(StrEnum):
    EARN = "EARN"
    USE = "USE"
    RESTORE = "RESTORE"
    REVOKE = "REVOKE"
    GRANT = "GRANT"  # 관리자 지급 (D23)
    EXPIRE = "EXPIRE"  # 탈퇴 소멸. 시간 경과 소멸이 아니다 (D-포인트유형소멸)


_POSITIVE_TYPES = (PointType.EARN, PointType.RESTORE, PointType.GRANT)
_NEGATIVE_TYPES = (PointType.USE, PointType.REVOKE, PointType.EXPIRE)


class PointLog:
    """포인트 변경 내역. 생성 후 변경할 수 없다."""

    def __init__(
        self,
        user_id: uuid.UUID,
        amount: int,
        point_type: PointType,
        created_at: datetime | None = None,
        id: uuid.UUID | None = None,
        reason: str | None = None,
        balance_after: int | None = None,
        created_by: uuid.UUID | None = None,
    ):
        if not isinstance(point_type, PointType):
            raise ValueError("point_type은 EARN, USE, RESTORE, REVOKE, GRANT, EXPIRE 중 하나여야 합니다.")
        if amount == 0:
            raise ValueError("포인트 변동량은 0일 수 없습니다.")
        if point_type in _POSITIVE_TYPES and amount < 0:
            raise ValueError("적립·복구·지급 내역의 금액은 양수여야 합니다.")
        if point_type in _NEGATIVE_TYPES and amount > 0:
            raise ValueError("사용·회수·소멸 내역의 금액은 음수여야 합니다.")
        if balance_after is not None and balance_after < 0:
            raise ValueError("변경 후 잔액은 0 이상이어야 합니다.")
        if created_at is not None and created_at.tzinfo is None:
            raise ValueError("created_at은 timezone 정보가 있어야 합니다.")
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "user_id", user_id)
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "point_type", point_type)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "balance_after", balance_after)
        object.__setattr__(self, "created_by", created_by)

    def __setattr__(self, name, value):
        # 영속화 시 id·created_at 채우기만 허용
        if name in ("id", "created_at") and getattr(self, name, None) is None:
            object.__setattr__(self, name, value)
            return
        raise AttributeError("PointLog는 변경할 수 없습니다.")

    @classmethod
    def record(
        cls,
        user_id: uuid.UUID,
        point_type: PointType,
        amount: int,
        balance_after: int,
        reason: str | None = None,
        created_by: uuid.UUID | None = None,
    ) -> "PointLog":
        """신규 기록. balance_after(변경 후 잔액)는 필수다 (D23)."""
        if balance_after is None:
            raise ValueError("변경 후 잔액은 필수입니다.")
        # 유형별 불변식은 새 내역에만 건다. DB 복원(생성자 직접 호출)은 기존 행을 읽을 수 있게 검사하지 않는다.
        if point_type is PointType.EXPIRE and balance_after != 0:
            raise ValueError("소멸 내역의 변경 후 잔액은 0이어야 합니다.")
        if point_type is PointType.GRANT:
            if not reason or created_by is None:
                raise ValueError("지급 내역에는 사유와 처리자가 필요합니다.")
        elif reason is not None or created_by is not None:
            raise ValueError("지급 외 내역에는 사유·처리자를 둘 수 없습니다.")
        return cls(
            user_id,
            amount,
            point_type,
            created_at=datetime.now(timezone.utc),
            reason=reason,
            balance_after=balance_after,
            created_by=created_by,
        )
