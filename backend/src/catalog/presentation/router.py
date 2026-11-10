import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.datastructures import UploadFile as StarletteUploadFile

from auth.presentation.dependencies import OwnerUser
from catalog.application.service import CatalogApplicationService
from catalog.domain.discount_offer import OfferStatus
from catalog.domain.search import OfferSort
from catalog.domain.exceptions import ReservationDataInconsistentError
from catalog.presentation.dependencies import OptionalUser, provide_catalog_service
from catalog.domain.product_image import MAX_IMAGE_BYTES
from catalog.presentation.image_router import MultipartSizeLimitRoute, image_router
from catalog.presentation.schemas import (
    OfferCreateRequest,
    OfferDeactivateRequest,
    OfferDeactivateResponse,
    OfferDetailResponse,
    OfferListResponse,
    NearbyOfferItem,
    NearbyOfferListResponse,
    OfferResponse,
    OfferUpdateRequest,
    ProductCreateRequest,
    ProductDetailResponse,
    ProductListResponse,
    ProductSearchResponse,
    StoreSearchItem,
    ProductResponse,
    ProductUpdateRequest,
    OfferListStatus,
    PublicOfferStatus,
    StockAdjustmentRequest,
    StockAdjustmentResponse,
)

router = APIRouter(prefix="/v1", tags=["카탈로그"])

Service = Annotated[CatalogApplicationService, Depends(provide_catalog_service)]
PageParam = Annotated[int, Query(ge=1, description="페이지 (1부터)")]
SizeParam = Annotated[int, Query(ge=1, le=100, description="페이지 크기 (1~100)")]


_CREATE_PRODUCT_FORM_PROPS = {
    "name": {"type": "string"},
    "category": {"type": "string"},
    "description": {"type": "string"},
    "original_price": {"type": "integer"},
    "file": {"type": "string", "format": "binary"},
}
_CREATE_PRODUCT_OPENAPI = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/ProductCreateRequest"}},
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["name", "original_price"],
                    "properties": _CREATE_PRODUCT_FORM_PROPS,
                }
            },
        },
    }
}


class BodyParseError(ValueError):
    """본문을 읽지 못함. FastAPI 기본 동작(400 HTTP_ERROR)과 같은 응답을 내되 router에서 HTTPException을 만들지 않는다(R6)."""

    error_code = "HTTP_ERROR"

    def __init__(self, message: str = "There was an error parsing the body"):
        super().__init__(message)


def _form_error(field: str, message: str) -> RequestValidationError:
    return RequestValidationError([{"loc": ("body", field), "msg": message, "type": "value_error"}])


async def _read_json_body(request: Request) -> tuple[dict, None]:
    raw = await request.body()
    if not raw:  # FastAPI: 빈 본문은 body 필드 누락(missing)
        raise RequestValidationError([{"type": "missing", "loc": ("body",), "msg": "Field required", "input": None}])
    try:
        parsed = json.loads(raw)  # FastAPI와 같은 방식으로 디코드한다
    except json.JSONDecodeError as e:
        raise RequestValidationError(
            [
                {
                    "type": "json_invalid",
                    "loc": ("body", e.pos),
                    "msg": "JSON decode error",
                    "input": {},
                    "ctx": {"error": e.msg},
                }
            ],
            body=e.doc,
        ) from e
    except Exception as e:  # 인코딩 오류 등. FastAPI는 HTTPException(400)으로 바꾼다 -> HTTP_ERROR
        raise BodyParseError() from e
    try:
        body = ProductCreateRequest.model_validate(parsed, from_attributes=True)  # FastAPI와 같은 검증 모드
    except ValidationError as e:
        raise RequestValidationError(e.errors()) from e
    return body.model_dump(), None


async def _read_multipart_body(request: Request) -> tuple[dict, bytes | None]:
    form = await request.form()
    raw: dict = {}
    for key in ("name", "category", "description", "original_price"):
        value = form.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            raise _form_error(key, "문자열이어야 합니다")
        if key in ("category", "description") and value == "":
            continue  # Q58: 비운 입력은 없음
        raw[key] = value
    try:
        data = ProductCreateRequest.model_validate(raw).model_dump()
    except ValidationError as e:
        raise RequestValidationError(e.errors()) from e
    data["product_image"] = None  # Q60: product_image 폼 필드는 무시
    files = form.getlist("file")
    if not files:
        return data, None
    if len(files) > 1 or not isinstance(files[0], StarletteUploadFile):
        raise _form_error("file", "사진은 1장만 보낼 수 있습니다")
    return data, await files[0].read(MAX_IMAGE_BYTES + 1)


