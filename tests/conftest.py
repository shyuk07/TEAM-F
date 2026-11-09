import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-0123456789abcdef")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://lastcall:lastcall_dev@localhost:5433/lastcall"
)

import httpx  # noqa: E402
import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from auth.infrastructure import models as _auth_models  # noqa: E402,F401
import container  # noqa: E402
from auth.infrastructure.reset_notifier import LoggingPasswordResetNotifier  # noqa: E402
from container import create_geocoder  # noqa: E402
from database import Base, get_db  # noqa: E402
from main import app  # noqa: E402
from tests.fakes import FakeGeocoder  # noqa: E402


@pytest.fixture(autouse=True)
def _no_real_mail(monkeypatch):
    """개발자 .env에 SMTP 설정이 있어도 테스트가 실제 메일을 보내지 않게 로그 전달로 되돌린다."""
    monkeypatch.setattr(container, "_reset_notifier", LoggingPasswordResetNotifier())


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _test_url():
    explicit = os.getenv("TEST_DATABASE_URL")
    if explicit:
        return explicit
    return make_url(os.environ["DATABASE_URL"]).set(database="lastcall_test").render_as_string(
        hide_password=False
    )


@pytest.fixture
async def session_factory():
    url = make_url(_test_url())
    try:
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            async with engine.connect():
                pass
        except Exception:
            # DB가 없으면 생성 시도
            admin = create_async_engine(
                url.set(database="postgres"), poolclass=NullPool, isolation_level="AUTOCOMMIT"
            )
            async with admin.connect() as conn:
                await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
            await admin.dispose()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as err:  # 연결 불가 시에만 skip
        pytest.skip(f"테스트 DB에 연결할 수 없습니다: {err!r}")
    yield async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(session_factory):
    async def override():
        async with session_factory() as session:
            yield session

    geocoder = FakeGeocoder()  # 네트워크 금지: 실제 KakaoGeocoder를 쓰지 않는다 (stores.md 14.8)
    app.dependency_overrides[get_db] = override
    app.dependency_overrides[create_geocoder] = lambda: geocoder
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        c.session_factory = session_factory
        c.geocoder = geocoder
        yield c
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(create_geocoder, None)
