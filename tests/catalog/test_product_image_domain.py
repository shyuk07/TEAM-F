import os
import uuid

import pytest

from catalog.domain.exceptions import ImageTooLargeError, UnsupportedImageTypeError
from catalog.domain.product import Product
from catalog.domain.product_image import (
    MAX_IMAGE_BYTES,
    ProductImage,
    detect_image_content_type,
    image_path,
    parse_image_path,
)

JPEG = b"\xff\xd8\xff\xe0" + os.urandom(64)
PNG = b"\x89PNG\r\n\x1a\n" + os.urandom(64)
WEBP = b"RIFF" + b"\x10\x00\x00\x00" + b"WEBP" + os.urandom(32)


def test_detect_supported_types():
    assert detect_image_content_type(JPEG) == "image/jpeg"
    assert detect_image_content_type(PNG) == "image/png"
    assert detect_image_content_type(WEBP) == "image/webp"


@pytest.mark.parametrize(
    "data",
    [
        b"GIF89a" + b"\x00" * 20,
        b"BM" + b"\x00" * 30,
        "그냥 텍스트 파일입니다. 이미지가 아닙니다.".encode(),
        b"",
        b"\xff\xd8\xff",  # 12바이트 미만
        b"RIFF" + b"\x10\x00\x00\x00" + b"WAVE" + b"\x00" * 20,
    ],
)
def test_detect_rejects_non_images(data):
    assert detect_image_content_type(data) is None


def test_create_uses_detected_type():
    img = ProductImage.create(uuid.uuid4(), PNG)
    assert img.content_type == "image/png" and img.size_bytes == len(PNG) and img.id is None


def test_create_exactly_max_ok_and_over_rejected():
    ok = PNG + b"\x00" * (MAX_IMAGE_BYTES - len(PNG))
    assert ProductImage.create(uuid.uuid4(), ok).size_bytes == MAX_IMAGE_BYTES
    with pytest.raises(ImageTooLargeError, match="5MB 이하"):
        ProductImage.create(uuid.uuid4(), ok + b"\x00")


def test_create_size_checked_before_type():
    with pytest.raises(ImageTooLargeError):
        ProductImage.create(uuid.uuid4(), b"a" * (MAX_IMAGE_BYTES + 1))


def test_create_rejects_text_and_empty():
    with pytest.raises(UnsupportedImageTypeError, match="JPEG, PNG, WebP"):
        ProductImage.create(uuid.uuid4(), b"hello world, not an image")
    with pytest.raises(UnsupportedImageTypeError):
        ProductImage.create(uuid.uuid4(), b"")


def test_url_requires_id():
    img = ProductImage.create(uuid.uuid4(), PNG)
    with pytest.raises(ValueError):
        img.url
    img.id = uuid.uuid4()
    assert img.url == image_path(img.product_id, img.id)


def test_path_roundtrip_and_rejections():
    pid, iid = uuid.uuid4(), uuid.uuid4()
    assert parse_image_path(image_path(pid, iid)) == (pid, iid)
    assert parse_image_path("https://e.com/a.jpg") is None
    assert parse_image_path(image_path(pid, iid).upper()) is None
    assert parse_image_path(image_path(pid, iid) + "/") is None
    assert parse_image_path(f"/v1/products/{pid}/images/{str(iid).upper()}") is None
    assert parse_image_path(f"/v2/products/{pid}/images/{iid}") is None
    assert parse_image_path(f"/v1/products/{pid}/images/{{{iid}}}") is None


# ── Product ──
def saved_product(images=None):
    return Product(
        store_id=uuid.uuid4(), name="빵", original_price=1000, product_image=images, id=uuid.uuid4()
    )


def uploaded(p):
    return ProductImage(product_id=p.id, content_type="image/png", data=PNG, id=uuid.uuid4())


def test_attach_image_appends_url():
    p = saved_product(["https://e.com/a.jpg"])
    img = uploaded(p)
    p.attach_image(img)
    assert p.product_image == ["https://e.com/a.jpg", img.url]
    assert p.uploaded_image_ids() == {img.id}


def test_attach_image_limit_counts_external_urls():
    p = saved_product([f"https://e.com/{i}.jpg" for i in range(9)])
    p.attach_image(uploaded(p))  # 10번째 성공
    assert len(p.product_image) == 10
    with pytest.raises(ValueError, match="이미지는 최대 10개까지 등록할 수 있습니다."):
        p.attach_image(uploaded(p))
    assert len(p.product_image) == 10


def test_attach_image_rejects_other_product_and_unsaved():
    p = saved_product()
    other = ProductImage(product_id=uuid.uuid4(), content_type="image/png", data=PNG, id=uuid.uuid4())
    with pytest.raises(ValueError):
        p.attach_image(other)
    with pytest.raises(ValueError):
        p.attach_image(ProductImage.create(p.id, PNG))  # id 없음


