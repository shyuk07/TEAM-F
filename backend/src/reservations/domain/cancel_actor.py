from enum import StrEnum


class CancelActor(StrEnum):
    """취소 주체(누가 취소를 일으켰는가). 값은 DB CHECK·응답과 같다 (D-40)."""

    CUSTOMER = "CUSTOMER"
    STORE = "STORE"
    SYSTEM = "SYSTEM"
