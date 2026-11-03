---
name: layer-implementation
description: 마감 직전 프로젝트의 기능 모듈(auth, stores, catalog, reservations, payments)에 domain, infrastructure(models, repositories), application(service), presentation(schemas, router) 코드를 작성할 때 따르는 규칙과 코드 패턴입니다. 4계층 코드를 새로 쓰거나 고칠 때 사용합니다.
---

# 4계층 구현 규칙과 패턴

정답 예시는 이미 구현된 auth 모듈입니다(`src/auth/**`, `src/error_handlers.py`, `src/main.py`, `tests/**`). 이 문서와 auth 코드가 다르면 auth 코드를 따르고 이 문서를 고칩니다.

> **의존성 주입·조립은 `layer-architecture` 스킬이 정본입니다.** 아래 예시 중 서비스가 레포지토리를 직접 생성하는 부분(`offers or DiscountOfferRepository(db)` 등)은 이전 방식입니다. 새 코드는 domain 추상 레포지토리 + infrastructure 구현체 + `presentation/dependencies.py`의 `provide_*` + `src/container.py` 연결을 따릅니다.

## 공통 규칙
- import는 `src/` 기준 절대 경로로 씁니다: `from catalog.domain.discount_offer import DiscountOffer`
- 새 폴더를 만들면 `__init__.py`를 함께 만듭니다.
- 구현 순서: domain → infrastructure(models → repositories) → application → presentation(schemas → router) → `main.py` 등록 → 테스트
- ID는 `uuid.UUID`, 시간은 timezone이 있는 `datetime`입니다. 테이블, 컬럼, FK, 매핑은 `db-schema` 스킬(`.claude/skills/db-schema/SKILL.md`)을 기준으로 합니다.
- 에러 응답은 공통 형식 `{"success": false, "error_code": "...", "message": "..."}`입니다(`docs/reference/README.md`). 이 형식은 `src/error_handlers.py`의 전역 핸들러가 만듭니다. **router에서 try/except로 `HTTPException`을 만들지 않습니다.**
- 공용 코드는 `src/common/`(4계층 불필요) 또는 `src` 루트 단일 파일(`database.py`, `error_handlers.py`처럼)에 둡니다. 기능 모듈 안에 다른 모듈용 공용 코드를 두지 않습니다.
- 아래 코드는 `catalog`의 마감 할인(`discount_offers`) 예시입니다. 시간 컬럼(`sales_end`, `pickup_start` 등)은 줄였으니 실제 `models.py`는 `db-schema` 6절을 그대로 따릅니다.
- 테스트 작성법은 같은 폴더의 [`testing.md`](testing.md)를 봅니다.

## 예외 → HTTP 상태 코드 (`src/error_handlers.py` 기준)
도메인·서비스는 파이썬 예외만 냅니다. 상태 코드 변환은 전역 핸들러가 합니다. 핸들러는 예외 클래스의 MRO를 따라 가장 가까운 등록 클래스를 고르므로, 하위 클래스도 같은 코드로 변환됩니다.

| 예외 | 상태 | `error_code` | 비고 |
| --- | --- | --- | --- |
| `RequestValidationError` (Pydantic, 잘못된 UUID 경로값 포함) | 400 | `VALIDATION_ERROR` | 메시지는 `필드: 오류` 형식 |
| `ValueError`와 하위 클래스 | 400 | 클래스의 `error_code` 속성, 없으면 `VALIDATION_ERROR` | 도메인 규칙 위반 |
| `AuthenticationError`와 하위 클래스 (`auth.domain.exceptions`) | 401 | 클래스의 `error_code` | `WWW-Authenticate: Bearer` 헤더 포함 |
| `PermissionError` | 403 | `FORBIDDEN` (고정) | 역할·소유권 없음 |
| `LookupError`와 하위 클래스 | 404 | `NOT_FOUND` (고정) | 대상 없음 |
| `EmailDuplicatedError` | 409 | `EMAIL_DUPLICATED` | `ValueError`를 상속하지 않음 |
| `HTTPException` (FastAPI·Starlette 내부) | 해당 코드 | 401/403/404/409는 이름, 그 외 `HTTP_ERROR` | 직접 만들지 않음 |