def test_uploaded_image_ids_ignores_external_and_other_product():
    p = saved_product()
    mine = uploaded(p)
    p.attach_image(mine)
    p.product_image += ["https://e.com/a.jpg", image_path(uuid.uuid4(), uuid.uuid4())]
    assert p.uploaded_image_ids() == {mine.id}


def test_detach_image():
    p = saved_product(["https://e.com/a.jpg"])
    img = uploaded(p)
    p.attach_image(img)
    p.detach_image(uuid.uuid4())  # 없음: 변화 없음
    assert len(p.product_image) == 2
    p.detach_image(img.id)
    assert p.product_image == ["https://e.com/a.jpg"]


def test_apply_changes_returns_removed_upload_ids():
    p = saved_product(["https://e.com/a.jpg"])
    a, b = uploaded(p), uploaded(p)
    p.attach_image(a)
    p.attach_image(b)
    removed = p.apply_changes({"product_image": [b.url, "https://e.com/a.jpg"]}, None)  # a 제거 + 순서 변경
    assert removed == {a.id}
    assert p.product_image == [b.url, "https://e.com/a.jpg"]


def test_apply_changes_reorder_only_returns_empty():
    p = saved_product()
    a, b = uploaded(p), uploaded(p)
    p.attach_image(a)
    p.attach_image(b)
    assert p.apply_changes({"product_image": [b.url, a.url]}, None) == set()
    assert p.apply_changes({"name": "새 이름"}, None) == set()


def test_apply_changes_rejects_new_upload_url_atomically():
    p = saved_product(["https://e.com/a.jpg"])
    mine = uploaded(p)
    p.attach_image(mine)
    before = list(p.product_image)
    for url in (image_path(p.id, uuid.uuid4()), image_path(uuid.uuid4(), uuid.uuid4())):
        with pytest.raises(ValueError, match="직접 추가할 수 없습니다"):
            p.apply_changes({"name": "바뀜", "product_image": [mine.url, url]}, None)
        assert p.name == "빵" and p.product_image == before  # REQ-10: 일부도 안 바뀜


def test_apply_changes_empty_list_removes_all_uploads():
    p = saved_product()
    a = uploaded(p)
    p.attach_image(a)
    assert p.apply_changes({"product_image": []}, None) == {a.id}
    assert p.product_image == []


def test_register_rejects_upload_url_format():
    with pytest.raises(ValueError, match="직접 추가할 수 없습니다"):
        Product.register(uuid.uuid4(), "빵", 1000, product_image=[image_path(uuid.uuid4(), uuid.uuid4())])
    assert Product.register(uuid.uuid4(), "빵", 1000, product_image=["https://e.com/a.jpg"]).product_image


def test_register_keeps_existing_validations():
    with pytest.raises(ValueError, match="최대 10개"):
        Product.register(uuid.uuid4(), "빵", 1000, product_image=["a"] * 11)
    with pytest.raises(ValueError, match="비어 있을 수 없습니다"):
        Product.register(uuid.uuid4(), "빵", 1000, product_image=[" "])


def test_constructor_restores_upload_urls():
    pid = uuid.uuid4()
    url = image_path(pid, uuid.uuid4())
    p = Product(store_id=uuid.uuid4(), name="빵", original_price=1000, product_image=[url], id=pid)
    assert p.product_image == [url]


def _variants(pid, iid):
    base = image_path(pid, iid)
    return [
        base.upper(),
        f"/v1/products/{pid}/images/{str(iid).upper()}",
        base + "?x=1",
        base + "#frag",
        base + "/",
        f"/V1/Products/{pid}/Images/{iid}",
        f"/v1/products/{str(pid).upper()}/images/{iid}",
        " " + base,
        f"/v1/products/{pid}/images",
    ]


def test_looks_like_image_path():
    from catalog.domain.product_image import looks_like_image_path

    pid, iid = uuid.uuid4(), uuid.uuid4()
    assert all(looks_like_image_path(u) for u in [image_path(pid, iid), *_variants(pid, iid)])
    assert not looks_like_image_path("https://e.com/v1/products/x/images/y")
    assert not looks_like_image_path("https://e.com/a.jpg")


def test_apply_changes_rejects_path_variants_of_own_and_foreign_images():
    p = saved_product()
    mine = uploaded(p)
    p.attach_image(mine)
    foreign = (uuid.uuid4(), uuid.uuid4())
    before = list(p.product_image)
    for variant in _variants(p.id, mine.id) + _variants(*foreign):
        with pytest.raises(ValueError, match="직접 추가할 수 없습니다"):
            p.apply_changes({"product_image": [mine.url, variant]}, None)
        assert p.product_image == before
    # 정규 URL을 그대로 유지하는 것은 허용
    assert p.apply_changes({"product_image": [mine.url, "https://e.com/a.jpg"]}, None) == set()


def test_register_rejects_path_variants():
    for variant in _variants(uuid.uuid4(), uuid.uuid4()):
        with pytest.raises(ValueError, match="직접 추가할 수 없습니다"):
            Product.register(uuid.uuid4(), "빵", 1000, product_image=[variant])
