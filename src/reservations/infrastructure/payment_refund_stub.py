from reservations.domain.exceptions import RefundNotConnectedError


class NoPaymentRefund:
    """임시 환불 포트 (D-15). 환불·포인트 복구를 할 수 없으므로 호출되면 RefundNotConnectedError(503)를 낸다.

    서비스가 commit 전에 호출하므로 예외가 나면 예약 상태·재고는 그대로다. payments가 C-3·C-4를 적용할 때 교체한다.
    """

    async def refund_for_cancelled_reservation(
        self, target: object, *, reason: str, waive_penalty: bool = False
    ) -> None:
        raise RefundNotConnectedError()
