from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rbac import Permission, RolePermission, UserRole


def permission_codes_for_user(db: Session, *, user_id: str) -> set[str]:
    return set(
        db.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user_id)
        )
        .scalars()
        .all()
    )


def user_has_any_permission(db: Session, *, user_id: str, required_permissions: tuple[str, ...] | list[str] | set[str]) -> bool:
    required = tuple(required_permissions)
    if not required:
        return True
    return bool(permission_codes_for_user(db, user_id=user_id).intersection(required))
