from fastapi import HTTPException, status

from core.config import settings


SERVICE_MAP = {
    "/auth": settings.AUTH_SERVICE_URL,
    "/profiles": settings.PROFILE_SERVICE_URL,
    "/catalog": settings.CATALOG_SERVICE_URL,
    "/stores": settings.STORE_SERVICE_URL,
    "/orders": settings.ORDER_SERVICE_URL,
    "/cart": settings.ORDER_SERVICE_URL,
    "/kitchen": settings.KITCHEN_SERVICE_URL,
    "/delivery": settings.DELIVERY_SERVICE_URL,
    "/support": settings.SUPPORT_CHAT_SERVICE_URL,
    "/notifications": settings.NOTIFICATION_SERVICE_URL,
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