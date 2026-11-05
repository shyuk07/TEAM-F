from payments.application.service import PaymentApplicationService


def provide_payment_service() -> PaymentApplicationService:
    """FastAPI Depends 플레이스홀더 (src/container.py에서 바인딩)"""
    raise NotImplementedError("PaymentApplicationService 의존성이 주입되지 않았습니다.")
