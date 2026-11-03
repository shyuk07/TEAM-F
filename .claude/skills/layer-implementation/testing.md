# 테스트 작성 가이드

정답 예시는 `tests/conftest.py`, `tests/auth/*.py`, `tests/test_error_handlers.py`입니다. 새 모듈 테스트는 `tests/<모듈>/`에 `__init__.py`와 함께 둡니다.

## 설정 (이미 되어 있음)
- `pyproject.toml`의 `[tool.pytest.ini_options]`: `pythonpath = ["src"]`(그래서 `from catalog.domain...`으로 import), `testpaths = ["tests"]`, 마커 `db`(실제 PostgreSQL 필요).
- `tests/conftest.py`: `JWT_SECRET_KEY`, `DATABASE_URL`을 `os.environ.setdefault`로 채웁니다. `database.py`가 import 시점에 `DATABASE_URL`이 없으면 `RuntimeError`를 내므로, 환경변수는 다른 import보다 먼저 정해져야 합니다.
- 테스트 의존성은 dev 그룹(`httpx`, `pytest`)입니다. 추가할 때는 `uv add --dev <패키지>`.

## 비동기 테스트는 anyio
`pytest-asyncio`는 설치되어 있지 않습니다. anyio의 pytest 플러그인(httpx 의존성으로 설치됨)을 씁니다. 기존 테스트처럼 파일마다 `anyio_backend` fixture로 백엔드를 asyncio에 고정합니다.

```python
import pytest

pytestmark = pytest.mark.anyio          # DB 테스트는 [pytest.mark.db, pytest.mark.anyio]


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_something():
    ...
```
`@pytest.mark.asyncio`를 붙이면 "async def functions are not natively supported"로 실패합니다.

## 테스트 종류
| 종류 | 예시 파일 | DB | 무엇을 |
| --- | --- | --- | --- |
| 도메인 단위 | `tests/auth/test_domain.py` | X | 생성 검증, 상태 전이, 예외 클래스와 메시지. 동기 함수로 충분 |
| 서비스 (fake 주입) | `tests/auth/test_service.py` | X | 흐름, `commit` 횟수, 예외 종류, `commit=False` 동작 |
| 에러 형식 | `tests/test_error_handlers.py` | X | 작은 `FastAPI()` 앱에 `register_exception_handlers`를 붙여 상태 코드·`error_code` 확인 |
| API + DB | `tests/auth/test_api_db.py` | O | 실제 라우터·핸들러·DB를 거친 응답, 동시성(`FOR UPDATE`) |

도메인 규칙 단위 테스트를 먼저 쓰고, 엔드포인트마다 성공 1건과 대표 에러(400/401/403/404/409) 1건씩을 API 테스트로 확인합니다.

## 서비스 테스트: fake 레포지토리 주입
서비스가 레포지토리를 키워드 인자로 받게 만들어 두고(구현 규칙 4절), 테스트에서 메모리 fake를 넣습니다. 세션은 `commit`/`rollback` 횟수만 세는 fake로 충분합니다.

```python
import uuid

import pytest

from catalog.application.service import CatalogApplicationService
from catalog.domain.discount_offer import DiscountOffer, OfferStatus
from catalog.domain.exceptions import OfferNotFoundError, OutOfStockError

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeSession:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


class FakeOffers:
    def __init__(self):
        self.items = {}

    async def find_by_id(self, offer_id, for_update=False):
        return self.items.get(offer_id)

    async def save(self, offer):
        if offer.id is None:
            offer.id = uuid.uuid4()
        self.items[offer.id] = offer
        return offer


def build():
    db, offers = FakeSession(), FakeOffers()
    return CatalogApplicationService(db, offers=offers), db, offers


async def test_deduct_without_commit():
    svc, db, offers = build()
    offer = await offers.save(DiscountOffer(uuid.uuid4(), 1000, 3, status=OfferStatus.ON_SALE))
    await svc.deduct_stock(offer.id, 2, commit=False)
    assert offer.remaining_stock == 1 and db.commits == 0


async def test_errors_are_domain_exceptions():
    svc, _, offers = build()
    with pytest.raises(OfferNotFoundError):
        await svc.get_offer(uuid.uuid4())
    offer = await offers.save(DiscountOffer(uuid.uuid4(), 1000, 1, status=OfferStatus.ON_SALE))
    with pytest.raises(OutOfStockError):
        await svc.deduct_stock(offer.id, 5)
```
`pytest.raises(LookupError)`보다 전용 예외 클래스로 확인해야 `KeyError` 같은 버그가 통과로 보이지 않습니다.

## API + DB 테스트
### 테스트 DB 준비
개발 DB(`lastcall`)를 지우지 않도록 별도 DB `lastcall_test`를 씁니다. fixture가 매 테스트마다 `drop_all`/`create_all`을 합니다.

```bash
docker compose up -d
docker exec team-f-postgres-1 createdb -U lastcall lastcall_test   # 처음 한 번
```
auth의 fixture는 DB가 없으면 `CREATE DATABASE`를 시도하지만, 아래 패턴은 DB가 없으면 오류(`InvalidCatalogNameError`)로 멈추므로 직접 만들어 둡니다. 다른 DB를 쓰려면 `TEST_DATABASE_URL`을 지정합니다.