새 모듈 규칙:
- **도메인 전용 예외를 만듭니다.** `LookupError`·`PermissionError`는 그대로 내지 말고 `<모듈>/domain/exceptions.py`에 하위 클래스를 둡니다. `ValueError`는 단순 입력 검증이면 그대로 써도 되고(400 `VALIDATION_ERROR`), 화면에서 구분할 `error_code`가 필요하면 하위 클래스를 만듭니다. 전역 `LookupError` 핸들러는 `KeyError`·`IndexError` 같은 버그까지 404로 바꿔 숨기므로, 서비스가 의도한 예외를 클래스로 구분해 둬야 테스트와 나중의 핸들러 축소가 쉽습니다.
- `error_code`가 응답에 반영되는 것은 `ValueError` 하위 클래스와 `AuthenticationError`뿐입니다. 404·403은 `NOT_FOUND`·`FORBIDDEN`으로 고정입니다.
- 409(중복·상태 충돌)는 auth처럼 `Exception`을 상속한 전용 예외를 만들고 `src/error_handlers.py`에 핸들러를 한 줄 추가합니다. `ValueError`를 상속하면 400이 됩니다. `error_handlers.py`는 모듈 밖 파일이므로 보고서에 적습니다.
- 401은 직접 만들지 않고 `auth`의 인증 의존성(아래)을 씁니다.

```python
# src/catalog/domain/exceptions.py
class OfferNotFoundError(LookupError):
    """404 NOT_FOUND"""

    def __init__(self, message: str = "할인 상품을 찾을 수 없습니다."):
        super().__init__(message)


class OutOfStockError(ValueError):
    """400 OUT_OF_STOCK"""

    error_code = "OUT_OF_STOCK"

    def __init__(self, message: str = "재고가 부족합니다."):
        super().__init__(message)


class NotOfferOwnerError(PermissionError):
    """403 FORBIDDEN"""

    def __init__(self, message: str = "본인 매장의 상품만 수정할 수 있습니다."):
        super().__init__(message)
```

## 1. domain/ — 순수 파이썬 (Rich Domain Model)
fastapi, sqlalchemy, pydantic, `database`, jwt, passlib을 import하지 않습니다. 검증과 상태 변경을 클래스 안에 둡니다.

```python
# src/catalog/domain/discount_offer.py
import uuid
from enum import StrEnum

from catalog.domain.exceptions import OutOfStockError


class OfferStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    ON_SALE = "ON_SALE"
    SOLD_OUT = "SOLD_OUT"
    CLOSED = "CLOSED"


class DiscountOffer:
    def __init__(
        self,
        product_id: uuid.UUID,
        sale_price: int,
        initial_stock: int,
        remaining_stock: int | None = None,
        status: OfferStatus = OfferStatus.SCHEDULED,
        id: uuid.UUID | None = None,
    ):
        if sale_price < 0:
            raise ValueError("할인가는 0원 이상이어야 합니다.")
        if initial_stock < 0:
            raise ValueError("재고는 0개 이상이어야 합니다.")
        remaining = initial_stock if remaining_stock is None else remaining_stock
        if not 0 <= remaining <= initial_stock:
            raise ValueError("남은 재고가 범위를 벗어났습니다.")
        self.id = id
        self.product_id = product_id
        self.sale_price = sale_price
        self.initial_stock = initial_stock
        self.remaining_stock = remaining
        self.status = OfferStatus(status)

    def deduct_stock(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("수량은 1개 이상이어야 합니다.")
        if self.status != OfferStatus.ON_SALE:
            raise ValueError("판매 중인 상품이 아닙니다.")
        if quantity > self.remaining_stock:
            raise OutOfStockError()
        self.remaining_stock -= quantity
        if self.remaining_stock == 0:
            self.status = OfferStatus.SOLD_OUT

    def restore_stock(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("수량은 1개 이상이어야 합니다.")
        if self.remaining_stock + quantity > self.initial_stock:
            raise ValueError("초기 재고보다 많이 복구할 수 없습니다.")
        self.remaining_stock += quantity
        if self.status == OfferStatus.SOLD_OUT:
            self.status = OfferStatus.ON_SALE
```

상태가 있는 엔티티(예약, 결제)는 허용 전이를 메서드로 만들고, 잘못된 전이는 전용 예외로 막습니다.

## 2. infrastructure/models.py — SQLAlchemy 테이블
```python
import uuid

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class DiscountOfferModel(Base):
    __tablename__ = "discount_offers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), index=True
    )
    sale_price: Mapped[int]
    initial_stock: Mapped[int]
    remaining_stock: Mapped[int]
    status: Mapped[str] = mapped_column(String(20))
    # sales_end, pickup_start, pickup_end 등은 db-schema 6절 참고
```

## 3. infrastructure/repositories.py — 모델 ↔ 도메인 변환
`*Model`을 밖으로 내보내지 않습니다. 조회하면 도메인 객체로 바꿔 반환하고, 저장할 때는 도메인 객체를 받습니다. `commit()`은 서비스가 합니다(레포지토리는 `flush()`까지만). UNIQUE 위반 같은 `IntegrityError`는 레포지토리에서 도메인 예외로 바꿉니다(auth `UserRepository.save` 참고).

