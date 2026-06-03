# api/dependencies.py (profile_service)

from fastapi import Header, HTTPException, status  # <--- обязательно есть Header

async def get_current_user_id(
    x_user_id: str | None = Header(default=None, alias="x-user-id"),
) -> int:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID header missing",
        )
    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-User-Id header",
        )