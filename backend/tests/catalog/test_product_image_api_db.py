"""상품 이미지 업로드·삭제·조회 API (실제 DB, ../docs/design/catalog.md 15절)."""

import asyncio
import os
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError

from auth.infrastructure import models as auth_models  # noqa: F401
from catalog.domain.product_image import MAX_IMAGE_BYTES, ProductImage, image_path
from catalog.infrastructure import models as catalog_models
from catalog.infrastructure.repositories import SqlAlchemyProductImageRepository
from catalog.presentation.image_router import (
    IMAGE_RESPONSE_HEADERS,
    MAX_UPLOAD_REQUEST_BYTES,
)
from stores.infrastructure import models as stores_models
from tests.catalog.test_api_db import err, make_offer, make_product, owner_with_store
from tests.helpers import bearer, token_for

pytestmark = [pytest.mark.db, pytest.mark.anyio]

PNG = b"\x89PNG\r\n\x1a\n" + os.urandom(64)
JPEG = b"\xff\xd8\xff\xe0" + os.urandom(64)
WEBP = b"RIFF" + b"\x10\x00\x00\x00" + b"WEBP" + os.urandom(32)
OWNER_403 = err(403, "FORBIDDEN", "본인 상점의 상품만 수정할 수 있습니다.")["message"]


def pad(header: bytes, size: int) -> bytes:
    return header + os.urandom(size - len(header))


async def upload(c, token, product_id, data=PNG, name="a.png", ctype="image/png"):
    headers = bearer(token) if token else {}
    return await c.post(
        f"/v1/products/{product_id}/images", files={"file": (name, data, ctype)}, headers=headers
    )


async def image_count(c, product_id=None):
    async with c.session_factory() as s:
        stmt = select(func.count()).select_from(catalog_models.ProductImageModel)
        if product_id:
            stmt = stmt.where(catalog_models.ProductImageModel.product_id == uuid.UUID(product_id))
        return (await s.execute(stmt)).scalar_one()


async def product_urls(c, product_id):
    r = await c.get(f"/v1/products/{product_id}")
    assert r.status_code == 200, r.text
    return r.json()["product_image"]


async def setup_product(c, email="owner@test.com", **kw):
    token, store_id = await owner_with_store(c, email)
    p = await make_product(c, token, store_id, **kw)
    return token, store_id, p["id"]


# ── #15 업로드 성공 / #17 조회 ──
async def test_upload_ok_and_get_same_bytes(client):
    token, _, pid = await setup_product(client, product_image=["https://e.com/a.jpg"])
    r = await upload(client, token, pid)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["url"] == f"/v1/products/{pid}/images/{body['id']}"
    assert body["product_id"] == pid and body["content_type"] == "image/png"
    assert body["size_bytes"] == len(PNG)
    assert body["product_image"] == ["https://e.com/a.jpg", body["url"]]
    assert await product_urls(client, pid) == ["https://e.com/a.jpg", body["url"]]  # #4 형식 불변

    g = await client.get(body["url"])  # 인증 헤더 없음
    assert g.status_code == 200 and g.content == PNG
    assert g.headers["content-type"] == "image/png"
    for k, v in IMAGE_RESPONSE_HEADERS.items():
        assert g.headers[k] == v


@pytest.mark.parametrize("data,ctype", [(JPEG, "image/jpeg"), (WEBP, "image/webp")])
async def test_upload_jpeg_webp(client, data, ctype):
    token, _, pid = await setup_product(client)
    r = await upload(client, token, pid, data, "x.bin", "application/octet-stream")
    assert r.status_code == 201 and r.json()["content_type"] == ctype
    assert (await client.get(r.json()["url"])).headers["content-type"] == ctype


async def test_content_decided_by_bytes_not_client_headers(client):
    token, _, pid = await setup_product(client)
    r = await upload(client, token, pid, PNG, "a.txt", "text/plain")
    assert r.status_code == 201 and r.json()["content_type"] == "image/png"


