from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

# 모든 models.py는 lifespan(create_all)보다 먼저 import해야 테이블이 만들어진다.
from auth.infrastructure import models as auth_models  # noqa: F401
from auth.infrastructure.settings import get_admin_seed_settings, get_auth_settings
from auth.presentation.router import router as auth_router
from container import build_auth_service, wire_dependencies
from database import AsyncSessionLocal, Base, engine
from error_handlers import register_exception_handlers
from payments.infrastructure import models as payments_models  # noqa: F401
from payments.presentation.router import router as payments_router

# FK 대상(users)이 먼저 등록돼야 하므로 auth → stores 순서를 유지한다.
from stores.infrastructure import models as stores_models  # noqa: F401
from stores.presentation.router import router as stores_router

# catalog의 FK 대상(stores, users)이 먼저 등록돼야 하므로 stores 뒤에 둔다.
from catalog.infrastructure import models as catalog_models  # noqa: F401
from catalog.presentation.router import router as catalog_router


async def seed_admin(session_factory=AsyncSessionLocal) -> bool:
    """ADMIN_EMAIL/ADMIN_PASSWORD가 설정돼 있으면 관리자를 보장한다. 새로 만들었으면 True."""
    settings = get_admin_seed_settings()
    if settings is None:
        return False
    async with session_factory() as session:
        _, created = await build_auth_service(session).ensure_admin(
            settings.email, settings.password
        )
    return created


@asynccontextmanager
async def lifespan(app: FastAPI):
    # JWT 설정 오류를 첫 로그인 때 500이 아니라 서버 시작 시점에 드러낸다.
    get_auth_settings()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await seed_admin()  # 설정 오류·이메일 충돌은 시작을 중단시킨다
    yield
    await engine.dispose()


app = FastAPI(title="마감 직전 API", lifespan=lifespan)

register_exception_handlers(app)
wire_dependencies(app)  # 라우터 등록 전에
app.include_router(auth_router)
app.include_router(stores_router)
app.include_router(catalog_router)

app.include_router(payments_router)


@app.get("/")
def home():
    return {"message": "마감 직전 서버 실행 성공!"}


@app.get("/health/db")
async def check_database():
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected"
    }
