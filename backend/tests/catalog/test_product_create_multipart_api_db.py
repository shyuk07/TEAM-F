"""#1 multipart 등록 · #2 목록 기본값 (실제 DB, ../docs/design/catalog.md 16절)."""

import os
import uuid

import pytest
from sqlalchemy import func, select

from auth.infrastructure import models as auth_models  # noqa: F401
from catalog.domain.product_image import MAX_IMAGE_BYTES
from catalog.infrastructure import models as catalog_models
from catalog.infrastructure.repositories import SqlAlchemyProductImageRepository
from catalog.presentation.image_router import MAX_UPLOAD_REQUEST_BYTES
from stores.infrastructure import models as stores_models  # noqa: F401
from tests.catalog.test_api_db import make_product, owner_with_store, set_product_inactive
from tests.helpers import bearer, token_for

pytestmark = [pytest.mark.db, pytest.mark.anyio]

PNG = b"\x89PNG\r\n\x1a\n" + os.urandom(64)


def pad(header: bytes, size: int) -> bytes:
    return header + os.urandom(size - len(header))


def url_of(store_id):
    return f"/v1/stores/{store_id}/products"


async def post_form(c, store_id, token, data=None, files=None):
    headers = bearer(token) if token else {}
    # httpx는 files가 없으면 urlencoded로 보내므로, 폼 필드도 파트로 만들어 항상 multipart로 보낸다
    parts = [(k, (None, v)) for k, v in (data or {}).items()]
    if isinstance(files, dict):
        parts += list(files.items())
    else:
        parts += list(files or [])
    return await c.post(url_of(store_id), files=parts, headers=headers)


FORM = {"name": "샌드위치", "original_price": "6000", "category": "베이커리", "description": "햄치즈"}


async def counts(c):
    async with c.session_factory() as s:
        p = (await s.execute(select(func.count()).select_from(catalog_models.ProductModel))).scalar_one()
        i = (await s.execute(select(func.count()).select_from(catalog_models.ProductImageModel))).scalar_one()
    return p, i


async def test_multipart_with_image_ok(client):
    token, sid = await owner_with_store(client)
    r = await post_form(client, sid, token, FORM, {"file": ("a.png", PNG, "image/png")})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "샌드위치" and body["original_price"] == 6000 and body["category"] == "베이커리"
    assert len(body["product_image"]) == 1
    assert body["product_image"][0].startswith(f"/v1/products/{body['id']}/images/")
    g = await client.get(body["product_image"][0])
    assert g.status_code == 200 and g.content == PNG
    assert await counts(client) == (1, 1)