### 함정: `str(url)`은 비밀번호를 가린다
SQLAlchemy `URL`을 `str()`로 바꾸면 비밀번호가 `***`로 마스킹되어, 그 문자열로 만든 엔진은 인증에 실패합니다. 문자열이 필요하면 `render_as_string(hide_password=False)`를 쓰고, 가능하면 `URL` 객체를 그대로 `create_async_engine`에 넘깁니다.

```python
from sqlalchemy.engine import make_url

url = make_url(os.environ["DATABASE_URL"]).set(database="lastcall_test")
str(url)                                       # postgresql+asyncpg://lastcall:***@...  (연결 실패)
url.render_as_string(hide_password=False)      # postgresql+asyncpg://lastcall:lastcall_dev@...
```

### 함정: 모든 실패를 skip하면 설정 오류가 숨는다
DB 연결 fixture에서 `except Exception: pytest.skip(...)`을 하면 비밀번호 오류, 잘못된 URL, `create_all` 실패(모델·FK 오류)까지 전부 skip이 되어 `pytest`가 "통과"로 보입니다. 실제로 DB 테스트 22개가 조용히 skip된 적이 있습니다.
- skip은 **서버에 닿지 못한 경우**(`OSError`, 예: `ConnectionRefusedError`)로 좁힙니다. 인증 실패(`asyncpg.InvalidPasswordError`)나 `create_all` 오류는 `OSError`가 아니므로 실패로 드러나야 합니다.
- 실행할 때 항상 `-rs`로 skip 이유를 봅니다. DB 테스트가 있는데 skip이면 완료가 아닙니다.

### fixture 패턴
공용 fixture(`anyio_backend`, `session_factory`, `client`)는 `tests/conftest.py`에, 헬퍼(`signup`, `login`, `token_for`, `bearer`)는 `tests/helpers.py`에 있습니다. 새 모듈은 이 둘을 그대로 쓰고(`from tests.helpers import ...`), 다른 모듈의 테스트 파일에서 fixture를 import하지 않습니다. 아래는 그 구조 설명이며 실제 정의는 `tests/conftest.py`가 정본입니다.

```python
import os

import httpx
import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from database import Base, get_db
from main import app  # 모든 models를 import하므로 FK 대상 테이블까지 create_all된다

pytestmark = [pytest.mark.db, pytest.mark.anyio]


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _test_url():
    explicit = os.getenv("TEST_DATABASE_URL")
    if explicit:
        return make_url(explicit)
    return make_url(os.environ["DATABASE_URL"]).set(database="lastcall_test")


@pytest.fixture
async def session_factory():
    engine = create_async_engine(_test_url(), poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except OSError as err:  # 서버에 닿지 못할 때만 skip
        await engine.dispose()
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

    app.dependency_overrides[get_db] = override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        c.session_factory = session_factory  # 테스트에서 서비스 직접 호출용
        yield c
    app.dependency_overrides.pop(get_db, None)  # clear() 금지: wire_dependencies의 container 매핑까지 지운다
```
- `httpx.ASGITransport`는 lifespan을 실행하지 않습니다. 테이블은 fixture가 만들고, 세션은 `dependency_overrides[get_db]`로 테스트 DB에 연결합니다.
- `NullPool`은 테스트마다 이벤트 루프가 바뀌어도 연결이 남지 않게 합니다.
- 테스트 중에 `app`에 라우트를 추가했다면 `finally`에서 지웁니다(`test_api_db.py`의 `/_t/` 라우트 참고). `dependency_overrides`는 fixture가 넣은 키만 `pop`으로 되돌립니다. `clear()`는 `src/container.py`의 `wire_dependencies`가 넣은 `provide_*` 매핑까지 지워, 다음 테스트부터 `NotImplementedError`가 납니다.

### 작성 요령
- 로그인 토큰은 API로 가입·로그인해서 받습니다(`signup`, `login`, `token_for`, `bearer` 헬퍼). 로그인은 JSON 본문(`json={"email": ..., "password": ...}`)입니다.
- 에러 응답은 본문 전체를 확인합니다: `assert r.json() == {"success": False, "error_code": "...", "message": "..."}`.
- 시드나 서비스 직접 호출은 `async with client.session_factory() as db:`로 세션을 열어 `XxxApplicationService(db)`를 씁니다.
- 동시성은 세션을 따로 연 작업 여러 개를 `asyncio.gather`로 돌려 확인합니다(`test_concurrent_use_points_never_negative` 참고). 실패한 작업은 `await db.rollback()` 합니다.

## 실행
```bash
uv run pytest -rs                 # 전체, skip 이유 표시
uv run pytest -m "not db" -q      # DB 없이 돌릴 수 있는 테스트만
uv run pytest -m db -rs           # DB 테스트만
uv run pytest tests/catalog -rs   # 모듈 하나
```
보고할 때는 `passed / failed / skipped` 수와 skip 이유를 함께 적습니다.
