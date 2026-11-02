from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from auth.application.service import AuthApplicationService
from auth.domain.point_log import PointType
from auth.presentation.dependencies import (
    CurrentPrincipal,
    CurrentUser,
    get_auth_service,
)
from auth.presentation.schemas import (
    LoginRequest,
    PointLogListResponse,
    SignupRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/v1")

Service = Annotated[AuthApplicationService, Depends(get_auth_service)]


@router.post(
    "/auth/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["인증"],
    summary="회원가입",
)
async def signup(body: SignupRequest, service: Service):
    return await service.signup(
        email=body.email,
        password=body.password,
        role=body.role,
        name=body.name,
        phone=body.phone,
    )


@router.post("/auth/login", response_model=TokenResponse, tags=["인증"], summary="로그인")
async def login(body: LoginRequest, service: Service):
    token = await service.login(body.email, body.password)
    return TokenResponse(access_token=token, token_type="bearer")


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["인증"],
    summary="로그아웃",
)
async def logout(principal: CurrentPrincipal, service: Service):
    await service.logout(principal.claims)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users/me", response_model=UserResponse, tags=["회원"], summary="내 정보 조회")
async def read_me(user: CurrentUser):
    return user


@router.get(
    "/users/me/points",
    response_model=PointLogListResponse,
    tags=["회원"],
    summary="포인트 내역 조회",
)
async def read_my_points(
    user: CurrentUser,
    service: Service,
    type: Annotated[PointType | None, Query(description="EARN / USE / RESTORE / REVOKE")] = None,
    page: Annotated[int, Query(ge=0, description="페이지 (0부터)")] = 0,
    size: Annotated[int, Query(ge=1, le=100, description="페이지 크기 (최대 100)")] = 20,
):
    return await service.list_point_logs(user, type, page, size)