_create_product_router = APIRouter(route_class=MultipartSizeLimitRoute, tags=["카탈로그"])


@_create_product_router.post(
    "/stores/{store_id}/products",
    response_model=ProductResponse,
    status_code=201,
    summary="상품 등록",
    openapi_extra=_CREATE_PRODUCT_OPENAPI,
)
async def create_product(store_id: uuid.UUID, request: Request, owner: OwnerUser, service: Service):
    if request.headers.get("content-type", "").lower().startswith("multipart/form-data"):
        data, image_data = await _read_multipart_body(request)
    else:
        data, image_data = await _read_json_body(request)
    return await service.create_product(owner.id, store_id, data, image_data)


router.include_router(_create_product_router)


@router.get(
    "/stores/{store_id}/products",
    response_model=ProductListResponse,
    summary="상점 상품 목록",
)
async def list_products(
    store_id: uuid.UUID,
    viewer: OptionalUser,
    service: Service,
    category: str | None = None,
    is_active: bool | None = None,
    page: PageParam = 1,
    size: SizeParam = 20,
):
    return await service.list_products(
        viewer.id if viewer else None, store_id, category, is_active, page, size
    )


@router.get(
    "/stores/{store_id}/offers",
    response_model=OfferListResponse,
    summary="상점 할인 목록",
)
async def list_store_offers(
    store_id: uuid.UUID,
    viewer: OptionalUser,
    service: Service,
    status: Annotated[
        list[OfferListStatus] | None,
        Query(
            description="SCHEDULED / ON_SALE / SOLD_OUT / CLOSED / SUSPENDED(상점주만) (반복 가능). "
            "생략하면 SCHEDULED, ON_SALE, SOLD_OUT (상점주는 SUSPENDED 포함)"
        ),
    ] = None,
    page: PageParam = 1,
    size: SizeParam = 20,
):
    statuses = [OfferStatus(s) for s in status] if status else None
    result = await service.list_offers_by_store(
        viewer.id if viewer else None, store_id, statuses, page, size
    )
    return OfferListResponse(
        items=[OfferResponse.from_view(v) for v in result.items],
        page=result.page,
        size=result.size,
        total=result.total,
    )


LatParam = Annotated[float | None, Query(ge=-90, le=90, description="위도 (lng와 함께)")]
LngParam = Annotated[float | None, Query(ge=-180, le=180, description="경도 (lat과 함께)")]
RadiusParam = Annotated[float | None, Query(ge=0.1, le=20, description="검색 반경 km (기본 3)")]


@router.get("/products", response_model=ProductSearchResponse, summary="상품 검색")
async def search_products(
    service: Service,
    keyword: Annotated[str | None, Query(max_length=100, description="상품명·설명 검색어")] = None,
    category: Annotated[str | None, Query(max_length=80)] = None,
    lat: LatParam = None,
    lng: LngParam = None,
    radius_km: RadiusParam = None,
    page: PageParam = 1,
    size: SizeParam = 20,
):
    result = await service.search_products(
        keyword=keyword, category=category, lat=lat, lng=lng, radius_km=radius_km, page=page, size=size
    )
    return ProductSearchResponse(
        items=[StoreSearchItem.from_hit(h) for h in result.items],
        page=result.page,
        size=result.size,
        total=result.total,
    )


@router.get("/offers", response_model=NearbyOfferListResponse, summary="주변 할인 목록")
async def list_nearby_offers(
    service: Service,
    lat: LatParam = None,
    lng: LngParam = None,
    radius_km: RadiusParam = None,
    category: Annotated[str | None, Query(max_length=80)] = None,
    keyword: Annotated[str | None, Query(max_length=100, description="상품명 검색어")] = None,
    status: PublicOfferStatus = PublicOfferStatus.ON_SALE,
    sort: OfferSort = OfferSort.SALES_END,
    page: PageParam = 1,
    size: SizeParam = 20,
):
    result = await service.list_nearby_offers(
        lat=lat, lng=lng, radius_km=radius_km, category=category, keyword=keyword,
        status=OfferStatus(status), sort=sort, page=page, size=size,
    )
    return NearbyOfferListResponse(
        items=[NearbyOfferItem.from_view(v) for v in result.items],
        page=result.page,
        size=result.size,
        total=result.total,
    )


