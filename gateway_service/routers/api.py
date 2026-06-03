# routers/api.py
from fastapi import APIRouter, Request, HTTPException, status
import httpx

from core.security import get_auth_context
from core.config import settings
from services.proxy_service import forward_request

router = APIRouter()


@router.get("/api/me")
async def get_full_me(request: Request):
    # auth_context уже валидирован security (type=access, principal_type=user)
    auth_context = await get_auth_context(request)
    user_id = auth_context["sub"]

    # забираем /auth/me
    async with httpx.AsyncClient(base_url=settings.AUTH_SERVICE_URL, timeout=5.0) as client:
        auth_resp = await client.get(
            "/auth/me",
            headers={"Authorization": request.headers.get("authorization", "")},
        )
    if auth_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Auth service /auth/me error: {auth_resp.status_code}",
        )

    user_data = auth_resp.json()

    # забираем /profiles/me
    # Прокидываем x-user-id, как это делает gateway
    async with httpx.AsyncClient(base_url=settings.PROFILE_SERVICE_URL, timeout=5.0) as client:
        profile_resp = await client.get(
            "/profiles/me",
            headers={
                "x-user-id": str(user_id),
            },
        )

    if profile_resp.status_code == 404:
        profile_data = None
    elif profile_resp.status_code == 200:
        profile_data = profile_resp.json()
    else:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Profile service /profiles/me error: {profile_resp.status_code}",
        )

    return {
        "user": user_data,
        "profile": profile_data,
    }

@router.api_route(
    "/api/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def proxy_all(request: Request, full_path: str):
    internal_path = "/" + full_path
    auth_context = await get_auth_context(request)
    return await forward_request(
        request=request,
        path=internal_path,
        auth_context=auth_context,
    )

