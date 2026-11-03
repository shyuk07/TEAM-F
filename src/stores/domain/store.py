import uuid
from datetime import datetime

from stores.domain.exceptions import NotStoreOwnerError, StoreAlreadyClosedError

# 임시 기본값 (stores.md 12절 D11)
NAME_MAX_LENGTH = 150
ADDRESS_MAX_LENGTH = 500


def _ensure_aware(value: datetime | None, label: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{label}은(는) 시간대 정보가 있어야 합니다.")


class Store:
    def __init__(
        self,
        owner_id: uuid.UUID,
        name: str,
        pickup_address: str,
        latitude: float | None = None,
        longitude: float | None = None,
        created_at: datetime | None = None,
        approval_at: datetime | None = None,
        closed_at: datetime | None = None,
        id: uuid.UUID | None = None,
    ):
        name = (name or "").strip()
        if not 1 <= len(name) <= NAME_MAX_LENGTH:
            raise ValueError(f"상점명은 1자 이상 {NAME_MAX_LENGTH}자 이하여야 합니다.")
        address = (pickup_address or "").strip()
        if not address:
            raise ValueError("주소를 입력해 주세요.")
        if len(address) > ADDRESS_MAX_LENGTH:
            raise ValueError(f"픽업 주소는 {ADDRESS_MAX_LENGTH}자 이하여야 합니다.")
        if (latitude is None) != (longitude is None):
            raise ValueError("좌표가 올바르지 않습니다.")
        if latitude is not None and not (
            -90 <= latitude <= 90 and -180 <= longitude <= 180
        ):
            raise ValueError("좌표가 올바르지 않습니다.")
        _ensure_aware(created_at, "생성 시각")
        _ensure_aware(approval_at, "승인 시각")
        _ensure_aware(closed_at, "폐점 시각")
        if closed_at is not None and (approval_at is None or closed_at < approval_at):
            raise ValueError("폐점 시각은 승인 시각 이후여야 합니다.")
        self.id = id
        self.owner_id = owner_id
        self.name = name
        self.pickup_address = address
        self.latitude = latitude
        self.longitude = longitude
        self.created_at = created_at
        self.approval_at = approval_at
        self.closed_at = closed_at

    @classmethod
    def open(
        cls,
        owner_id: uuid.UUID,
        name: str,
        pickup_address: str,
        now: datetime,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> "Store":
        _ensure_aware(now, "개설 시각")
        if now is None:
            raise ValueError("개설 시각이 필요합니다.")
        return cls(
            owner_id=owner_id,
            name=name,
            pickup_address=pickup_address,
            latitude=latitude,
            longitude=longitude,
            approval_at=now,
        )

    @property
    def is_approved(self) -> bool:
        return self.approval_at is not None

    @property
    def is_closed(self) -> bool:
        return self.closed_at is not None

    def is_owned_by(self, user_id: uuid.UUID) -> bool:
        return self.owner_id == user_id

    def ensure_owned_by(
        self, user_id: uuid.UUID, message: str = "본인 상점만 접근할 수 있습니다."
    ) -> None:
        if not self.is_owned_by(user_id):
            raise NotStoreOwnerError(message)

    def approve(self, now: datetime) -> None:
        _ensure_aware(now, "승인 시각")
        if now is None:
            raise ValueError("승인 시각이 필요합니다.")
        if self.is_approved:
            raise ValueError("이미 승인된 상점입니다.")
        self.approval_at = now

    def close(self, now: datetime) -> None:
        _ensure_aware(now, "폐점 시각")
        if now is None:
            raise ValueError("폐점 시각이 필요합니다.")
        if self.is_closed:
            raise StoreAlreadyClosedError()
        if not self.is_approved:
            raise ValueError("승인되지 않은 상점은 폐점할 수 없습니다.")
        if now < self.approval_at:
            raise ValueError("폐점 시각은 승인 시각 이후여야 합니다.")
        self.closed_at = now
