import re
import uuid

from catalog.domain.exceptions import ImageTooLargeError, UnsupportedImageTypeError

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # Q52: 5 MiB. DDL ck_product_images_size와 같은 값
ALLOWED_IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp")

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_UUID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_PATH_RE = re.compile(rf"^/v1/products/({_UUID_PATTERN})/images/({_UUID_PATTERN})$", re.IGNORECASE)


_LOOKS_LIKE_PATH_RE = re.compile(r"^/v1/products/[^/?#]*/images(?:[/?#]|$)", re.IGNORECASE)


def looks_like_image_path(url: str) -> bool:
    """업로드 이미지 경로처럼 보이는지. 대소문자·쿼리스트링·프래그먼트·끝 슬래시 변형도 true."""
    return isinstance(url, str) and _LOOKS_LIKE_PATH_RE.match(url.strip()) is not None


def detect_image_content_type(data: bytes) -> str | None:
    """파일 이름·헤더를 보지 않고 앞부분 바이트(매직 바이트)로만 판별한다."""
    if len(data) < 12:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == _PNG_SIGNATURE:
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def image_path(product_id: uuid.UUID, image_id: uuid.UUID) -> str:
    return f"/v1/products/{product_id}/images/{image_id}"


def parse_image_path(url: str) -> tuple[uuid.UUID, uuid.UUID] | None:
    """업로드 이미지 URL이면 (product_id, image_id), 아니면 None. 재조립 비교로 변형 표기를 거부한다."""
    if not isinstance(url, str):
        return None
    match = _PATH_RE.match(url)
    if match is None:
        return None
    try:
        product_id, image_id = uuid.UUID(match.group(1)), uuid.UUID(match.group(2))
    except ValueError:
        return None
    if image_path(product_id, image_id) != url:
        return None
    return product_id, image_id


class ProductImage:
    def __init__(
        self,
        product_id: uuid.UUID,
        content_type: str,
        data: bytes,
        id: uuid.UUID | None = None,
    ):
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise UnsupportedImageTypeError()
        if not data:
            raise UnsupportedImageTypeError()
        self.id = id
        self.product_id = product_id
        self.content_type = content_type
        self.data = data

    @staticmethod
    def validate_bytes(data: bytes) -> str:
        """저장 전 검증(D113). 통과하면 content_type을 돌려준다."""
        if len(data) > MAX_IMAGE_BYTES:
            raise ImageTooLargeError()
        content_type = detect_image_content_type(data)
        if content_type is None:
            raise UnsupportedImageTypeError()
        return content_type

    @classmethod
    def create(cls, product_id: uuid.UUID, data: bytes) -> "ProductImage":
        content_type = cls.validate_bytes(data)
        return cls(product_id=product_id, content_type=content_type, data=data)

    @property
    def size_bytes(self) -> int:
        return len(self.data)

    @property
    def url(self) -> str:
        if self.id is None:
            raise ValueError("저장되지 않은 이미지는 주소가 없습니다.")
        return image_path(self.product_id, self.id)
