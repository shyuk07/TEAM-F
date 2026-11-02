from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

# 모든 models.py는 lifespan(create_all)보다 먼저 import해야 테이블이 만들어진다.
from auth.infrastructure import models as auth_models  # noqa: F401
from auth.presentation.router import router as auth_router
from database import Base, engine
from error_handlers import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="마감 직전 API", lifespan=lifespan)

register_exception_handlers(app)
app.include_router(auth_router)


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
