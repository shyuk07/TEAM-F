class ReservationDataInconsistentError(Exception):
    """예약 일괄 취소 중 예약·결제 데이터 불일치가 발견되었다(500 DATA_INCONSISTENT).

    예약 어댑터가 reservations의 DataInconsistentError를 이 예외로 번역한다.
    409/400/403/404 계열을 상속하지 않는다(전역 핸들러에 잡혀 바뀌는 것을 막는다).
    전역 핸들러가 공통 형식의 500으로 바꾼다. 로그·롤백은 예약 서비스가 이미 했다.
    """

    error_code = "DATA_INCONSISTENT"
    default_message = "예약과 결제 상태가 일치하지 않습니다. 관리자에게 문의해 주세요."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)
