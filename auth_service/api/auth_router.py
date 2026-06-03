# api/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import (
    get_user_auth_service,
    get_current_user,
    get_user_dao,
)
from dao.user_dao import UserDAO
from models.user import User
from schemas.auth import (
    ChangePasswordRequest,
    ChangeEmailRequest,
    RegisterCustomerRequest,
    RegisterEmployeeRequest,
    LoginRequest,
    TokenResponse,
    UserRead,
    RefreshRequest,
    LogoutRequest,
    UserUpdateRequest,
)
from services.user_auth_service import UserAuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register/customer", response_model=TokenResponse)
async def register_customer(
    data: RegisterCustomerRequest,
    auth_service: UserAuthService = Depends(get_user_auth_service),
):
    return await auth_service.register_customer(data)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    auth_service: UserAuthService = Depends(get_user_auth_service),
):
    return await auth_service.login(data)


@router.get("/me", response_model=UserRead)
async def me(
    current_user: User = Depends(get_current_user),
):
    return UserRead(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        role=current_user.role.name if current_user.role else None,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_endpoint(
    data: RefreshRequest,
    auth_service: UserAuthService = Depends(get_user_auth_service),
):
    return await auth_service.refresh(data)


@router.post("/logout", status_code=204)
async def logout_endpoint(
    data: LogoutRequest,
    auth_service: UserAuthService = Depends(get_user_auth_service),
):
    await auth_service.logout(data)
    return

@router.put("/me", response_model=UserRead)
async def update_me(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    dao: UserDAO = Depends(get_user_dao),
):
    user = await dao.update_user_fields(current_user.id, data)
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    dao: UserDAO = Depends(get_user_dao),
):
    ok = await dao.change_password(
        user_id=current_user.id,
        current_password=data.current_password,
        new_password=data.new_password,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )


@router.post("/change-email", response_model=UserRead)
async def change_email(
    data: ChangeEmailRequest,
    current_user: User = Depends(get_current_user),
    dao: UserDAO = Depends(get_user_dao),
):
    try:
        user = await dao.change_email(current_user.id, data.new_email)
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use",
        )

    return user