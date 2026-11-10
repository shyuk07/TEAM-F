"""payments 규칙 상수. 바뀔 수 있는 값은 이 파일 한 곳에 모은다."""

from payments.domain.cancellation_policy import CancellationPolicy, FullRefundPolicy

# 환불 사유 최대 길이 (API 명세, refunds.reason VARCHAR(200))
REFUND_REASON_MAX_LENGTH = 200  # 앞뒤 공백을 뺀 길이 기준(REQ-34)
# 요청 본문 원문의 최대 길이(남용 방지용 임시값). 실제 판정은 앞뒤 공백을 뺀 200자로 도메인이 한다.
REFUND_REASON_RAW_MAX_LENGTH = 1000

# 미정(D-9): 예약 담당 확정 시 변경 (아래 세 값은 임시값)
RESERVATION_PAYABLE_STATUS = "PENDING_PAYMENT"  # 결제 대기
RESERVATION_PAID_STATUS = "RESERVED"  # 결제 완료
REFUNDABLE_RESERVATION_STATUSES = frozenset({RESERVATION_PAID_STATUS})
RESERVATION_CANCELLED_STATUS = "CANCELLED"
# 결제가 PAID인데 예약이 이 상태이면 반대 방향 데이터 불일치다(RD-38, RD-39).
PAID_PAYMENT_CONFLICT_RESERVATION_STATUSES = frozenset(
    {RESERVATION_PAYABLE_STATUS, RESERVATION_CANCELLED_STATUS}
)

# REQ-46: 결제 금액(포인트 사용분 제외)의 1%를 적립한다. 사용 단위(100P)는 auth User.POINT_USE_UNIT이 정본이다.
POINT_EARN_PERCENT = 1

# 미정(D-2): 위약금 계산 담당 확정 시 변경. D-1: 우선 0원(팀 합의).
DEFAULT_CANCELLATION_POLICY: CancellationPolicy = FullRefundPolicy()
