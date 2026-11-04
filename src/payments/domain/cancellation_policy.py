"""위약금 계산 정책.

# 미정(D-2): 위약금 계산 담당(payments / reservations)과 정책 코드 위치가 정해지지 않았다.
#            우선 payments가 정책을 가지고 계산한다. 공용화가 필요하면 그때 옮긴다.
# 미정(D-1): 위약금 규칙이 없어 팀 합의대로 항상 0원(FullRefundPolicy)으로 둔다.
"""

from datetime import datetime
from typing import Protocol


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
