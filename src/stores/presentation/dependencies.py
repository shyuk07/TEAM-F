from stores.application.service import StoresApplicationService
from stores.domain.repository import StoreRepository


def provide_store_repository() -> StoreRepository:
    """FastAPI Depends 플레이스홀더 (src/container.py에서 바인딩)"""
    raise NotImplementedError("StoreRepository 의존성이 주입되지 않았습니다.")


def provide_stores_service() -> StoresApplicationService:
    """FastAPI Depends 플레이스홀더 (src/container.py에서 바인딩)"""
    raise NotImplementedError("StoresApplicationService 의존성이 주입되지 않았습니다.")
