class StoreNotFoundError(LookupError):
    """404 NOT_FOUND"""

    def __init__(self, message: str = "상점을 찾을 수 없습니다."):
        super().__init__(message)


class NotStoreOwnerError(PermissionError):
    """403 FORBIDDEN"""

    def __init__(self, message: str = "본인 상점만 접근할 수 있습니다."):
        super().__init__(message)


class StoreAlreadyExistsError(ValueError):
    """400 STORE_ALREADY_EXISTS"""

    error_code = "STORE_ALREADY_EXISTS"

    def __init__(self, message: str = "이미 개설된 상점이 있습니다."):
        super().__init__(message)


class AddressNotFoundError(ValueError):
    """400 ADDRESS_NOT_FOUND"""

    error_code = "ADDRESS_NOT_FOUND"

    def __init__(self, message: str = "주소를 찾을 수 없습니다."):
        super().__init__(message)


class StoreDuplicatedError(ValueError):
    """400 STORE_DUPLICATED"""

    error_code = "STORE_DUPLICATED"

    def __init__(self, message: str = "동일한 상점명과 주소의 상점이 이미 존재합니다."):
        super().__init__(message)


class GeocodingUnavailableError(Exception):
    """503 GEOCODING_UNAVAILABLE (ValueError 아님: 사용자 입력 오류가 아니다)"""

    error_code = "GEOCODING_UNAVAILABLE"

    def __init__(
        self,
        message: str = "주소 변환 서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해 주세요.",
    ):
        super().__init__(message)


class StoreAlreadyClosedError(ValueError):
    """400 STORE_ALREADY_CLOSED"""

    error_code = "STORE_ALREADY_CLOSED"

    def __init__(self, message: str = "이미 폐점된 상점입니다."):
        super().__init__(message)


class StoreClosedError(ValueError):
    """400 STORE_CLOSED"""

    error_code = "STORE_CLOSED"

    def __init__(self, message: str = "폐점된 상점입니다."):
        super().__init__(message)


class StoreAlreadySuspendedError(ValueError):
    """400 STORE_ALREADY_SUSPENDED"""

    error_code = "STORE_ALREADY_SUSPENDED"

    def __init__(self, message: str = "이미 정지된 상점입니다."):
        super().__init__(message)


class StoreSuspendedError(ValueError):
    """400 STORE_SUSPENDED"""

    error_code = "STORE_SUSPENDED"

    def __init__(self, message: str = "관리자에 의해 정지된 상점입니다."):
        super().__init__(message)


class StoreHasOpenOffersError(ValueError):
    """400 STORE_HAS_OPEN_OFFERS"""

    error_code = "STORE_HAS_OPEN_OFFERS"

    def __init__(
        self, message: str = "진행 중이거나 예정된 할인 판매가 있어 폐점할 수 없습니다."
    ):
        super().__init__(message)


class StoreHasReservedReservationsError(ValueError):
    """400 STORE_HAS_RESERVED_RESERVATIONS"""

    error_code = "STORE_HAS_RESERVED_RESERVATIONS"

    def __init__(
        self, message: str = "처리되지 않은 예약이 있는 상점은 폐점할 수 없습니다."
    ):
        super().__init__(message)
