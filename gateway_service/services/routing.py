from fastapi import HTTPException, status
from core.config import settings


SERVICE_MAP = {
    "/api/v1/auth": settings.AUTH_SERVICE_URL,
    "/api/v1/profiles": settings.PROFILE_SERVICE_URL,
    "/api/v1/catalog": settings.CATALOG_SERVICE_URL,
    "/api/v1/stores": settings.STORE_SERVICE_URL,
    "/api/v1/orders": settings.ORDER_SERVICE_URL,
    "/api/v1/cart": settings.ORDER_SERVICE_URL,
    "/api/v1/kitchen": settings.KITCHEN_SERVICE_URL,
    "/api/v1/delivery": settings.DELIVERY_SERVICE_URL,
    "/api/v1/support": settings.SUPPORT_CHAT_SERVICE_URL,
    "/api/v1/notifications": settings.NOTIFICATION_SERVICE_URL,
}


def resolve_service(path: str) -> str:
    matched_prefix: str | None = None
    matched_target: str | None = None

    for prefix, target in SERVICE_MAP.items():
        if path.startswith(prefix):
            if matched_prefix is None or len(prefix) > len(matched_prefix):
                matched_prefix = prefix
                matched_target = target

    if matched_target:
        return matched_target

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Route not found",
    )