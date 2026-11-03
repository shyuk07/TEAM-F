from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

# 모든 models.py는 lifespan(create_all)보다 먼저 import해야 테이블이 만들어진다.
from auth.infrastructure import models as auth_models  # noqa: F401
from auth.infrastructure.settings import get_auth_settings
from auth.presentation.router import router as auth_router
from container import wire_dependencies
from database import Base, engine
from error_handlers import register_exception_handlers

# FK 대상(users)이 먼저 등록돼야 하므로 auth → stores 순서를 유지한다.
from stores.infrastructure import models as stores_models  # noqa: F401
from stores.presentation.router import router as stores_router

# catalog의 FK 대상(stores, users)이 먼저 등록돼야 하므로 stores 뒤에 둔다.
from catalog.infrastructure import models as catalog_models  # noqa: F401
from catalog.presentation.router import router as catalog_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # JWT 설정 오류를 첫 로그인 때 500이 아니라 서버 시작 시점에 드러낸다.
    get_auth_settings()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="마감 직전 API", lifespan=lifespan)

register_exception_handlers(app)
wire_dependencies(app)  # 라우터 등록 전에
app.include_router(auth_router)
app.include_router(stores_router)
app.include_router(catalog_router)


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
