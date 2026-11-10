import os
import uuid

import pytest

from catalog.domain.exceptions import ImageTooLargeError, UnsupportedImageTypeError
from catalog.domain.product_image import MAX_IMAGE_BYTES, ProductImage
from catalog.domain.store_ref import ProductListScope, StoreRef

JPEG = b"\xff\xd8\xff\xe0" + os.urandom(64)
PNG = b"\x89PNG\r\n\x1a\n" + os.urandom(64)
WEBP = b"RIFF" + b"\x10\x00\x00\x00" + b"WEBP" + os.urandom(32)


@pytest.mark.parametrize(
    "data,ctype", [(JPEG, "image/jpeg"), (PNG, "image/png"), (WEBP, "image/webp")]
)
def test_validate_bytes_ok_and_create_matches(data, ctype):
    assert ProductImage.validate_bytes(data) == ctype
    assert ProductImage.create(uuid.uuid4(), data).content_type == ctype


def test_validate_bytes_too_large():
    big = PNG + os.urandom(MAX_IMAGE_BYTES + 1 - len(PNG))
    with pytest.raises(ImageTooLargeError):
        ProductImage.validate_bytes(big)
    with pytest.raises(ImageTooLargeError):
        ProductImage.create(uuid.uuid4(), big)


@pytest.mark.parametrize("data", [b"", b"hello world, not an image"])
def test_validate_bytes_unsupported(data):
    with pytest.raises(UnsupportedImageTypeError):
        ProductImage.validate_bytes(data)
    with pytest.raises(UnsupportedImageTypeError):
        ProductImage.create(uuid.uuid4(), data)


OWNER = uuid.uuid4()
STORE = StoreRef(id=uuid.uuid4(), owner_id=OWNER, name="s", pickup_address="a", approved=True, closed=False)


@pytest.mark.parametrize(
    "viewer,requested,expected",
    [
        (OWNER, None, ProductListScope(False, None)),
        (OWNER, True, ProductListScope(False, True)),
        (OWNER, False, ProductListScope(False, False)),
        (uuid.uuid4(), None, ProductListScope(False, True)),
        (uuid.uuid4(), True, ProductListScope(False, True)),
        (uuid.uuid4(), False, ProductListScope(True, True)),
        (None, None, ProductListScope(False, True)),
        (None, True, ProductListScope(False, True)),
        (None, False, ProductListScope(True, True)),
    ],
)
def test_product_list_scope(viewer, requested, expected):
    assert STORE.product_list_scope(viewer, requested) == expected
