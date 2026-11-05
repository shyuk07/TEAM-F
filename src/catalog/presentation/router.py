import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from auth.domain.exceptions import AuthenticationError
from auth.presentation.dependencies import OwnerUser
from catalog.application.service import CatalogApplicationService
from catalog.domain.discount_offer import OfferStatus
from catalog.domain.exceptions import ReservationDataInconsistentError
from catalog.presentation.dependencies import OptionalUser, provide_catalog_service
from catalog.presentation.schemas import (
    OfferCreateRequest,
    OfferDeactivateRequest,
    OfferDeactivateResponse,
    OfferDetailResponse,
    OfferListResponse,
    OfferResponse,
    OfferUpdateRequest,
    ProductCreateRequest,
    ProductDetailResponse,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
    PublicOfferStatus,
    StockAdjustmentRequest,
    StockAdjustmentResponse,
)

router = APIRouter(prefix="/v1", tags=["카탈로그"])

Service = Annotated[CatalogApplicationService, Depends(provide_catalog_service)]
PageParam = Annotated[int, Query(ge=1, description="페이지 (1부터)")]
SizeParam = Annotated[int, Query(ge=1, le=100, description="페이지 크기 (1~100)")]


@router.post(
    "/stores/{store_id}/products",
    response_model=ProductResponse,
    status_code=201,
    summary="상품 등록",
)
async def create_product(
    store_id: uuid.UUID, body: ProductCreateRequest, owner: OwnerUser, service: Service
):
    return await service.create_product(owner.id, store_id, body.model_dump())


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
    is_active: bool = True,
    page: PageParam = 1,
    size: SizeParam = 20,
):
    if not is_active and viewer is None:
        raise AuthenticationError()  # 비활성 상품 조회는 로그인 필요 (D6, CI-3)
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
        list[PublicOfferStatus] | None,
        Query(
            description="SCHEDULED / ON_SALE / SOLD_OUT / CLOSED (반복 가능). "
            "생략하면 SCHEDULED, ON_SALE, SOLD_OUT"
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