```python
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.domain.discount_offer import DiscountOffer, OfferStatus
from catalog.domain.exceptions import OfferNotFoundError
from catalog.infrastructure.models import DiscountOfferModel


class DiscountOfferRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, offer_id: uuid.UUID, for_update: bool = False) -> DiscountOffer | None:
        stmt = select(DiscountOfferModel).where(DiscountOfferModel.id == offer_id)
        if for_update:
            stmt = stmt.with_for_update()  # 재고 차감처럼 동시성이 중요한 곳에서 사용
        model = (await self.db.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def save(self, offer: DiscountOffer) -> DiscountOffer:
        if offer.id is None:
            model = DiscountOfferModel(
                product_id=offer.product_id, sale_price=offer.sale_price,
                initial_stock=offer.initial_stock, remaining_stock=offer.remaining_stock,
                status=str(offer.status),
            )
            self.db.add(model)
            await self.db.flush()
            offer.id = model.id
        else:
            model = await self.db.get(DiscountOfferModel, offer.id)
            if model is None:
                raise OfferNotFoundError("저장할 할인 상품을 찾을 수 없습니다.")
            model.remaining_stock = offer.remaining_stock
            model.status = str(offer.status)
            await self.db.flush()
        return offer

    @staticmethod
    def _to_domain(model: DiscountOfferModel) -> DiscountOffer:
        return DiscountOffer(
            id=model.id, product_id=model.product_id, sale_price=model.sale_price,
            initial_stock=model.initial_stock, remaining_stock=model.remaining_stock,
            status=OfferStatus(model.status),
        )
```

## 4. application/service.py — 흐름과 트랜잭션 조율
비즈니스 판단은 도메인 메서드에 맡기고, 서비스는 조회 → 도메인 메서드 → `save()` → `commit()`만 조율합니다. `HTTPException`을 쓰지 않습니다. 레포지토리는 생성자 키워드 인자로 바꿔 끼울 수 있게 해 두면 DB 없이 서비스 테스트를 할 수 있습니다(auth `AuthApplicationService` 참고).

다른 모듈이 같은 트랜잭션 안에서 부를 메서드는 `commit: bool = True` 키워드 인자를 받습니다.

```python
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from catalog.domain.discount_offer import DiscountOffer
from catalog.domain.exceptions import OfferNotFoundError
from catalog.infrastructure.repositories import DiscountOfferRepository


class CatalogApplicationService:
    def __init__(self, db: AsyncSession, *, offers: DiscountOfferRepository | None = None):
        self.db = db
        self.offers = offers or DiscountOfferRepository(db)

    async def get_offer(self, offer_id: uuid.UUID) -> DiscountOffer:
        offer = await self.offers.find_by_id(offer_id)
        if offer is None:
            raise OfferNotFoundError()
        return offer

    async def deduct_stock(
        self, offer_id: uuid.UUID, quantity: int, *, commit: bool = True
    ) -> DiscountOffer:
        offer = await self.offers.find_by_id(offer_id, for_update=True)
        if offer is None:
            raise OfferNotFoundError()
        offer.deduct_stock(quantity)  # 규칙 검사는 도메인이 함
        await self.offers.save(offer)
        if commit:
            await self.db.commit()
        return offer
```

### 여러 모듈이 얽힌 흐름 (예약 → 재고 차감 → 포인트 사용)
호출하는 쪽 서비스가 **자기 세션으로** 다른 모듈의 서비스를 만들고, `commit=False`로 부른 뒤 마지막에 `commit()`을 한 번만 합니다. 중간에 예외가 나면 커밋되지 않고, 세션이 닫힐 때 롤백됩니다. 다른 모듈의 레포지토리·모델은 직접 쓰지 않고 그 모듈의 application 서비스를 씁니다.

```python
# src/reservations/application/service.py (일부)
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from auth.application.service import AuthApplicationService
from catalog.application.service import CatalogApplicationService


class ReservationApplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.catalog = CatalogApplicationService(db)  # 같은 세션
        self.auth = AuthApplicationService(db)        # 같은 세션

    async def reserve(self, user_id: uuid.UUID, offer_id: uuid.UUID, quantity: int, points: int):
        offer = await self.catalog.deduct_stock(offer_id, quantity, commit=False)
        if points:
            await self.auth.use_points(user_id, points, commit=False)
        # ... 예약 저장 (self.reservations.save(...))
        await self.db.commit()  # 한 번만
        return offer
```

auth가 제공하는 `commit` 인자 메서드: `use_points`, `earn_points`, `restore_points`, `revoke_points`(실제 차감액 반환). 회원 조회는 `get_user(user_id)`입니다.

