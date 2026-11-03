import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-0123456789abcdef")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://lastcall:lastcall_dev@localhost:5433/lastcall"
)
