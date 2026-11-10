import os
import uuid

import pytest

from catalog.domain.exceptions import (
    ImageTooLargeError,
    NotStoreOwnerError,
    ProductImageNotFoundError,
    ProductNotFoundError,
    UnsupportedImageTypeError,
)
from catalog.domain.product_image import MAX_IMAGE_BYTES, ProductImage, image_path
from tests.catalog.test_service import NOW, Ctx, anyio_backend  # noqa: F401

pytestmark = pytest.mark.anyio

PNG = b"\x89PNG\r\n\x1a\n" + os.urandom(64)
FULL = [f"https://e.com/{i}.jpg" for i in range(10)]


@pytest.fixture
def ctx():
    return Ctx()


async def attach_existing(ctx, product, data=PNG):
    img = ProductImage.create(product.id, data)
    await ctx.images.add(img)
    product.attach_image(img)
    return img


# ── #15 ──
async def test_upload_success(ctx):
    p = await ctx.product(product_image=["https://e.com/a.jpg"])
    result = await ctx.service.upload_product_image(ctx.owner, p.id, PNG)
    assert ctx.session.commits == 1 and ctx.images.add_calls == 1
    assert result.image.id is not None and result.image.content_type == "image/png"
    assert result.product.product_image == ["https://e.com/a.jpg", image_path(p.id, result.image.id)]
    assert ctx.products.items[p.id].product_image == result.product.product_image
    assert p.id in ctx.products.locked


async def test_upload_unknown_product(ctx):
    with pytest.raises(ProductNotFoundError):
        await ctx.service.upload_product_image(ctx.owner, uuid.uuid4(), PNG)
    assert ctx.session.commits == 0 and ctx.images.add_calls == 0


async def test_upload_other_owner(ctx):
    p = await ctx.product()
    with pytest.raises(NotStoreOwnerError, match="본인 상점의 상품만 수정할 수 있습니다."):
        await ctx.service.upload_product_image(uuid.uuid4(), p.id, PNG)
    assert ctx.session.commits == 0 and ctx.images.add_calls == 0


async def test_upload_text_too_large_and_full(ctx):
    p = await ctx.product()
    with pytest.raises(UnsupportedImageTypeError):
        await ctx.service.upload_product_image(ctx.owner, p.id, b"plain text file contents")
    with pytest.raises(ImageTooLargeError):
        await ctx.service.upload_product_image(ctx.owner, p.id, PNG + b"\x00" * MAX_IMAGE_BYTES)
    full = await ctx.product(product_image=FULL)
    with pytest.raises(ValueError, match="이미지는 최대 10개까지 등록할 수 있습니다."):
        await ctx.service.upload_product_image(ctx.owner, full.id, PNG)
    assert ctx.session.commits == 0 and ctx.images.add_calls == 0


async def test_upload_error_priority(ctx):
    full = await ctx.product(product_image=FULL)
    big_text = b"t" * (MAX_IMAGE_BYTES + 1)
    with pytest.raises(NotStoreOwnerError):  # 403이 400 형식 오류보다 먼저
        await ctx.service.upload_product_image(uuid.uuid4(), full.id, b"text")
    with pytest.raises(ImageTooLargeError):  # 크기 > 형식 > 개수
        await ctx.service.upload_product_image(ctx.owner, full.id, big_text)
    with pytest.raises(UnsupportedImageTypeError):
        await ctx.service.upload_product_image(ctx.owner, full.id, b"text")
    with pytest.raises(ValueError, match="최대 10개"):
        await ctx.service.upload_product_image(ctx.owner, full.id, PNG)


async def test_upload_allowed_for_closed_suspended_inactive(ctx):
    p = await ctx.product()
    p.is_active = False
    ctx.store.closed_at = NOW
    ctx.store.suspended_at = NOW
    result = await ctx.service.upload_product_image(ctx.owner, p.id, PNG)  # D95
    assert result.image.id is not None and ctx.session.commits == 1


