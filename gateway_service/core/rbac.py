from __future__ import annotations

from fastapi import HTTPException, status

ROLE_RULES: dict[str, set[str]] = {
    "/cart": {"customer"},
    "/orders/checkout": {"customer"},
    "/orders/history": {"customer"},
    "/orders": {"customer", "support", "admin"},
    "/profiles": {"customer", "cook", "courier", "support", "admin"},
    "/kitchen": {"cook", "admin"},
    "/delivery": {"courier", "admin"},
    "/support": {"customer", "support", "admin"},
    "/notifications": {"customer", "support", "admin"},
}

def get_allowed_roles(path: str) -> set[str] | None:
    matched_prefix = None
    matched_roles = None

    for prefix, roles in ROLE_RULES.items():
        if path.startswith(prefix):
            if matched_prefix is None or len(prefix) > len(matched_prefix):
                matched_prefix = prefix
                matched_roles = roles

    return matched_roles

def enforce_rbac(path: str, auth_context: dict | None) -> None:
    allowed_roles = get_allowed_roles(path)
    if allowed_roles is None:
        return

    if auth_context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    role = auth_context.get("role")
    if role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' is not allowed to access this resource",
        )