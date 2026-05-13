"""Auth module — FastAPI-Users wiring.

Public exports:
- fastapi_users: the configured FastAPIUsers instance (route factory)
- current_user, current_active_user, current_superuser: deps
- get_user_manager, get_user_db: deps used by FastAPI-Users routers
"""

from app.auth.backend import auth_backend, jwt_strategy
from app.auth.deps import (
    current_active_user,
    current_optional_user,
    current_superuser,
    current_user,
    fastapi_users,
    get_user_db,
    get_user_manager,
)
from app.auth.guards import (
    admin_org_ids_for,
    ensure_not_last_admin_demotion,
    ensure_not_self_superadmin_demote,
    require_org_admin_or_superuser,
    require_org_member_or_superuser,
    user_is_admin_of_org,
    user_is_member_of_org,
)

__all__ = [
    "admin_org_ids_for",
    "auth_backend",
    "current_active_user",
    "current_optional_user",
    "current_superuser",
    "current_user",
    "ensure_not_last_admin_demotion",
    "ensure_not_self_superadmin_demote",
    "fastapi_users",
    "get_user_db",
    "get_user_manager",
    "jwt_strategy",
    "require_org_admin_or_superuser",
    "require_org_member_or_superuser",
    "user_is_admin_of_org",
    "user_is_member_of_org",
]
