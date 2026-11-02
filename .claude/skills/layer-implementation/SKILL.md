---
name: layer-implementation
description: 마감 직전 프로젝트의 기능 모듈(auth, stores, catalog, reservations, payments)에 domain, infrastructure(models, repositories), application(service), presentation(schemas, router) 코드를 작성할 때 따르는 규칙과 코드 패턴입니다. 4계층 코드를 새로 쓰거나 고칠 때 사용합니다.
---

# 4계층 구현 규칙과 패턴

## 공통 규칙
- import는 `src/` 기준 절대 경로로 씁니다: `from catalog.domain.product import Product`
- 새 폴더를 만들면 `__init__.py`를 함께 만듭니다.
- 구현 순서: domain → infrastructure(models → repositories) → application → presentation(schemas → router) → `main.py` 등록
- 예외 규칙: 규칙 위반은 `ValueError`, 대상 없음은 `LookupError`, 권한 없음은 `PermissionError`를 내고, HTTP 코드 변환은 router에서만 합니다.
- 아래 코드는 `catalog` 상품 예시입니다. 실제 필드와 규칙은 팀이 정한 도메인 규칙을 따릅니다.
- 실제 테이블, 컬럼, FK, UUID·TIMESTAMPTZ 매핑은 `db-schema` 스킬(`.claude/skills/db-schema/SKILL.md`)을 기준으로 합니다. 예시의 `int` ID는 실제로는 `uuid.UUID`입니다.

## 1. domain/ — 순수 파이썬 (Rich Domain Model)
fastapi, sqlalchemy, pydantic, `database`를 import하지 않습니다. 검증과 상태 변경을 클래스 안에 둡니다.

```python
# src/catalog/domain/product.py
class Product:
    def __init__(self, store_id: int, name: str, price: int, stock: int, id: int | None = None):
        if not name.strip():
            raise ValueError("상품명은 비어 있을 수 없습니다.")
        if price < 0:
            raise ValueError("가격은 0원 이상이어야 합니다.")
        if stock < 0:
            raise ValueError("재고는 0개 이상이어야 합니다.")
        self.id = id
        self.store_id = store_id
        self.name = name
        self.price = price
        self.stock = stock

    @property
    def is_sold_out(self) -> bool:
        return self.stock == 0

    def deduct_stock(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("수량은 1개 이상이어야 합니다.")
        if quantity > self.stock:
            raise ValueError("재고가 부족합니다.")
        self.stock -= quantity

    def restore_stock(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("수량은 1개 이상이어야 합니다.")
        self.stock += quantity
```

상태가 있는 엔티티(예약, 결제)는 허용 전이를 메서드로 만들고, 잘못된 전이는 `ValueError`로 막습니다.

## 2. infrastructure/models.py — SQLAlchemy 테이블
```python
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[int]
    stock: Mapped[int]
```

## 3. infrastructure/repositories.py — 모델 ↔ 도메인 변환
`*Model`을 밖으로 내보내지 않습니다. 조회하면 도메인 객체로 바꿔 반환하고, 저장할 때는 도메인 객체를 받습니다. `commit()`은 서비스가 합니다(레포지토리는 `flush()`까지만).

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.domain.product import Product
from catalog.infrastructure.models import ProductModel


