import uuid

from payments.domain.gateway_result import GatewayResult
from payments.domain.payment import Payment
from payments.domain.service import PaymentGateway


class MockPaymentGateway(PaymentGateway):
    """모의 결제 게이트웨이(D-11): 항상 성공한다.

    실패 경로는 테스트에서 fake 게이트웨이를 주입해 검증한다.
    """

    async def charge(self, payment: Payment) -> GatewayResult:
        return GatewayResult(success=True, provider_payment_id="mock_" + uuid.uuid4().hex)