async def test_multipart_without_file_and_empty_optionals(client):
    token, sid = await owner_with_store(client)
    r = await post_form(client, sid, token, {**FORM, "category": "", "description": "",
                                              "product_image": "https://e.com/x.jpg"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["category"] is None and body["description"] is None and body["product_image"] == []
    assert await counts(client) == (1, 0)


async def test_bad_type_rolls_back(client):
    token, sid = await owner_with_store(client)
    r = await post_form(client, sid, token, FORM, {"file": ("a.txt", b"hello world not image", "text/plain")})
    assert r.status_code == 400 and r.json()["error_code"] == "UNSUPPORTED_IMAGE_TYPE"
    assert await counts(client) == (0, 0)


async def test_zero_byte_file(client):
    token, sid = await owner_with_store(client)
    r = await post_form(client, sid, token, FORM, {"file": ("a.png", b"", "image/png")})
    assert r.status_code == 400 and r.json()["error_code"] == "UNSUPPORTED_IMAGE_TYPE"
    assert await counts(client) == (0, 0)


async def test_too_large_rolls_back(client):
    token, sid = await owner_with_store(client)
    big = pad(PNG, MAX_IMAGE_BYTES + 1)
    r = await post_form(client, sid, token, FORM, {"file": ("a.png", big, "image/png")})
    assert r.status_code == 400 and r.json()["error_code"] == "IMAGE_TOO_LARGE"
    assert await counts(client) == (0, 0)


async def test_image_add_failure_rolls_back_product(client, monkeypatch):
    token, sid = await owner_with_store(client)

    async def boom(self, image):
        raise RuntimeError("db down")

    monkeypatch.setattr(SqlAlchemyProductImageRepository, "add", boom)
    with pytest.raises(RuntimeError):
        await post_form(client, sid, token, FORM, {"file": ("a.png", PNG, "image/png")})
    assert await counts(client) == (0, 0)


async def test_oversized_multipart_is_400_before_auth(client):
    _, sid = await owner_with_store(client)
    big = pad(PNG, MAX_UPLOAD_REQUEST_BYTES + 1024)
    r = await post_form(client, sid, None, FORM, {"file": ("a.png", big, "image/png")})
    assert r.status_code == 400 and r.json()["error_code"] == "IMAGE_TOO_LARGE"


async def test_two_files_400(client):
    token, sid = await owner_with_store(client)
    r = await post_form(client, sid, token, FORM,
                        [("file", ("a.png", PNG, "image/png")), ("file", ("b.png", PNG, "image/png"))])
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    assert await counts(client) == (0, 0)


async def test_form_validation_matches_json(client):
    token, sid = await owner_with_store(client)
    for form in [{"name": "a"}, {"name": "a", "original_price": "abc"}]:
        rf = await post_form(client, sid, token, form)
        assert rf.status_code == 400 and rf.json()["error_code"] == "VALIDATION_ERROR"
        assert rf.json()["message"].startswith("original_price")
    rj = await client.post(url_of(sid), json={"name": "a"}, headers=bearer(token))
    rf = await post_form(client, sid, token, {"name": "a"})
    assert rj.status_code == rf.status_code == 400
    assert rj.json()["error_code"] == rf.json()["error_code"]
    assert rj.json()["message"].split(":")[0] == rf.json()["message"].split(":")[0]


async def test_field_error_precedes_image_error(client):
    token, sid = await owner_with_store(client)
    r = await post_form(client, sid, token, {**FORM, "original_price": "0"},
                        {"file": ("a.txt", b"not an image at all", "text/plain")})
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    assert r.json()["message"] == "정상 가격은 0보다 커야 합니다."


async def test_auth_before_image_validation(client):
    token, sid = await owner_with_store(client)
    files = {"file": ("a.txt", b"not an image at all", "text/plain")}
    assert (await post_form(client, sid, None, FORM, files)).status_code == 401
    other = await token_for(client, "o2@test.com", "OWNER")
    assert (await post_form(client, sid, other, FORM, files)).status_code == 403
    cust = await token_for(client, "c@test.com", "CUSTOMER")
    assert (await post_form(client, sid, cust, FORM, files)).status_code == 403


async def test_broken_multipart_is_400(client):
    token, sid = await owner_with_store(client)
    r = await client.post(
        url_of(sid), content=b"garbage",
        headers={**bearer(token), "content-type": "multipart/form-data; boundary=zzz"},
    )
    assert r.status_code == 400
    print("broken multipart:", r.json())


# ── JSON 회귀 ──
async def test_json_regression(client):
    token, sid = await owner_with_store(client)
    r = await client.post(url_of(sid), json={"name": "a", "original_price": 100,
                                             "product_image": ["https://e.com/a.jpg"]}, headers=bearer(token))
    assert r.status_code == 201 and r.json()["product_image"] == ["https://e.com/a.jpg"]
    r = await client.post(url_of(sid), json={"name": "a", "original_price": 0}, headers=bearer(token))
    assert r.status_code == 400 and r.json()["message"] == "정상 가격은 0보다 커야 합니다."
    r = await client.post(url_of(sid), content=b"{broken", headers={**bearer(token), "content-type": "application/json"})
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    assert r.json()["message"] == "1: JSON decode error"  # main(FastAPI)과 같은 loc(e.pos=1)·msg
    jh = {**bearer(token), "content-type": "application/json"}
    for body in (b"[]", b'"x"'):  # 객체가 아닌 JSON: main과 같은 pydantic 메시지
        r = await client.post(url_of(sid), content=body, headers=jh)
        assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
        assert r.json()["message"] == "요청: Input should be a valid dictionary or object to extract fields from"
    r = await client.post(url_of(sid), json={"original_price": 1}, headers=bearer(token))
    assert r.json()["message"] == "name: Field required"
    r = await client.post(url_of(sid), content=b"", headers=jh)  # 빈 본문: main과 같은 missing
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    assert r.json()["message"] == "요청: Field required"
    r = await client.post(url_of(sid), content=b"\xff\xfe\x00", headers=jh)  # 비 UTF-8: main과 같은 HTTP_ERROR
    assert r.status_code == 400 and r.json()["error_code"] == "HTTP_ERROR"
    assert r.json()["message"] == "There was an error parsing the body"


async def test_large_json_is_not_image_too_large(client):
    token, sid = await owner_with_store(client)
    r = await client.post(
        url_of(sid), json={"name": "a", "original_price": 100, "description": "x" * (MAX_UPLOAD_REQUEST_BYTES + 10)},
        headers=bearer(token),
    )
    assert r.status_code == 201, r.text[:200]


# ── #2 목록 3x3 ──
async def test_list_products_matrix(client):
    owner, sid = await owner_with_store(client)
    await make_product(client, owner, sid, name="shown", category="x")
    hidden = await make_product(client, owner, sid, name="hidden", category="x")
    await set_product_inactive(client, hidden["id"])
    other = await token_for(client, "x@test.com", "CUSTOMER")
    viewers = {"owner": bearer(owner), "other": bearer(other), "anon": {}}
    expected = {
        "owner": {None: (["hidden", "shown"], 2), "true": (["shown"], 1), "false": (["hidden"], 1)},
        "other": {None: (["shown"], 1), "true": (["shown"], 1), "false": ([], 0)},
        "anon": {None: (["shown"], 1), "true": (["shown"], 1), "false": ([], 0)},
    }
    for who, headers in viewers.items():
        for flag, (names, total) in expected[who].items():
            params = {} if flag is None else {"is_active": flag}
            r = await client.get(url_of(sid), params=params, headers=headers)
            assert r.status_code == 200, (who, flag, r.text)
            body = r.json()
            assert [i["name"] for i in body["items"]] == names and body["total"] == total, (who, flag)
    r = await client.get(url_of(sid), params={"category": "x", "page": 2, "size": 1}, headers=bearer(owner))
    assert [i["name"] for i in r.json()["items"]] == ["shown"] and r.json()["total"] == 2