class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, product_id: int, for_update: bool = False) -> Product | None:
        stmt = select(ProductModel).where(ProductModel.id == product_id)
        if for_update:
            stmt = stmt.with_for_update()  # 재고 차감처럼 동시성이 중요한 곳에서 사용
        model = (await self.db.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_all(self, *, keyword: str | None = None, offset: int = 0, limit: int = 20) -> list[Product]:
        stmt = select(ProductModel).order_by(ProductModel.id).offset(offset).limit(limit)
        if keyword:
            stmt = stmt.where(ProductModel.name.ilike(f"%{keyword}%"))
        models = (await self.db.execute(stmt)).scalars().all()
        return [self._to_domain(m) for m in models]

    async def save(self, product: Product) -> Product:
        if product.id is None:
            model = ProductModel(store_id=product.store_id, name=product.name,
                                 price=product.price, stock=product.stock)
            self.db.add(model)
            await self.db.flush()
            product.id = model.id
        else:
            model = await self.db.get(ProductModel, product.id)
            if model is None:
                raise LookupError("저장할 상품을 찾을 수 없습니다.")
            model.name = product.name
            model.price = product.price
            model.stock = product.stock
        return product

    @staticmethod
    def _to_domain(model: ProductModel) -> Product:
        return Product(id=model.id, store_id=model.store_id, name=model.name,
                       price=model.price, stock=model.stock)
```

## 4. application/service.py — 흐름과 트랜잭션 조율
비즈니스 판단은 도메인 메서드에 맡기고, 서비스는 조회 → 도메인 메서드 → `save()` → `commit()`만 조율합니다. `HTTPException`을 쓰지 않습니다.

```python
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.domain.product import Product
from catalog.infrastructure.repositories import ProductRepository


class ProductApplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ProductRepository(db)

    async def get_product(self, product_id: int) -> Product:
        product = await self.repository.find_by_id(product_id)
        if product is None:
            raise LookupError("상품을 찾을 수 없습니다.")
        return product

    async def deduct_stock(self, product_id: int, quantity: int) -> Product:
        product = await self.repository.find_by_id(product_id, for_update=True)
        if product is None:
            raise LookupError("상품을 찾을 수 없습니다.")
        product.deduct_stock(quantity)  # 규칙 검사는 도메인이 함
        await self.repository.save(product)
        await self.db.commit()
        return product
```

여러 모듈이 얽힌 흐름(예약 → 재고 차감)은 한 서비스 메서드 안에서 각 레포지토리를 호출하고 `commit()`을 한 번만 합니다.

## 5. presentation/schemas.py — 입출력 검증
```python
from pydantic import BaseModel, ConfigDict, Field


class StockDeductRequest(BaseModel):
    quantity: int = Field(..., ge=1, description="차감할 수량")


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # 도메인 객체를 그대로 직렬화

    id: int = Field(..., description="상품 ID")
    store_id: int = Field(..., description="매장 ID")
    name: str = Field(..., description="상품명")
    price: int = Field(..., description="가격(원)")
    stock: int = Field(..., description="남은 재고")
```
응답 스키마에 비밀번호 해시 같은 민감 정보를 넣지 않습니다.

## 6. presentation/router.py — 엔드포인트와 예외 변환
router는 서비스만 호출합니다(레포지토리·모델 직접 사용 금지).

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.application.service import ProductApplicationService
from catalog.presentation.schemas import ProductResponse, StockDeductRequest
from database import get_db

router = APIRouter(prefix="/products", tags=["상품"])


def get_service(db: AsyncSession = Depends(get_db)) -> ProductApplicationService:
    return ProductApplicationService(db)


@router.get("/{product_id}", response_model=ProductResponse, summary="상품 상세 조회")
async def get_product(product_id: int, service: ProductApplicationService = Depends(get_service)):
    try:
        return await service.get_product(product_id)
    except LookupError as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err))


@router.post("/{product_id}/deduct", response_model=ProductResponse, summary="재고 차감")
async def deduct_stock(product_id: int, body: StockDeductRequest,
                       service: ProductApplicationService = Depends(get_service)):
    try:
        return await service.deduct_stock(product_id, body.quantity)
    except LookupError as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err))
    except ValueError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err))
```

예외 변환이 반복되면 `main.py`에 전역 핸들러(`@app.exception_handler(ValueError)` → 400, `LookupError` → 404)를 두고 router의 try/except를 줄여도 됩니다.

## 7. main.py 등록
```python
from catalog.presentation.router import router as catalog_router
app.include_router(catalog_router)
```
테이블 생성은 `lifespan`에서 `Base.metadata.create_all`로 하므로, 모든 `models.py`를 lifespan보다 먼저 import해야 테이블이 만들어집니다.

## 마무리 확인
```bash
python3 .claude/skills/layer-check/check_layers.py
```
```bash
cd src && uv run python -c "import catalog.presentation.router"
```
