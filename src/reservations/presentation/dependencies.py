from reservations.application.lifecycle_service import ReservationLifecycleService
from reservations.application.service import ReservationApplicationService


def provide_reservation_service() -> ReservationApplicationService:
    """FastAPI Depends 플레이스홀더 (src/container.py에서 바인딩)"""
    raise NotImplementedError("ReservationApplicationService 의존성이 주입되지 않았습니다.")


def provide_reservation_lifecycle_service() -> ReservationLifecycleService:
    """FastAPI Depends 플레이스홀더 (src/container.py에서 바인딩)"""
    raise NotImplementedError("ReservationLifecycleService 의존성이 주입되지 않았습니다.")
