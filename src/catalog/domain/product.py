import uuid

from catalog.domain.exceptions import (
    ProductAlreadyInactiveError,
    ProductHasOpenOfferError,
    ProductInactiveError,
)

MAX_NAME_LENGTH = 200
MAX_CATEGORY_LENGTH = 80
MAX_IMAGES = 10
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
        return cls(
            store_id=store_id,
            name=name,
            original_price=original_price,
            category=category,
            description=description,
            product_image=product_image,
        )

    def apply_changes(self, changes: dict, open_offer_sale_price: int | None) -> None:
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
            price = self._validate_price(changes["original_price"])
            if open_offer_sale_price is not None and price <= open_offer_sale_price:
                raise ValueError("정상 가격은 진행 중인 할인 가격보다 커야 합니다.")
            new["original_price"] = price
        if "product_image" in changes:
            if changes["product_image"] is None:  # D16: null 거부
                raise ValueError("이미지 목록은 비울 수 없습니다. 빈 목록([])을 보내 주세요.")
            new["product_image"] = self._validate_images(changes["product_image"])
        for key, value in new.items():
            setattr(self, key, value)

    def deactivate(self, has_open_offer: bool) -> None:
        if not self.is_active:
            raise ProductAlreadyInactiveError("이미 비활성화된 상품입니다.")
        if has_open_offer:
            raise ProductHasOpenOfferError("진행 중인 할인 판매가 있어 비활성화할 수 없습니다.")
        self.is_active = False

    def ensure_active_for_offer(self) -> None:
        if not self.is_active:
            raise ProductInactiveError("비활성화된 상품은 할인 등록할 수 없습니다.")