# ── 인증·권한·존재 ──
async def test_upload_401(client):
    _, _, pid = await setup_product(client)
    r = await upload(client, None, pid)
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    assert r.json()["success"] is False and r.json()["error_code"] == "UNAUTHORIZED"


async def test_upload_customer_403(client):
    _, _, pid = await setup_product(client)
    ctoken = await token_for(client, "c@test.com", "CUSTOMER")
    r = await upload(client, ctoken, pid)
    assert r.status_code == 403 and r.json()["error_code"] == "FORBIDDEN"


async def test_upload_other_owner_403(client):
    _, _, pid = await setup_product(client)
    other, _ = await owner_with_store(client, "other@test.com")
    r = await upload(client, other, pid)
    assert r.status_code == 403
    assert r.json() == err(403, "FORBIDDEN", "본인 상점의 상품만 수정할 수 있습니다.")
    assert await image_count(client) == 0


async def test_upload_unknown_product_404_and_bad_uuid_400(client):
    token, _ = await owner_with_store(client)
    r = await upload(client, token, uuid.uuid4())
    assert r.status_code == 404 and r.json()["error_code"] == "NOT_FOUND"
    r = await upload(client, token, "not-a-uuid")
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"


# ── 형식·크기·개수 ──
async def test_upload_text_named_jpg_rejected(client):
    token, _, pid = await setup_product(client)
    r = await upload(client, token, pid, "이건 텍스트입니다".encode() * 5, "photo.jpg", "image/jpeg")
    assert r.status_code == 400
    assert r.json() == err(
        400, "UNSUPPORTED_IMAGE_TYPE", "JPEG, PNG, WebP 형식의 이미지만 업로드할 수 있습니다."
    )
    assert await image_count(client) == 0 and await product_urls(client, pid) == []


async def test_upload_gif_and_empty_rejected(client):
    token, _, pid = await setup_product(client)
    for data in (b"GIF89a" + b"\x00" * 30, b""):
        r = await upload(client, token, pid, data, "a.gif", "image/gif")
        assert r.status_code == 400 and r.json()["error_code"] == "UNSUPPORTED_IMAGE_TYPE"
    assert await image_count(client) == 0


async def test_upload_missing_file_field_400(client):
    token, _, pid = await setup_product(client)
    r = await client.post(
        f"/v1/products/{pid}/images", files={"other": ("a.png", PNG, "image/png")}, headers=bearer(token)
    )
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    assert "file" in r.json()["message"]


async def test_upload_json_body_400(client):
    token, _, pid = await setup_product(client)
    r = await client.post(f"/v1/products/{pid}/images", json={"file": "x"}, headers=bearer(token))
    assert r.status_code == 400 and r.json()["success"] is False
    assert await image_count(client) == 0


async def test_upload_exactly_5mib_ok_and_one_more_rejected(client):
    token, _, pid = await setup_product(client)
    ok = await upload(client, token, pid, pad(PNG, MAX_IMAGE_BYTES))
    assert ok.status_code == 201 and ok.json()["size_bytes"] == MAX_IMAGE_BYTES
    g = await client.get(ok.json()["url"])
    assert len(g.content) == MAX_IMAGE_BYTES
    r = await upload(client, token, pid, pad(PNG, MAX_IMAGE_BYTES + 1))
    assert r.status_code == 400
    assert r.json() == err(400, "IMAGE_TOO_LARGE", "이미지 크기는 5MB 이하여야 합니다.")
    assert await image_count(client, pid) == 1 and len(await product_urls(client, pid)) == 1


async def test_oversized_request_without_token_is_400_not_401(client):
    _, _, pid = await setup_product(client)
    big = pad(PNG, MAX_UPLOAD_REQUEST_BYTES + 1024)
    r = await upload(client, None, pid, big)
    assert r.status_code == 400 and r.json()["error_code"] == "IMAGE_TOO_LARGE"
    # 정상 범위(5 MiB 이하)에서 토큰이 없으면 401
    r = await upload(client, None, pid, pad(PNG, MAX_IMAGE_BYTES))
    assert r.status_code == 401


