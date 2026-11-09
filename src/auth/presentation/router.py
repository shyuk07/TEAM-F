import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from auth.application.password_reset_service import PasswordResetService
from auth.application.service import AuthApplicationService
from auth.application.withdrawal_service import AccountWithdrawalService
from auth.domain.point_log import PointType
from auth.domain.user import Role, UserStatus
from auth.presentation.dependencies import (
    AdminUser,
    CurrentPrincipal,
    CurrentUser,
    PrincipalAllowSuspended,
    provide_auth_service,
    provide_password_reset_service,
    provide_withdrawal_service,
)
from auth.presentation.schemas import (
    AdminUserListResponse,
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PointLogListResponse,
    ProfileUpdateRequest,
    PurgeTokensResponse,
    SignupRequest,
    TokenResponse,
    UserResponse,
    WithdrawalResponse,
    WithdrawRequest,
)

router = APIRouter(prefix="/v1")

Service = Annotated[AuthApplicationService, Depends(provide_auth_service)]
ResetService = Annotated[PasswordResetService, Depends(provide_password_reset_service)]
WithdrawalService = Annotated[AccountWithdrawalService, Depends(provide_withdrawal_service)]


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
    result = await service.login(body.email, body.password)
    return TokenResponse(access_token=result.token, token_type="bearer", status=result.status)


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["인증"],
    summary="로그아웃",
)
async def logout(principal: PrincipalAllowSuspended, service: Service):
    await service.logout(principal.claims)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/auth/password-reset/request",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["인증"],
    summary="비밀번호 재설정 코드 요청 (가입 여부와 무관하게 204)",
)
async def request_password_reset(body: PasswordResetRequest, service: ResetService):
    await service.request_reset(body.email)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/auth/password-reset/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["인증"],
    summary="비밀번호 재설정 확인",
)
async def confirm_password_reset(body: PasswordResetConfirmRequest, service: ResetService):
    await service.confirm_reset(body.email, body.code, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users/me", response_model=UserResponse, tags=["회원"], summary="내 정보 조회")
async def read_me(user: CurrentUser):
    return user


@router.patch("/users/me", response_model=UserResponse, tags=["회원"], summary="프로필 변경")
async def update_me(body: ProfileUpdateRequest, user: CurrentUser, service: Service):
    return await service.update_profile(user.id, body.name, body.phone)


@router.post(
    "/users/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["회원"],
    summary="비밀번호 변경 (이 토큰 외 기존 토큰 무효)",
)
async def change_my_password(
    body: PasswordChangeRequest, principal: CurrentPrincipal, service: Service
):
    await service.change_password(
        principal.user.id,
        body.current_password,
        body.new_password,
        keep_jti=principal.claims.jti,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/users/me/withdraw",
    response_model=WithdrawalResponse,
    tags=["회원"],
    summary="회원 탈퇴 (예약 취소·환불·포인트 소멸)",
)
async def withdraw_me(body: WithdrawRequest, user: CurrentUser, service: WithdrawalService):
    return await service.withdraw_self(user.id, body.password)


@router.get(
    "/users/me/points",
    response_model=PointLogListResponse,
    tags=["회원"],
    summary="포인트 내역 조회",
)
async def read_my_points(
    user: CurrentUser,
    service: Service,
    type: Annotated[PointType | None, Query(description="EARN / USE / RESTORE / REVOKE / GRANT / EXPIRE")] = None,
    page: Annotated[int, Query(ge=0, description="페이지 (0부터)")] = 0,
    size: Annotated[int, Query(ge=1, le=100, description="페이지 크기 (최대 100)")] = 20,
):
    return await service.list_point_logs(user, type, page, size)


@router.get(
    "/admin/users",
    response_model=AdminUserListResponse,
    tags=["관리자"],
    summary="회원 목록 조회(관리자)",
)
async def admin_list_users(
    admin: AdminUser,
    service: Service,
    role: Annotated[Role | None, Query(description="CUSTOMER / OWNER / ADMIN")] = None,
    status_filter: Annotated[
        UserStatus | None,
        Query(
            alias="status",
            description="PENDING / APPROVED / REJECTED / SUSPENDED / WITHDRAWN (기간이 지난 정지는 APPROVED)",
        ),
    ] = None,
    email: Annotated[str | None, Query(max_length=255, description="이메일 부분 검색")] = None,
    page: Annotated[int, Query(ge=0, description="페이지 (0부터)")] = 0,
    size: Annotated[int, Query(ge=1, le=100, description="페이지 크기 (최대 100)")] = 20,
):
    page_result = await service.list_users(role, status_filter, email, page, size)
    return AdminUserListResponse(
        users=page_result.items,
        page=page_result.page,
        size=page_result.size,
        total_elements=page_result.total_elements,
    )


@router.get(
    "/admin/users/{user_id}",
    response_model=UserResponse,
    tags=["관리자"],
    summary="회원 조회(관리자)",
)
async def admin_read_user(user_id: uuid.UUID, admin: AdminUser, service: Service):
    return await service.get_user(user_id)


@router.post(
    "/admin/token-blacklist/purge",
    response_model=PurgeTokensResponse,
    tags=["관리자"],
    summary="만료된 블랙리스트 토큰 정리",
)
async def admin_purge_tokens(admin: AdminUser, service: Service):
    return PurgeTokensResponse(deleted_count=await service.purge_expired_tokens())
