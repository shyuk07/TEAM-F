"""catalog 도메인 예외. HTTP 변환은 src/error_handlers.py가 한다 (R6)."""


class ProductNotFoundError(LookupError):
    """404 NOT_FOUND"""

    def __init__(self, message: str = "상품을 찾을 수 없습니다."):
        super().__init__(message)


class OfferNotFoundError(LookupError):
    """404 NOT_FOUND"""

    def __init__(self, message: str = "할인 판매를 찾을 수 없습니다."):
        super().__init__(message)


class StoreNotFoundError(LookupError):
    """404 NOT_FOUND"""

    def __init__(self, message: str = "상점을 찾을 수 없습니다."):
        super().__init__(message)


class NotStoreOwnerError(PermissionError):
    """403 FORBIDDEN (메시지는 EP별로 전달)"""

    def __init__(self, message: str = "본인 상점만 이용할 수 있습니다."):
        super().__init__(message)


class StoreNotApprovedError(ValueError):
    error_code = "STORE_NOT_APPROVED"


class StoreClosedError(ValueError):
    error_code = "STORE_CLOSED"


class ProductInactiveError(ValueError):
    error_code = "PRODUCT_INACTIVE"


class OpenOfferExistsError(ValueError):
    error_code = "OFFER_ALREADY_OPEN"


class ProductAlreadyInactiveError(ValueError):
    error_code = "PRODUCT_ALREADY_INACTIVE"


class ProductHasOpenOfferError(ValueError):
    error_code = "PRODUCT_HAS_OPEN_OFFER"


class OfferClosedError(ValueError):
    error_code = "OFFER_CLOSED"


class InsufficientStockError(ValueError):
    error_code = "INSUFFICIENT_STOCK"