async def test_11th_image_rejected_and_reupload_after_patch(client):
    token, _, pid = await setup_product(
        client, product_image=[f"https://e.com/{i}.jpg" for i in range(5)]
    )
    urls = []
    for _ in range(5):
        r = await upload(client, token, pid)
        assert r.status_code == 201, r.text
        urls = r.json()["product_image"]
    r = await upload(client, token, pid)
    assert r.status_code == 400
    assert r.json() == err(400, "VALIDATION_ERROR", "이미지는 최대 10개까지 등록할 수 있습니다.")
    assert await image_count(client, pid) == 5 and len(await product_urls(client, pid)) == 10
    # PATCH로 1개 빼면 다시 올릴 수 있다
    p = await client.patch(f"/v1/products/{pid}", json={"product_image": urls[:-1]}, headers=bearer(token))
    assert p.status_code == 200, p.text
    assert await image_count(client, pid) == 4
    assert (await upload(client, token, pid)).status_code == 201


# ── 삭제 ──
async def test_delete_ok(client):
    token, _, pid = await setup_product(client, product_image=["https://e.com/a.jpg"])
    body = (await upload(client, token, pid)).json()
    d = await client.delete(body["url"], headers=bearer(token))
    assert d.status_code == 204 and d.content == b""
    assert await product_urls(client, pid) == ["https://e.com/a.jpg"]  # 외부 URL 유지
    g = await client.get(body["url"])
    assert g.status_code == 404 and g.json() == err(404, "NOT_FOUND", "이미지를 찾을 수 없습니다.")
    again = await client.delete(body["url"], headers=bearer(token))
    assert again.status_code == 404 and again.json()["error_code"] == "NOT_FOUND"
    assert await image_count(client) == 0


async def test_delete_unknown_image_404_and_wrong_product(client):
    token, store_id, pid = await setup_product(client)
    body = (await upload(client, token, pid)).json()
    other_p = (await make_product(client, token, store_id, name="다른 상품"))["id"]
    r = await client.delete(f"/v1/products/{pid}/images/{uuid.uuid4()}", headers=bearer(token))
    assert r.status_code == 404
    r = await client.delete(f"/v1/products/{other_p}/images/{body['id']}", headers=bearer(token))
    assert r.status_code == 404
    assert (await client.get(f"/v1/products/{other_p}/images/{body['id']}")).status_code == 404
    assert (await client.get(body["url"])).status_code == 200  # 원래 상품 경로는 그대로
    r = await client.delete(f"/v1/products/{uuid.uuid4()}/images/{body['id']}", headers=bearer(token))
    assert r.status_code == 404
    r = await client.delete(f"/v1/products/{pid}/images/bad-uuid", headers=bearer(token))
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"


async def test_delete_auth(client):
    token, _, pid = await setup_product(client)
    body = (await upload(client, token, pid)).json()
    other, _ = await owner_with_store(client, "other@test.com")
    ctoken = await token_for(client, "c@test.com", "CUSTOMER")
    r = await client.delete(body["url"], headers=bearer(other))
    assert r.status_code == 403 and r.json()["message"] == OWNER_403
    assert (await client.delete(body["url"], headers=bearer(ctoken))).status_code == 403
    r = await client.delete(body["url"])
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    assert await image_count(client) == 1


async def test_get_unknown_and_bad_uuid(client):
    _, _, pid = await setup_product(client)
    r = await client.get(f"/v1/products/{pid}/images/{uuid.uuid4()}")
    assert r.status_code == 404 and r.json()["error_code"] == "NOT_FOUND"
    r = await client.get(f"/v1/products/{pid}/images/bad")
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"


