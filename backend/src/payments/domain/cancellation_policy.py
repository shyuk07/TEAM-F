"""위약금 계산 정책.

# 미정(D-2): 위약금 계산 담당(payments / reservations)과 정책 코드 위치가 정해지지 않았다.
#            우선 payments가 정책을 가지고 계산한다. 공용화가 필요하면 그때 옮긴다.
# 미정(D-1): 위약금 규칙이 없어 팀 합의대로 항상 0원(FullRefundPolicy)으로 둔다.
"""

from datetime import datetime
from typing import Protocol

from payments.domain.exceptions import RefundDeadlinePassedError


class CancellationPolicy(Protocol):
    def penalty(self, paid_amount: int, pickup_start: datetime | None, now: datetime) -> int:
        """위약금을 돌려준다. 결과는 0 <= 위약금 <= paid_amount 여야 한다.

        범위를 벗어나면 Payment.refund()가 ValueError로 막는다.
        """
        ...


class FullRefundPolicy:
    """임시 기본 정책: 위약금 항상 0원(전액 환불)."""

    def penalty(self, paid_amount: int, pickup_start: datetime | None, now: datetime) -> int:
        return 0


def ensure_before_refund_deadline(cancellable_until: datetime | None, now: datetime) -> None:
    """결제 완료 예약의 고객 취소·환불은 취소 가능 시각(같은 순간 포함)까지만 된다(payments REQ-6, 사용자 결정 2026-11-06).

    마감 시각은 Catalog 취소 정책(pickup_start - CANCEL_LEAD_TIME)으로 계산된 값을 받는다. 결제 쪽에서 따로 계산하지 않는다.
    값이 없으면 판단할 수 없으므로 막는다(fail-closed). 일괄 취소(상점주 사유·탈퇴)는 이 검사를 부르지 않는다.
    """
    if cancellable_until is None:
        raise RuntimeError("취소 가능 시각 정보가 없어 환불 가능 여부를 판단할 수 없습니다.")
    if now > cancellable_until:
        raise RefundDeadlinePassedError()
