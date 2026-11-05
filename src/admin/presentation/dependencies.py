from admin.application.service import AdminApplicationService


def provide_admin_service() -> AdminApplicationService:
    """FastAPI Depends 플레이스홀더 (src/container.py에서 바인딩)"""
    raise NotImplementedError("AdminApplicationService 의존성이 주입되지 않았습니다.")