# ── PATCH와의 관계 (D97) ──
async def test_patch_removing_upload_url_deletes_bytes(client):
    token, _, pid = await setup_product(client, product_image=["https://e.com/a.jpg"])
    body = (await upload(client, token, pid)).json()
    r = await client.patch(
        f"/v1/products/{pid}", json={"product_image": ["https://e.com/a.jpg"]}, headers=bearer(token)
    )
    assert r.status_code == 200 and r.json()["product_image"] == ["https://e.com/a.jpg"]
    assert (await client.get(body["url"])).status_code == 404
    assert await image_count(client) == 0


async def test_patch_external_only_change_keeps_upload(client):
    token, _, pid = await setup_product(client, product_image=["https://e.com/a.jpg"])
    body = (await upload(client, token, pid)).json()
    r = await client.patch(
        f"/v1/products/{pid}",
        json={"product_image": [body["url"], "https://e.com/b.jpg"]},  # 외부 URL 교체 + 순서 변경
        headers=bearer(token),
    )
    assert r.status_code == 200 and r.json()["product_image"] == [body["url"], "https://e.com/b.jpg"]
    assert (await client.get(body["url"])).content == PNG
    r = await client.patch(f"/v1/products/{pid}", json={"name": "새 이름"}, headers=bearer(token))
    assert r.status_code == 200 and (await client.get(body["url"])).status_code == 200


async def test_new_upload_url_cannot_be_injected(client):
    token, store_id, pid = await setup_product(client)
    fake = image_path(uuid.UUID(pid), uuid.uuid4())
    r = await client.patch(f"/v1/products/{pid}", json={"product_image": [fake]}, headers=bearer(token))
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    r = await client.post(
        f"/v1/stores/{store_id}/products",
        json={"name": "새 상품", "original_price": 1000, "product_image": [fake]},
        headers=bearer(token),
    )
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    assert await product_urls(client, pid) == []


# ── 공개 범위 / 상태 (D95, D96) ──
async def test_owner_can_upload_delete_for_closed_suspended_inactive(client):
    token, store_id, pid = await setup_product(client)
    async with client.session_factory() as s:
        sm = await s.get(stores_models.StoreModel, uuid.UUID(store_id))
        sm.closed_at = datetime.now(timezone.utc)
        sm.suspended_at = datetime.now(timezone.utc)
        sm.suspended_reason = "정책 위반"
        pm = await s.get(catalog_models.ProductModel, uuid.UUID(pid))
        pm.is_active = False
        await s.commit()
    r = await upload(client, token, pid)
    assert r.status_code == 201, r.text
    assert (await client.get(r.json()["url"])).status_code == 200  # 공개 범위: 상태 무관
    assert (await client.delete(r.json()["url"], headers=bearer(token))).status_code == 204


async def test_get_public_even_when_offer_detail_shows_url(client):
    token, store_id, pid = await setup_product(client)
    url = (await upload(client, token, pid)).json()["url"]
    offer = await make_offer(client, token, pid)
    detail = await client.get(f"/v1/offers/{offer['id']}")
    assert detail.status_code == 200 and url in detail.json()["product_image"]
    async with client.session_factory() as s:  # 노출 중단
        pm = await s.get(catalog_models.ProductModel, uuid.UUID(pid))
        pm.is_active = False
        await s.commit()
    assert (await client.get(url)).status_code == 200


# ── 성능: 다른 조회가 product_images를 건드리지 않는다 (D98) ──
async def test_other_endpoints_never_touch_product_images(client):
    token, store_id, pid = await setup_product(client)
    for _ in range(10):
        assert (await upload(client, token, pid)).status_code == 201
    offer = await make_offer(client, token, pid)

    statements: list[str] = []
    engine = client.session_factory.kw["bind"].sync_engine

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        calls = [
            client.get("/v1/products?keyword=샌드"),
            client.get("/v1/offers"),
            client.get(f"/v1/products/{pid}"),
            client.get(f"/v1/stores/{store_id}/products"),
            client.get(f"/v1/offers/{offer['id']}"),
            client.patch(f"/v1/products/{pid}", json={"name": "다른 이름"}, headers=bearer(token)),
        ]
        for call in calls:
            assert (await call).status_code == 200
        assert not [s for s in statements if "product_images" in s]
        statements.clear()
        assert (await upload(client, token, pid)).status_code == 400  # 11번째: 상한
        statements.clear()
        p2 = (await make_product(client, token, store_id, name="두번째"))["id"]
        statements.clear()
        assert (await upload(client, token, p2)).status_code == 201
        assert [s for s in statements if "INSERT INTO product_images" in s]
    finally:
        event.remove(engine, "before_cursor_execute", record)


