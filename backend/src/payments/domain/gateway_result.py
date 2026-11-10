from dataclasses import dataclass


@dataclass(frozen=True)
class GatewayResult:
    """결제 게이트웨이(PG)의 처리 결과."""

    success: bool
    provider_payment_id: str | None = None
    failure_response: dict | None = None
