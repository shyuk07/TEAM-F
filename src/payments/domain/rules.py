"""payments 규칙 상수. 바뀔 수 있는 값은 이 파일 한 곳에 모은다."""

from payments.domain.cancellation_policy import CancellationPolicy, FullRefundPolicy

# 환불 사유 최대 길이 (API 명세, refunds.reason VARCHAR(200))
REFUND_REASON_MAX_LENGTH = 200

# 미정(D-9): 예약 담당 확정 시 변경 (아래 세 값은 임시값)
RESERVATION_PAYABLE_STATUS = "PENDING_PAYMENT"  # 결제 대기
RESERVATION_PAID_STATUS = "RESERVED"  # 결제 완료
REFUNDABLE_RESERVATION_STATUSES = frozenset({RESERVATION_PAID_STATUS})
RESERVATION_CANCELLED_STATUS = "CANCELLED"
# 결제가 PAID인데 예약이 이 상태이면 반대 방향 데이터 불일치다(RD-38, RD-39).
PAID_PAYMENT_CONFLICT_RESERVATION_STATUSES = frozenset(
    {RESERVATION_PAYABLE_STATUS, RESERVATION_CANCELLED_STATUS}
)

# 미정(D-2): 위약금 계산 담당 확정 시 변경. D-1: 우선 0원(팀 합의).
DEFAULT_CANCELLATION_POLICY: CancellationPolicy = FullRefundPolicy()
