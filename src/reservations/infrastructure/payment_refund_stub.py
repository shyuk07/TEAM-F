class NoPaymentRefund:
    """임시 환불 포트 (D-15). 환불·포인트 복구를 하지 않고 즉시 반환한다.

    결제된(RESERVED) 예약 취소 시 환불이 일어나지 않는다. payments가 C-3·C-4를 적용할 때 교체한다.
    """

    async def refund_for_cancelled_reservation(
        self, target: object, *, reason: str, waive_penalty: bool = False
    ) -> None:
        return None
