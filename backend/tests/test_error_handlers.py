import httpx
import pytest
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from auth.domain.exceptions import EmailDuplicatedError, TokenRevokedError
from error_handlers import register_exception_handlers

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class Body(BaseModel):
    x: int


class CodedError(ValueError):
    error_code = "CUSTOM"


def make_app():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/revoked")
    async def revoked():
        raise TokenRevokedError()

    @app.get("/dup")
    async def dup():
        raise EmailDuplicatedError()

    @app.get("/value")
    async def value():
        raise ValueError("bad")

    @app.get("/coded")
    async def coded():
        raise CodedError("c")

    @app.get("/perm")
    async def perm():
        raise PermissionError("no")

    @app.get("/lookup")
    async def lookup():
        raise LookupError("none")

    @app.get("/http/{code}")
    async def http(code: int):
        raise HTTPException(code, "d", headers={"X-A": "1"})

    @app.post("/body")
    async def body(b: Body):
        return b

    return app


async def get(path, method="get", **kw):
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        return await c.request(method, path, **kw)


@pytest.mark.parametrize("path,status,code", [
    ("/revoked", 401, "TOKEN_REVOKED"), ("/dup", 409, "EMAIL_DUPLICATED"),
    ("/value", 400, "VALIDATION_ERROR"), ("/coded", 400, "CUSTOM"),
    ("/perm", 403, "FORBIDDEN"), ("/lookup", 404, "NOT_FOUND"),
    ("/http/401", 401, "UNAUTHORIZED"), ("/http/403", 403, "FORBIDDEN"),
    ("/http/404", 404, "NOT_FOUND"), ("/http/409", 409, "CONFLICT"),
    ("/http/418", 418, "HTTP_ERROR"), ("/nope", 404, "NOT_FOUND"),
])
async def test_mapping(path, status, code):
    r = await get(path)
    assert r.status_code == status
    body = r.json()
    assert body["success"] is False and body["error_code"] == code and body["message"]


async def test_revoked_has_www_authenticate():
    assert (await get("/revoked")).headers["www-authenticate"] == "Bearer"


async def test_http_headers_kept():
    assert (await get("/http/418")).headers["x-a"] == "1"


async def test_validation_message():
    r = await get("/body", "post", json={"x": "a"})
    assert r.status_code == 400
    assert r.json()["error_code"] == "VALIDATION_ERROR"
    assert r.json()["message"].startswith("x: ")
