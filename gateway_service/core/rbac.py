from __future__ import annotations

from fastapi import HTTPException, status

# Требуемые permissions по префиксу пути.
# Более длинный префикс выигрывает.
ACCESS_RULES: dict[str, set[str]] = {
    # Cart
    "/cart": {"cart:write"},

    # Orders
    "/orders/checkout": {"order:create"},
    "/orders/history": {"order:read_own"},
    "/orders": {"order:read_own"},

    # Profile & addresses
    "/profiles/me": {"profile:read_self"},
    "/profiles": {"profile:read_self"},
    "/addresses": {"address:manage_self"},

    # Kitchen
    "/kitchen/jobs": {"kitchen:orders:read"},
    "/kitchen": {"kitchen:orders:update_status"},

    # Delivery
    "/delivery/jobs": {"delivery:jobs:read"},
    "/delivery": {"delivery:jobs:update_status"},

    # Support & notifications
    "/support/threads": {
        "support:threads:read_own",
        "support:threads:create",
        "support:threads:reply_own",
    },
    "/support": {"support:threads:read_own"},
    "/notifications": {"support:threads:read_own"},
}


def get_required_permissions(path: str) -> set[str] | None:
    matched_prefix: str | None = None
    matched_perms: set[str] | None = None

    for prefix, perms in ACCESS_RULES.items():
        if path.startswith(prefix):
            if matched_prefix is None or len(prefix) > len(matched_prefix):
                matched_prefix = prefix
                matched_perms = perms

    return matched_perms


def enforce_rbac(path: str, auth_context: dict | None) -> None:
    required_perms = get_required_permissions(path)
    if required_perms is None:
        # Нет правил — путь считается незаполненным RBAC (пока)
        return

    if auth_context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user_permissions = set(auth_context.get("permissions") or [])

    if not required_perms.issubset(user_permissions):
        missing = required_perms - user_permissions
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permissions: {sorted(missing)}",
        )