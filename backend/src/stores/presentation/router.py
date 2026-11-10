import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from auth.presentation.dependencies import ApprovedOwnerUser
from stores.application.service import StoresApplicationService
from stores.presentation.dependencies import provide_stores_service
from stores.presentation.schemas import (
    StoreCloseResponse,
    StoreOpenRequest,
    StoreResponse,
)

router = APIRouter(prefix="/v1")

Service = Annotated[StoresApplicationService, Depends(provide_stores_service)]


@router.post(
    "/stores",
    response_model=StoreResponse,
    status_code=201,
    tags=["상점"],
    summary="상점 개설",
)
async def open_store(body: StoreOpenRequest, owner: ApprovedOwnerUser, service: Service):
    return await service.open_store(owner.id, owner.name, body.pickup_address)


@router.post(
    "/stores/{store_id}/close",
    response_model=StoreCloseResponse,
    status_code=200,
    tags=["상점"],
    summary="상점 폐점",
)
async def close_store(store_id: uuid.UUID, owner: ApprovedOwnerUser, service: Service):
    return await service.close_store(owner.id, store_id)
