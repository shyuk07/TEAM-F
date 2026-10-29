import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


# .env 파일 읽기
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")

# PostgreSQL 비동기 연결
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

# DB 세션 생성
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


# 모든 DB 모델이 공통으로 상속할 클래스
class Base(DeclarativeBase):
    pass


# API에서 DB 세션을 사용할 때 호출
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session