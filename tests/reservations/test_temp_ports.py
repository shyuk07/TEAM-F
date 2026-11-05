"""임시 포트(재고·환불 미연동 503) 테스트. DB 없음. 포트가 교체되면 이 파일도 함께 삭제한다."""

import inspect

import pytest

from reservations.domain import exceptions as ex
from reservations.domain.exceptions import (
    IntegrationNotReadyError,
    RefundNotConnectedError,
    ReservationConflictError,
    StockNotConnectedError,
)
from reservations.infrastructure.payment_refund_stub import NoPaymentRefund


def test_not_ready_errors_have_codes_and_messages():
    assert StockNotConnectedError().error_code == "STOCK_NOT_CONNECTED"
    assert str(StockNotConnectedError()) == "재고 연동이 아직 준비되지 않아 예약을 생성할 수 없습니다."
    assert RefundNotConnectedError().error_code == "REFUND_NOT_CONNECTED"
    assert str(RefundNotConnectedError()) == "환불 연동이 아직 준비되지 않아 결제된 예약은 취소할 수 없습니다."


@pytest.mark.parametrize("cls", [IntegrationNotReadyError, StockNotConnectedError, RefundNotConnectedError])
def test_not_ready_errors_do_not_hit_global_handlers(cls):
    # 400/403/404/409/500으로 잡히지 않도록 일반 Exception만 상속한다
    assert not issubclass(
        cls, (ValueError, PermissionError, LookupError, RuntimeError, ReservationConflictError)
    )
    assert issubclass(StockNotConnectedError, IntegrationNotReadyError)
    assert issubclass(RefundNotConnectedError, IntegrationNotReadyError)


def test_exceptions_module_is_pure_python():
    assert "fastapi" not in inspect.getsource(ex)


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_no_payment_refund_fails_closed(anyio_backend):
    with pytest.raises(RefundNotConnectedError):
        await NoPaymentRefund().refund_for_cancelled_reservation(
            object(), reason="x", waive_penalty=True
        )
