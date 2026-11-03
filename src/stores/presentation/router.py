from typing import Annotated

from fastapi import APIRouter, Depends

from auth.presentation.dependencies import OwnerUser
from stores.application.service import StoresApplicationService
from stores.presentation.dependencies import provide_stores_service
from stores.presentation.schemas import StoreOpenRequest, StoreResponse

router = APIRouter(prefix="/v1")

Service = Annotated[StoresApplicationService, Depends(provide_stores_service)]


@router.post(
    "/stores",
    response_model=StoreResponse,
    status_code=201,
    tags=["상점"],
    summary="상점 개설",
)
async def open_store(body: StoreOpenRequest, owner: OwnerUser, service: Service):
    return await service.open_store(owner.id, owner.name, body.pickup_address)