## 5. presentation/schemas.py — 입출력 검증
```python
import uuid

from pydantic import BaseModel, ConfigDict, Field


class StockDeductRequest(BaseModel):
    quantity: int = Field(..., ge=1, description="차감할 수량")


class DiscountOfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # 도메인 객체를 그대로 직렬화

    id: uuid.UUID = Field(..., description="할인 상품 ID")
    product_id: uuid.UUID = Field(..., description="상품 ID")
    sale_price: int = Field(..., description="할인가(원)")
    remaining_stock: int = Field(..., description="남은 재고")
    status: str = Field(..., description="SCHEDULED / ON_SALE / SOLD_OUT / CLOSED")
```
응답 스키마에 비밀번호 해시 같은 민감 정보를 넣지 않습니다. 필드 이름은 API 명세(`docs/reference/<모듈>.md`)를 따릅니다.

## 6. presentation/router.py — 엔드포인트
router는 서비스만 호출합니다(레포지토리·모델 직접 사용 금지). 예외는 잡지 않고 그대로 올려 전역 핸들러에 맡깁니다. URI는 `/v1`로 시작합니다.

### 인증·권한 사용법
다른 모듈은 `auth.presentation.dependencies`의 타입 별칭을 파라미터 타입으로 씁니다. 토큰이 없거나 잘못되면 401, 역할이 다르면 403이 자동으로 나갑니다.

| 별칭 | 값 | 실패 시 |
| --- | --- | --- |
| `CurrentUser` | 로그인한 `User` | 401 |
| `CustomerUser` / `OwnerUser` / `AdminUser` | 해당 역할의 `User` | 401, 역할 불일치 403 |
| `CurrentPrincipal` | `user`와 토큰 `claims` | 401 (로그아웃처럼 토큰 정보가 필요할 때) |

소유권(본인 매장, 본인 예약) 확인은 의존성이 아니라 도메인·서비스에서 `PermissionError` 하위 예외로 합니다.

```python
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth.presentation.dependencies import CurrentUser, OwnerUser
from catalog.application.service import CatalogApplicationService
from catalog.presentation.schemas import DiscountOfferResponse, StockDeductRequest
from database import get_db

router = APIRouter(prefix="/v1")


def get_catalog_service(db: AsyncSession = Depends(get_db)) -> CatalogApplicationService:
    return CatalogApplicationService(db)


Service = Annotated[CatalogApplicationService, Depends(get_catalog_service)]


@router.get(
    "/offers/{offer_id}",
    response_model=DiscountOfferResponse,
    tags=["카탈로그"],
    summary="할인 상품 상세 조회",
)
async def get_offer(offer_id: uuid.UUID, user: CurrentUser, service: Service):
    return await service.get_offer(offer_id)  # 없으면 OfferNotFoundError → 404


@router.post(
    "/offers/{offer_id}/deduct",
    response_model=DiscountOfferResponse,
    tags=["카탈로그"],
    summary="재고 차감",
)
async def deduct_stock(offer_id: uuid.UUID, body: StockDeductRequest, owner: OwnerUser, service: Service):
    return await service.deduct_stock(offer_id, body.quantity)  # 재고 부족 → 400 OUT_OF_STOCK
```

`get_db`와 인증 의존성이 같은 요청 안에서 같은 세션을 받으므로, 서비스와 인증이 한 세션을 공유합니다.

## 7. main.py 등록 (모듈 밖 수정 범위)
모듈 구현자가 `src/main.py`에서 고치는 것은 아래 두 줄뿐입니다. 그 외 `main.py`, `database.py` 수정이나 `error_handlers.py` 핸들러 추가는 보고서에 적습니다.

```python
# 모든 models.py는 lifespan(create_all)보다 먼저 import해야 테이블이 만들어진다.
from catalog.infrastructure import models as catalog_models  # noqa: F401
from catalog.presentation.router import router as catalog_router

app.include_router(catalog_router)
```
FK가 다른 모듈 테이블을 가리키면(예: `products.store_id` → `stores.id`) 그 모듈의 `models`도 import되어 있어야 `create_all`이 성공합니다.

## 의존성 추가
라이브러리가 필요하면 `pyproject.toml`을 손으로 고치지 않고 `uv add <패키지>`(테스트 전용은 `uv add --dev <패키지>`)를 씁니다. `uv.lock`도 함께 바뀝니다. 추가한 이유를 보고서에 적습니다.

## 마무리 확인
```bash
python3 .claude/skills/layer-check/check_layers.py
cd src && uv run python -c "import main"   # 모든 모듈과 라우터, 핸들러를 함께 불러온다
cd .. && uv run pytest -rs                 # skip이 있으면 이유를 확인한다 (testing.md)
```