@router.get(
    "/products/{product_id}",
    response_model=ProductDetailResponse,
    summary="상품 상세",
)
async def get_product(product_id: uuid.UUID, viewer: OptionalUser, service: Service):
    view = await service.get_product(viewer.id if viewer else None, product_id)
    return ProductDetailResponse(
        **ProductResponse.model_validate(view.product).model_dump(),
        store_name=view.store_name,
        pickup_address=view.pickup_address,
    )


@router.patch(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="상품 수정",
)
async def update_product(
    product_id: uuid.UUID, body: ProductUpdateRequest, owner: OwnerUser, service: Service
):
    return await service.update_product(owner.id, product_id, body.model_dump(exclude_unset=True))


@router.post(
    "/products/{product_id}/deactivate",
    response_model=ProductResponse,
    summary="상품 노출 중단",
)
async def deactivate_product(product_id: uuid.UUID, owner: OwnerUser, service: Service):
    return await service.deactivate_product(owner.id, product_id)


@router.post(
    "/products/{product_id}/activate",
    response_model=ProductResponse,
    summary="상품 재노출",
)
async def activate_product(product_id: uuid.UUID, owner: OwnerUser, service: Service):
    return await service.reactivate_product(owner.id, product_id)


@router.post(
    "/products/{product_id}/offers",
    response_model=OfferResponse,
    status_code=201,
    summary="할인 등록",
)
async def register_offer(
    product_id: uuid.UUID, body: OfferCreateRequest, owner: OwnerUser, service: Service
):
    view = await service.register_offer(owner.id, product_id, body.model_dump())
    return OfferResponse.from_view(view)


@router.get(
    "/offers/{offer_id}",
    response_model=OfferDetailResponse,
    summary="할인 상세",
)
async def get_offer_detail(offer_id: uuid.UUID, viewer: OptionalUser, service: Service):
    view = await service.get_offer_detail(viewer.id if viewer else None, offer_id)
    return OfferDetailResponse.from_view(view)


@router.patch(
    "/offers/{offer_id}",
    response_model=OfferResponse,
    summary="할인 수정",
)
async def update_offer(
    offer_id: uuid.UUID, body: OfferUpdateRequest, owner: OwnerUser, service: Service
):
    view = await service.update_offer(owner.id, offer_id, body.model_dump(exclude_unset=True))
    return OfferResponse.from_view(view)


@router.post(
    "/offers/{offer_id}/deactivate",
    response_model=OfferDeactivateResponse,
    summary="할인 판매 중단",
)
async def deactivate_offer(
    offer_id: uuid.UUID, body: OfferDeactivateRequest, owner: OwnerUser, service: Service
):
    try:
        result = await service.deactivate_offer(owner.id, offer_id, body.reason, body.cancel_reservations)
    except ReservationDataInconsistentError as error:
        # 예약 서비스가 이미 롤백하고 ERROR 로그를 1건 남겼다. 여기서는 공통 형식의 500 응답만 만든다(로그 없음).
        return JSONResponse(
            status_code=500,
            content={"success": False, "error_code": error.error_code, "message": str(error)},
        )
    return OfferDeactivateResponse.from_result(result)


@router.post(
    "/offers/{offer_id}/relist",
    response_model=OfferResponse,
    status_code=201,
    summary="할인 재등록",
)
async def relist_offer(
    offer_id: uuid.UUID, body: OfferCreateRequest, owner: OwnerUser, service: Service
):
    view = await service.relist_offer(owner.id, offer_id, body.model_dump())
    return OfferResponse.from_view(view)


@router.post(
    "/offers/{offer_id}/stock-adjustments",
    response_model=StockAdjustmentResponse,
    summary="재고 수동 조정",
)
async def adjust_stock(
    offer_id: uuid.UUID, body: StockAdjustmentRequest, owner: OwnerUser, service: Service
):
    result = await service.adjust_stock(owner.id, offer_id, body.amount, body.reason)
    return StockAdjustmentResponse.from_result(result)


router.include_router(image_router)
