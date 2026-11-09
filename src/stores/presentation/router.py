import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from auth.presentation.dependencies import ApprovedOwnerUser, SuspendedAllowedOwnerUser
from stores.application.query_service import StoreQueryService
from stores.application.service import StoresApplicationService
from stores.presentation.dependencies import provide_store_query_service, provide_stores_service
from stores.presentation.schemas import (
    MyStoreResponse,
    StoreCloseResponse,
    StoreOpenRequest,
    StoreResponse,
)

router = APIRouter(prefix="/v1")

Service = Annotated[StoresApplicationService, Depends(provide_stores_service)]
QueryService = Annotated[StoreQueryService, Depends(provide_store_query_service)]


@router.post(
    "/stores",
    response_model=StoreResponse,
    status_code=201,
    tags=["상점"],
    summary="상점 개설",
)
async def open_store(body: StoreOpenRequest, owner: ApprovedOwnerUser, service: Service):
    return await service.open_store(owner.id, owner.name, body.pickup_address)


# /stores/me는 /stores/{store_id} 형태 경로보다 앞에 선언한다 (D66).
# 나중에 GET /stores/{store_id}가 생겨도 "me"가 UUID 검증에 먼저 걸려 400이 나지 않게 한다.
@router.get(
    "/stores/me",
    response_model=MyStoreResponse,
    tags=["상점"],
    summary="내 상점 조회",
)
async def get_my_store(owner: SuspendedAllowedOwnerUser, query: QueryService):
    return await query.get_store_of_owner(owner.id)


@router.post(
    "/stores/{store_id}/close",
    response_model=StoreCloseResponse,
    status_code=200,
    tags=["상점"],
    summary="상점 폐점",
)
async def close_store(store_id: uuid.UUID, owner: ApprovedOwnerUser, service: Service):
    return await service.close_store(owner.id, store_id)
