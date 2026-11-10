import uuid

from catalog.domain.product_image import ProductImage, image_path, looks_like_image_path, parse_image_path
from catalog.domain.exceptions import (
    ProductAlreadyActiveError,
    ProductAlreadyInactiveError,
    ProductHasOpenOfferError,
    ProductInactiveError,
)

MAX_NAME_LENGTH = 200
MAX_CATEGORY_LENGTH = 80
MAX_IMAGES = 10
MAX_PRICE = 99_999_999  # requirements REQ-3: 1억 이상 거부
_UPLOAD_URL_MESSAGE = "업로드한 이미지 주소는 직접 추가할 수 없습니다. 이미지 업로드를 이용하세요."
_CHANGEABLE = {"name", "category", "description", "original_price", "product_image"}


class Product:
    def __init__(
        self,
        store_id: uuid.UUID,
        name: str,
        original_price: int,
        category: str | None = None,
        description: str | None = None,
        is_active: bool = True,
        product_image: list[str] | None = None,
        id: uuid.UUID | None = None,
    ):
        self.id = id
        self.store_id = store_id
        self.name = self._validate_name(name)
        self.category = self._validate_category(category)
        self.description = description
        self.original_price = self._validate_price(original_price)
        self.is_active = is_active
        self.product_image = self._validate_images(product_image)

    @staticmethod
    def _validate_name(name: str | None) -> str:
        if not isinstance(name, str):
            raise ValueError("상품명은 1자 이상 200자 이하여야 합니다.")
        stripped = name.strip()
        if not 1 <= len(stripped) <= MAX_NAME_LENGTH:
            raise ValueError("상품명은 1자 이상 200자 이하여야 합니다.")
        return stripped

    @staticmethod
    def _validate_category(category: str | None) -> str | None:
        if category is None:
            return None
        stripped = category.strip()
        if not 1 <= len(stripped) <= MAX_CATEGORY_LENGTH:
            raise ValueError("카테고리는 1자 이상 80자 이하여야 합니다.")
        return stripped

    @staticmethod
    def _validate_price(price: int | None) -> int:
        if isinstance(price, bool) or not isinstance(price, int) or price <= 0:
            raise ValueError("정상 가격은 0보다 커야 합니다.")
        return price

    @classmethod
    def _validate_new_price(cls, price: int | None) -> int:
        """새로 입력되는 가격용. 상한은 상한 도입 전 저장된 값의 복원을 막지 않도록 여기서만 검사한다."""
        price = cls._validate_price(price)
        if price > MAX_PRICE:
            raise ValueError("정상 가격은 1억 원 미만이어야 합니다.")
        return price

    @staticmethod
    def _validate_images(images: list[str] | None) -> list[str]:
        if images is None:
            return []
        if len(images) > MAX_IMAGES:
            raise ValueError("이미지는 최대 10개까지 등록할 수 있습니다.")
        if any(not isinstance(i, str) or not i.strip() for i in images):
            raise ValueError("이미지 주소는 비어 있을 수 없습니다.")
        return list(images)

    @classmethod
    def register(
        cls,
        store_id: uuid.UUID,
        name: str,
        original_price: int,
        category: str | None = None,
        description: str | None = None,
        product_image: list[str] | None = None,
    ) -> "Product":
        if any(looks_like_image_path(i) for i in product_image or []):
            raise ValueError(_UPLOAD_URL_MESSAGE)
        return cls(
            store_id=store_id,
            name=name,
            original_price=cls._validate_new_price(original_price),
            category=category,
            description=description,
            product_image=product_image,
        )

    def apply_changes(self, changes: dict, open_offer_sale_price: int | None) -> set[uuid.UUID]:
        """반환: 이번 변경으로 목록에서 빠진 업로드 이미지 id (바이트 삭제 대상)."""
        if not changes:
            raise ValueError("수정할 항목이 없습니다.")
        unknown = set(changes) - _CHANGEABLE
        if unknown:
            raise ValueError(f"수정할 수 없는 항목입니다: {', '.join(sorted(unknown))}")
        # 모두 검증한 뒤 한꺼번에 반영한다 (일부만 바뀌지 않게)
        new: dict = {}
        if "name" in changes:
            new["name"] = self._validate_name(changes["name"])
        if "category" in changes:
            new["category"] = self._validate_category(changes["category"])
        if "description" in changes:
            new["description"] = changes["description"]
        if "original_price" in changes:
            price = self._validate_new_price(changes["original_price"])
            if open_offer_sale_price is not None and price <= open_offer_sale_price:
                raise ValueError("정상 가격은 진행 중인 할인 가격보다 커야 합니다.")
            new["original_price"] = price
        if "product_image" in changes:
            if changes["product_image"] is None:  # D16: null 거부
                raise ValueError("이미지 목록은 비울 수 없습니다. 빈 목록([])을 보내 주세요.")
            images = self._validate_images(changes["product_image"])
            current = self.uploaded_image_ids()
            for url in images:
                if not looks_like_image_path(url):
                    continue
                parsed = parse_image_path(url)  # 정규형이 아니면 None
                if parsed is None or not (parsed[0] == self.id and parsed[1] in current):
                    raise ValueError(_UPLOAD_URL_MESSAGE)
            new["product_image"] = images
        removed: set[uuid.UUID] = set()
        if "product_image" in new:
            kept = {p[1] for p in map(parse_image_path, new["product_image"]) if p is not None}
            removed = self.uploaded_image_ids() - kept
        for key, value in new.items():
            setattr(self, key, value)
        return removed

    def uploaded_image_ids(self) -> set[uuid.UUID]:
        ids: set[uuid.UUID] = set()
        for url in self.product_image:
            parsed = parse_image_path(url)
            if parsed is not None and parsed[0] == self.id:
                ids.add(parsed[1])
        return ids

    def ensure_can_attach_image(self) -> None:
        if len(self.product_image) >= MAX_IMAGES:
            raise ValueError("이미지는 최대 10개까지 등록할 수 있습니다.")

    def attach_image(self, image: ProductImage) -> None:
        if image.id is None:
            raise ValueError("저장되지 않은 이미지는 붙일 수 없습니다.")
        if image.product_id != self.id:
            raise ValueError("다른 상품의 이미지는 붙일 수 없습니다.")
        self.ensure_can_attach_image()
        self.product_image.append(image.url)

    def detach_image(self, image_id: uuid.UUID) -> None:
        target = image_path(self.id, image_id)
        self.product_image = [u for u in self.product_image if u != target]

    def deactivate(self, has_open_offer: bool) -> None:
        if not self.is_active:
            raise ProductAlreadyInactiveError("이미 비활성화된 상품입니다.")
        if has_open_offer:
            raise ProductHasOpenOfferError("진행 중인 할인 판매가 있어 비활성화할 수 없습니다.")
        self.is_active = False

    def reactivate(self) -> None:
        if self.is_active:
            raise ProductAlreadyActiveError("이미 노출 중인 상품입니다.")
        self.is_active = True

    def ensure_active_for_offer(self) -> None:
        if not self.is_active:
            raise ProductInactiveError("비활성화된 상품은 할인 등록할 수 없습니다.")
