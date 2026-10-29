from fastapi import FastAPI
from sqlalchemy import text

from database import engine


app = FastAPI(title="마감 직전 API")


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