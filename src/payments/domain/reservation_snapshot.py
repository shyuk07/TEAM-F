from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from payments.domain.exceptions import (
    PaymentAccessDeniedError,
    PaymentNotRefundableError,
    RefundAccessDeniedError,
    ReservationNotPayableError,
)
from payments.domain.rules import (
    REFUNDABLE_RESERVATION_STATUSES,
    RESERVATION_PAYABLE_STATUS,
)


@dataclass(frozen=True)
class ReservationSnapshot:
    """결제·환불 판단에 필요한 예약 정보만 추린 값 객체."""

    id: UUID
    user_id: UUID
    total_price: int | None
    status: str
    pickup_start: datetime | None = None

    def _is_owner(self, user_id: UUID) -> bool:
        return self.user_id == user_id

    # 결제 요청: 소유 확인(403)과 상태 확인(400)을 분리했다.
    # 서비스가 "소유(403) -> 중복 결제(409) -> 상태(400)" 순서로 부르기 위해서다.
    def ensure_payable_by(self, user_id: UUID) -> None:
        """본인 예약이 아니면 403. (상태는 ensure_payable_state가 확인)"""
        if not self._is_owner(user_id):
            raise PaymentAccessDeniedError("본인 예약만 결제할 수 있습니다.")

    def ensure_payable_state(self) -> None:
        if self.status != RESERVATION_PAYABLE_STATUS:
            raise ReservationNotPayableError()

    def ensure_viewable_by(self, user_id: UUID) -> None:
        """결제 조회는 본인만 (D-4)."""
        if not self._is_owner(user_id):
            raise PaymentAccessDeniedError("결제 정보를 조회할 권한이 없습니다.")

    def ensure_refund_viewable_by(self, user_id: UUID) -> None:
        """환불 조회는 본인만 (D-4)."""
        if not self._is_owner(user_id):
            raise RefundAccessDeniedError("환불 정보를 조회할 권한이 없습니다.")

    def ensure_refundable_by(self, user_id: UUID) -> None:
        """환불 요청은 본인만 (D-3)."""
        if not self._is_owner(user_id):
            raise RefundAccessDeniedError("환불을 처리할 권한이 없습니다.")

    def ensure_refundable_state(self) -> None:
        """예약 상태가 환불 가능 상태가 아니면 400 (D-7). 시간 제한은 없다."""
        if self.status not in REFUNDABLE_RESERVATION_STATUSES:
            raise PaymentNotRefundableError()