# ── #16 ──
async def test_delete_success(ctx):
    p = await ctx.product(product_image=["https://e.com/a.jpg"])
    img = await attach_existing(ctx, p)
    await ctx.service.delete_product_image(ctx.owner, p.id, img.id)
    assert ctx.session.commits == 1
    assert (p.id, img.id) not in ctx.images.items
    assert ctx.products.items[p.id].product_image == ["https://e.com/a.jpg"]


async def test_delete_unknown_image(ctx):
    p = await ctx.product()
    with pytest.raises(ProductImageNotFoundError, match="이미지를 찾을 수 없습니다."):
        await ctx.service.delete_product_image(ctx.owner, p.id, uuid.uuid4())
    assert ctx.session.commits == 0


async def test_delete_other_owner_is_403_even_if_image_exists(ctx):
    p = await ctx.product()
    img = await attach_existing(ctx, p)
    with pytest.raises(NotStoreOwnerError):
        await ctx.service.delete_product_image(uuid.uuid4(), p.id, img.id)
    with pytest.raises(NotStoreOwnerError):
        await ctx.service.delete_product_image(uuid.uuid4(), p.id, uuid.uuid4())
    assert ctx.session.commits == 0 and (p.id, img.id) in ctx.images.items


async def test_delete_unknown_product(ctx):
    with pytest.raises(ProductNotFoundError):
        await ctx.service.delete_product_image(ctx.owner, uuid.uuid4(), uuid.uuid4())


async def test_delete_row_without_url_self_heals(ctx):
    p = await ctx.product()
    img = ProductImage.create(p.id, PNG)
    await ctx.images.add(img)  # 목록에는 URL 없음
    await ctx.service.delete_product_image(ctx.owner, p.id, img.id)
    assert ctx.session.commits == 1 and (p.id, img.id) not in ctx.images.items


# ── #17 ──
async def test_get_image(ctx):
    p = await ctx.product()
    img = await attach_existing(ctx, p)
    got = await ctx.service.get_product_image(p.id, img.id)
    assert got.data == PNG and ctx.session.commits == 0
    assert ctx.stores.visible_calls == []


async def test_get_image_not_found_and_wrong_product(ctx):
    p = await ctx.product()
    img = await attach_existing(ctx, p)
    with pytest.raises(ProductImageNotFoundError):
        await ctx.service.get_product_image(p.id, uuid.uuid4())
    with pytest.raises(ProductImageNotFoundError):
        await ctx.service.get_product_image(uuid.uuid4(), img.id)
    assert ctx.session.commits == 0


# ── update_product (D97) ──
async def test_update_removing_upload_url_deletes_bytes_before_commit(ctx):
    p = await ctx.product(product_image=["https://e.com/a.jpg"])
    img = await attach_existing(ctx, p)
    ctx.products.events.clear()
    await ctx.service.update_product(ctx.owner, p.id, {"product_image": ["https://e.com/a.jpg"]})
    assert ctx.images.delete_many_calls == [(p.id, {img.id})]
    assert ctx.session.commits == 1
    assert (p.id, img.id) not in ctx.images.items
    assert ctx.products.events.index("image_delete_many") > ctx.products.events.index("product_lock")


async def test_update_without_image_change_skips_delete_many(ctx):
    p = await ctx.product()
    await attach_existing(ctx, p)
    await ctx.service.update_product(ctx.owner, p.id, {"name": "새 이름"})
    await ctx.service.update_product(ctx.owner, p.id, {"product_image": list(p.product_image)})
    assert ctx.images.delete_many_calls == []  # 그대로 다시 보냄: 빠진 것 없음


async def test_update_adding_new_upload_url_rejected(ctx):
    p = await ctx.product()
    with pytest.raises(ValueError, match="직접 추가할 수 없습니다"):
        await ctx.service.update_product(
            ctx.owner, p.id, {"product_image": [image_path(p.id, uuid.uuid4())]}
        )
    assert ctx.session.commits == 0 and ctx.images.delete_many_calls == []
