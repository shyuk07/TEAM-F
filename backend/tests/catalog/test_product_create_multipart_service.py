import os

import pytest

from catalog.domain.exceptions import ImageTooLargeError, UnsupportedImageTypeError
from catalog.domain.product_image import MAX_IMAGE_BYTES, image_path
from tests.catalog.test_service import Ctx, anyio_backend  # noqa: F401

pytestmark = pytest.mark.anyio

PNG = b"\x89PNG\r\n\x1a\n" + os.urandom(64)
DATA = {"name": "빵", "original_price": 1000}


@pytest.fixture
def ctx():
    return Ctx()


async def test_without_image_same_as_before(ctx):
    p = await ctx.service.create_product(ctx.owner, ctx.store.id, DATA)
    assert ctx.session.commits == 1 and ctx.images.add_calls == 0 and p.product_image == []


async def test_with_image(ctx):
    p = await ctx.service.create_product(ctx.owner, ctx.store.id, DATA, PNG)
    assert len(ctx.products.items) == 1 and len(ctx.images.items) == 1
    (pid, iid), = ctx.images.items
    assert pid == p.id and p.product_image == [image_path(p.id, iid)]
    assert ctx.products.items[p.id].product_image == p.product_image
    assert ctx.session.commits == 1


@pytest.mark.parametrize(
    "data,exc",
    [(b"not an image at all", UnsupportedImageTypeError), (b"", UnsupportedImageTypeError),
     (PNG + os.urandom(MAX_IMAGE_BYTES), ImageTooLargeError)],
)
async def test_bad_image_leaves_nothing(ctx, data, exc):
    with pytest.raises(exc):
        await ctx.service.create_product(ctx.owner, ctx.store.id, DATA, data)
    assert ctx.products.items == {} and ctx.images.items == {} and ctx.session.commits == 0


async def test_field_error_before_image_error(ctx):
    with pytest.raises(ValueError, match="정상 가격은 0보다 커야 합니다."):
        await ctx.service.create_product(
            ctx.owner, ctx.store.id, {"name": "빵", "original_price": 0}, b"not an image"
        )
    # 필드 불량 + 사진 정상 -> 사진 저장 없음
    with pytest.raises(ValueError):
        await ctx.service.create_product(ctx.owner, ctx.store.id, {"name": "", "original_price": 5}, PNG)
    assert ctx.images.items == {} and ctx.products.items == {} and ctx.session.commits == 0


async def test_image_add_failure_no_commit(ctx):
    async def boom(image):
        raise RuntimeError("db down")

    ctx.images.add = boom
    with pytest.raises(RuntimeError):
        await ctx.service.create_product(ctx.owner, ctx.store.id, DATA, PNG)
    assert ctx.session.commits == 0
