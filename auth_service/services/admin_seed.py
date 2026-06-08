import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import get_session  # может пригодиться, если будешь вызывать seed_rbac из lifespan
from dao.user_dao import UserDAO  # можно убрать, если здесь не используешь
from services.password_service import hash_password  # возможно больше не нужен тут
from models.role import Role, Permission, RolePermission  # общие RBAC-модели

# Роли для всей системы (обычные пользователи)
ROLE_DEFINITIONS = {
    "customer": "Customer / buyer role",
    "cook": "Kitchen staff role",
    "courier": "Delivery staff role",
    "admin": "Administrator role with full access",
}

# Permissions по доменам пиццерии
PERMISSION_DEFINITIONS = {
    # Catalog & Store (публичное чтение + внутреннее использование)
    "catalog:read": "Read product catalog",
    "store:read": "Read stores and delivery zones",

    # Customer features
    "profile:read_self": "Read own profile",
    "profile:update_self": "Update own profile",
    "address:manage_self": "Manage own delivery addresses",

    "cart:write": "Manage cart",
    "order:create": "Create order",
    "order:read_own": "Read own orders",

    # Kitchen / Delivery domain
    "kitchen:orders:read": "View orders in kitchen",
    "kitchen:orders:update_status": "Update kitchen order status",

    "delivery:jobs:read": "View delivery jobs",
    "delivery:jobs:update_status": "Update delivery status",
    "delivery:location:update": "Update courier location",

    # Support
    "support:threads:read_own": "Read own support threads",
    "support:threads:create": "Create support thread",
    "support:threads:reply_own": "Reply in own threads",
}

# Маппинг ролей на permissions
ROLE_PERMISSIONS = {
    # Покупатель
    "customer": {
        "catalog:read",
        "store:read",
        "profile:read_self",
        "profile:update_self",
        "address:manage_self",
        "cart:write",
        "order:create",
        "order:read_own",
        "support:threads:read_own",
        "support:threads:create",
        "support:threads:reply_own",
    },

    # Повар
    "cook": {
        "kitchen:orders:read",
        "kitchen:orders:update_status",
        "order:read_own",  # чтение только своих заказов кухни, если так решишь
        "store:read",
        "catalog:read",
    },

    # Курьер
    "courier": {
        "delivery:jobs:read",
        "delivery:jobs:update_status",
        "delivery:location:update",
        "order:read_own",  # чтение только своих доставляемых заказов
        "store:read",
    },
    "admin": set(PERMISSION_DEFINITIONS.keys()),
}


async def seed_rbac(session: AsyncSession) -> None:
    role_map: dict[str, Role] = {}
    permission_map: dict[str, Permission] = {}

    # роли
    for role_name, description in ROLE_DEFINITIONS.items():
        existing = await session.scalar(select(Role).where(Role.name == role_name))
        if existing is None:
            existing = Role(name=role_name, description=description)
            session.add(existing)
            await session.flush()
        role_map[role_name] = existing

    # permissions
    for code, description in PERMISSION_DEFINITIONS.items():
        existing = await session.scalar(select(Permission).where(Permission.code == code))
        if existing is None:
            existing = Permission(code=code, description=description)
            session.add(existing)
            await session.flush()
        permission_map[code] = existing

    # связи роль–permission
    for role_name, permission_codes in ROLE_PERMISSIONS.items():
        role = role_map[role_name]
        for code in permission_codes:
            permission = permission_map[code]
            existing_link = await session.scalar(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
            )
            if existing_link is None:
                session.add(RolePermission(role_id=role.id, permission_id=permission.id))

    await session.commit()