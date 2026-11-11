import uuid
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, UploadFile
from fastapi.routing import APIRoute

from auth.presentation.dependencies import OwnerUser
from catalog.application.service import CatalogApplicationService
from catalog.domain.exceptions import ImageTooLargeError
from catalog.domain.product_image import MAX_IMAGE_BYTES
from catalog.presentation.dependencies import provide_catalog_service
from catalog.presentation.schemas import ProductImageResponse

# D103, Q55: 이미지 id는 불변 리소스지만 삭제 반영 지연을 1시간으로 제한한다.
IMAGE_RESPONSE_HEADERS = {
    "Cache-Control": "public, max-age=3600",
    "X-Content-Type-Options": "nosniff",
}
# multipart 경계·헤더 여유 64 KiB
MAX_UPLOAD_REQUEST_BYTES = MAX_IMAGE_BYTES + 64 * 1024


class UploadSizeLimitRoute(APIRoute):
    """본문이 읽히기(임시 파일로 받아지기) 전에 Content-Length로 크기를 거른다 (B-IMG4, 인증보다 먼저)."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            length = request.headers.get("content-length")
            if length is not None and length.isdigit() and int(length) > MAX_UPLOAD_REQUEST_BYTES:
                raise ImageTooLargeError()
            return await original(request)

        return handler


class MultipartSizeLimitRoute(UploadSizeLimitRoute):
    """multipart일 때만 Content-Length를 사전 검사한다 (D114). JSON 요청 동작은 바꾸지 않는다."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super(UploadSizeLimitRoute, self).get_route_handler()
        limited = super().get_route_handler()

        async def handler(request: Request) -> Response:
            content_type = request.headers.get("content-type", "").lower()
            if content_type.startswith("multipart/form-data"):
                return await limited(request)
            return await original(request)

        return handler


image_router = APIRouter(route_class=UploadSizeLimitRoute, tags=["카탈로그"])

Service = Annotated[CatalogApplicationService, Depends(provide_catalog_service)]


@image_router.post(
    "/products/{product_id}/images",
    response_model=ProductImageResponse,
    status_code=201,
    summary="상품 이미지 업로드",
)
async def upload_product_image(
    product_id: uuid.UUID, owner: OwnerUser, service: Service, file: UploadFile
):
    data = await file.read(MAX_IMAGE_BYTES + 1)  # 최대 5 MiB+1바이트만 메모리에 올린다
    result = await service.upload_product_image(owner.id, product_id, data)
    return ProductImageResponse.from_result(result)


@image_router.delete(
    "/products/{product_id}/images/{image_id}",
    status_code=204,
    response_class=Response,
    summary="상품 이미지 삭제",
)
async def delete_product_image(
    product_id: uuid.UUID, image_id: uuid.UUID, owner: OwnerUser, service: Service
):
    await service.delete_product_image(owner.id, product_id, image_id)
    return Response(status_code=204)


@image_router.get(
    "/products/{product_id}/images/{image_id}",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}, "image/png": {}, "image/webp": {}}}},
    summary="상품 이미지 조회",
)
async def get_product_image(product_id: uuid.UUID, image_id: uuid.UUID, service: Service):
    image = await service.get_product_image(product_id, image_id)
    return Response(
        content=image.data, media_type=image.content_type, headers=IMAGE_RESPONSE_HEADERS
    )
