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

__all__ = [
    "auth_backend",
    "current_active_user",
    "current_optional_user",
    "current_superuser",
    "current_user",
    "fastapi_users",
    "get_user_db",
    "get_user_manager",
    "jwt_strategy",
]