# ── 레포지토리 ──
async def test_repository_roundtrip_delete_and_checks(client):
    token, _, pid = await setup_product(client)
    product_id = uuid.UUID(pid)
    data = pad(PNG, MAX_IMAGE_BYTES)
    async with client.session_factory() as s:
        repo = SqlAlchemyProductImageRepository(s)
        img = await repo.add(ProductImage.create(product_id, data))
        await s.commit()
    async with client.session_factory() as s:
        repo = SqlAlchemyProductImageRepository(s)
        got = await repo.find_by_id(product_id, img.id)
        assert got.data == data and got.content_type == "image/png" and got.size_bytes == MAX_IMAGE_BYTES
        assert await repo.find_by_id(uuid.uuid4(), img.id) is None
        assert await repo.delete(uuid.uuid4(), img.id) is False
        assert await repo.delete_many(product_id, set()) == 0
        assert await repo.delete_many(product_id, {img.id, uuid.uuid4()}) == 1
        assert await repo.delete(product_id, img.id) is False
        await s.commit()
    # data는 deferred라 select(Model)에 컬럼이 없다
    stmt = str(select(catalog_models.ProductImageModel))
    assert "product_images.data" not in stmt


@pytest.mark.parametrize(
    "ctype,size,data",
    [
        ("image/gif", 4, b"abcd"),  # 형식 CHECK
        ("image/png", 5242881, b"x" * 5242881),  # 크기 상한 CHECK
        ("image/png", 0, b""),  # 크기 하한 CHECK
        ("image/png", 10, b"abcd"),  # size_bytes 불일치 CHECK
    ],
)
async def test_check_constraints(client, ctype, size, data):
    _, _, pid = await setup_product(client)
    async with client.session_factory() as s:
        s.add(
            catalog_models.ProductImageModel(
                product_id=uuid.UUID(pid), content_type=ctype, size_bytes=size, data=data
            )
        )
        with pytest.raises(IntegrityError):
            await s.flush()


# ── 동시성 ──
async def test_concurrent_uploads_respect_limit(client):
    token, _, pid = await setup_product(
        client, product_image=[f"https://e.com/{i}.jpg" for i in range(8)]
    )
    results = await asyncio.gather(*[upload(client, token, pid, pad(PNG, 200 + i)) for i in range(4)])
    codes = sorted(r.status_code for r in results)
    assert codes == [201, 201, 400, 400], [r.text for r in results]
    urls = await product_urls(client, pid)
    assert len(urls) == 10 and await image_count(client, pid) == 2  # 고아 없음


async def test_upload_vs_patch_keeps_stores_consistent(client):
    token, _, pid = await setup_product(client, product_image=["https://e.com/a.jpg"])
    first = (await upload(client, token, pid)).json()
    results = await asyncio.gather(
        upload(client, token, pid),
        client.patch(f"/v1/products/{pid}", json={"product_image": ["https://e.com/a.jpg"]}, headers=bearer(token)),
    )
    assert all(r.status_code in (200, 201) for r in results)
    urls = await product_urls(client, pid)
    async with client.session_factory() as s:
        ids = {
            str(i)
            for i in (await s.execute(select(catalog_models.ProductImageModel.id))).scalars().all()
        }
    uploaded = {u.rsplit("/", 1)[1] for u in urls if u.startswith("/v1/")}
    assert uploaded == ids  # 불변식: 목록의 업로드 URL 집합 == 행 집합
    assert first["id"] not in ids
