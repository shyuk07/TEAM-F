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


class StoreAlreadyClosedError(ValueError):
    """400 STORE_ALREADY_CLOSED"""

    error_code = "STORE_ALREADY_CLOSED"

    def __init__(self, message: str = "이미 폐점된 상점입니다."):
        super().__init__(message)
