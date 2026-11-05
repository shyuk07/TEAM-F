import uuid


class NoPickupPendingReservations:
    """PickupPendingPort 임시 구현(미연계): 항상 False.

    reservations 후속 PR이 실제 구현으로 교체한다 (docs/design/stores.md D21).
    """

    async def has_pickup_pending_for_store(self, store_id: uuid.UUID) -> bool:
        return False
