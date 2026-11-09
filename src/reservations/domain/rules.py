"""바뀔 수 있는 임시 기본값 모음 (설계 1.7절, Q-1~Q-16). 확정이 아니라 제안값이다."""

from datetime import timedelta

from reservations.domain.cancel_actor import CancelActor

PAYMENT_TIMEOUT: timedelta | None = None  # Q-2: 결제 제한 시간 없음
PICKUP_WINDOW_ENFORCED = False  # Q-5: 픽업 시간 밖에서도 처리 가능
ALLOW_OWNER_SELF_RESERVATION = True  # Q-3: 상점주 자기 매장 예약 허용
PICKUP_CODE_CASE_SENSITIVE = False  # Q-4
PICKUP_CODE_LETTERS = 1  # Q-4: 예) A12345
PICKUP_CODE_DIGITS = 5
CUSTOMER_CANCEL_REASON = "고객 요청 취소"  # Q-7
WITHDRAWAL_CANCEL_REASON = "회원 탈퇴"  # Q-A6: 호출자가 사유를 넘기면 그 값을 쓴다
MAX_RESERVATION_QUANTITY = 5  # 요구조건 R-REQ1: 예약 1건 수량 1~5 (확정, 2026-11-06)
LIST_DEFAULT_SIZE = 20  # Q-9
LIST_MAX_SIZE = 100

# 취소 주체 (설계 16.2, D-41/D-42): 타 모듈 포트 시그니처를 바꾸지 않고 진입점별로 정한다
REFUND_REQUEST_CANCEL_ACTOR = CancelActor.CUSTOMER  # P2 환불 요청으로 인한 취소
OFFER_CLOSE_CANCEL_ACTOR = CancelActor.STORE  # P3 점주 판매 중단
WITHDRAWAL_CANCEL_ACTOR = CancelActor.SYSTEM  # P4·P5 회원 탈퇴(자진·강제)
