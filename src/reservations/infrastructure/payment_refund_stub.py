import uuid

from reservations.domain.exceptions import RefundNotConnectedError


class NoPaymentRefund:
    """임시 환불 포트 (D-15). 환불·포인트 복구를 할 수 없으므로 호출되면 RefundNotConnectedError(503)를 낸다.

    서비스가 commit 전에 호출하므로 예외가 나면 예약 상태·재고는 그대로다. payments가 C-3·C-4를 적용할 때 교체한다.
    """

    async def refund_for_cancelled_reservation(
        self, target: object, *, reason: str, waive_penalty: bool = False
    ) -> None:
        raise RefundNotConnectedError()

    async def ensure_no_paid_payment(self, reservation_id: uuid.UUID) -> None:
        """결제 모듈이 연결되지 않아 확인할 수 없다. 미결제 취소(200)를 막지 않도록 아무것도 하지 않는다.

        근거: 결제(PAID)는 결제 모듈만 만들 수 있고, 결제 모듈이 연결되지 않은 앱에는 PAID 결제가 있을 수 없다.
        여기서 503을 내면 결제와 무관한 미결제 취소까지 막힌다. 결제된 예약(RESERVED)의 환불은 위 메서드가 계속 503으로 막는다.
        실제 앱에서는 wire_dependencies가 결제 어댑터로 교체하며, tests/reservations/test_wiring.py가 확인한다.
        """
        return None
