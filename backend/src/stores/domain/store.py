import unicodedata
import uuid
from datetime import datetime

from enum import StrEnum

from stores.domain.coordinates import Coordinates
from stores.domain.exceptions import (
    NotStoreOwnerError,
    StoreAlreadyClosedError,
    StoreAlreadyExistsError,
    StoreAlreadySuspendedError,
    StoreClosedError,
    StoreDuplicatedError,
    StoreHasOpenOffersError,
    StoreHasReservedReservationsError,
    StoreSuspendedError,
)

# 임시 기본값 (stores.md 12절 D11)
NAME_MAX_LENGTH = 150
ADDRESS_MAX_LENGTH = 500
REASON_MAX_LENGTH = 500


class StoreStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


def _normalize_text(value: str | None) -> str:
    """NFC 정규화 + 앞뒤 공백 제거 + 내부 연속 공백(전각 포함)을 한 칸으로 (D32)"""
    return " ".join(unicodedata.normalize("NFC", value or "").split())


def _normalize_reason(reason: str | None, empty_message: str) -> str:
    text = (reason or "").strip()
    if not text:
        raise ValueError(empty_message)
    if len(text) > REASON_MAX_LENGTH:
        raise ValueError(f"사유는 {REASON_MAX_LENGTH}자 이하여야 합니다.")
    return text


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
        suspended_reason: str | None = None,
        suspended_at: datetime | None = None,
        closed_reason: str | None = None,
    ):
        address = self.normalize_address(pickup_address)
        name = self.normalize_name(name)
        if (latitude is None) != (longitude is None):
            raise ValueError("좌표가 올바르지 않습니다.")
        if latitude is not None:
            Coordinates(latitude, longitude)
        _ensure_aware(created_at, "생성 시각")
        _ensure_aware(approval_at, "승인 시각")
        _ensure_aware(closed_at, "폐점 시각")
        if closed_at is not None and (approval_at is None or closed_at < approval_at):
            raise ValueError("폐점 시각은 승인 시각 이후여야 합니다.")
        _ensure_aware(suspended_at, "정지 시각")
        if (suspended_reason is None) != (suspended_at is None):
            raise ValueError("정지 사유와 정지 시각은 함께 있어야 합니다.")
        if closed_reason is not None and closed_at is None:
            raise ValueError("폐점 사유는 폐점된 상점에만 있을 수 있습니다.")
        self.id = id
        self.owner_id = owner_id
        self.name = name
        self.pickup_address = address
        self.latitude = latitude
        self.longitude = longitude
        self.created_at = created_at
        self.approval_at = approval_at
        self.closed_at = closed_at
        self.suspended_reason = suspended_reason
        self.suspended_at = suspended_at
        self.closed_reason = closed_reason

    @staticmethod
    def normalize_address(raw: str | None) -> str:
        text = _normalize_text(raw)
        if not text:
            raise ValueError("주소를 입력해 주세요.")
        if len(text) > ADDRESS_MAX_LENGTH:
            raise ValueError(f"픽업 주소는 {ADDRESS_MAX_LENGTH}자 이하여야 합니다.")
        return text

    @staticmethod
    def normalize_name(raw: str | None) -> str:
        text = _normalize_text(raw)
        if not 1 <= len(text) <= NAME_MAX_LENGTH:
            raise ValueError(f"상점명은 1자 이상 {NAME_MAX_LENGTH}자 이하여야 합니다.")
        return text

    @staticmethod
    def ensure_can_open(*, owner_already_has_store: bool, duplicate_exists: bool) -> None:
        if owner_already_has_store:
            raise StoreAlreadyExistsError()
        if duplicate_exists:
            raise StoreDuplicatedError()

    @classmethod
    def open(
        cls,
        owner_id: uuid.UUID,
        name: str,
        pickup_address: str,
        now: datetime,
        coordinates: Coordinates,
    ) -> "Store":
        _ensure_aware(now, "개설 시각")
        if now is None:
            raise ValueError("개설 시각이 필요합니다.")
        return cls(
            owner_id=owner_id,
            name=name,
            pickup_address=pickup_address,
            latitude=coordinates.latitude,
            longitude=coordinates.longitude,
            approval_at=now,
        )

    @property
    def is_approved(self) -> bool:
        return self.approval_at is not None

    @property
    def is_closed(self) -> bool:
        return self.closed_at is not None

    @property
    def is_suspended(self) -> bool:
        return self.suspended_at is not None

    @property
    def status(self) -> StoreStatus:
        if self.closed_at is not None:
            return StoreStatus.CLOSED
        if self.suspended_at is not None:
            return StoreStatus.SUSPENDED
        return StoreStatus.ACTIVE

    @property
    def is_publicly_visible(self) -> bool:
        """공개 검색 노출 조건 (catalog D61). 레포지토리 find_visible_near의 SQL 조건과 같아야 한다."""
        return self.is_approved and self.status == StoreStatus.ACTIVE

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

    def close(
        self,
        now: datetime,
        *,
        has_open_offers: bool = False,
        has_pickup_pending: bool = False,
    ) -> None:
        _ensure_aware(now, "폐점 시각")
        if now is None:
            raise ValueError("폐점 시각이 필요합니다.")
        if self.is_closed:
            raise StoreAlreadyClosedError()
        if self.is_suspended:
            raise StoreSuspendedError()
        if has_open_offers:
            raise StoreHasOpenOffersError()
        if has_pickup_pending:
            raise StoreHasReservedReservationsError(
                "픽업 대기 중인 예약이 있어 폐점할 수 없습니다."
            )
        self._close(now)

    def _close(self, now: datetime, reason: str | None = None) -> None:
        if not self.is_approved:
            raise ValueError("승인되지 않은 상점은 폐점할 수 없습니다.")
        if now < self.approval_at:
            raise ValueError("폐점 시각은 승인 시각 이후여야 합니다.")
        self.closed_at = now
        self.closed_reason = reason

    def suspend(self, reason: str, now: datetime) -> None:
        text = _normalize_reason(reason, "정지 사유를 입력해 주세요.")
        _ensure_aware(now, "정지 시각")
        if now is None:
            raise ValueError("정지 시각이 필요합니다.")
        if self.is_closed:
            raise StoreClosedError()
        if self.is_suspended:
            raise StoreAlreadySuspendedError()
        self.suspended_reason = text
        self.suspended_at = now

    def suspend_if_active(self, reason: str, now: datetime) -> bool:
        text = _normalize_reason(reason, "정지 사유를 입력해 주세요.")
        _ensure_aware(now, "정지 시각")
        if now is None:
            raise ValueError("정지 시각이 필요합니다.")
        if self.status != StoreStatus.ACTIVE:
            return False
        self.suspend(text, now)
        return True

    def ensure_force_closable(self, reason: str) -> None:
        _normalize_reason(reason, "폐점 사유를 입력해 주세요.")
        if self.is_closed:
            raise StoreAlreadyClosedError()

    def force_close(
        self, reason: str, now: datetime, has_reserved_reservations: bool
    ) -> None:
        text = _normalize_reason(reason, "폐점 사유를 입력해 주세요.")
        if self.is_closed:
            raise StoreAlreadyClosedError()
        _ensure_aware(now, "폐점 시각")
        if now is None:
            raise ValueError("폐점 시각이 필요합니다.")
        if has_reserved_reservations:
            raise StoreHasReservedReservationsError()
        self._close(now, text)
