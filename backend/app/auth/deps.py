"""FastAPI-Users dependencies — the auth deps every route uses."""

from uuid import UUID

from fastapi_users import FastAPIUsers

from app.auth.backend import auth_backend
from app.auth.db import get_user_db
from app.auth.manager import get_user_manager
from app.models.user import User


fastapi_users = FastAPIUsers[User, UUID](get_user_manager, [auth_backend])

# Strict — raises 401 if no/invalid token.
current_user = fastapi_users.current_user(active=False)
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)

# Lenient — returns None if no/invalid token. Useful for routes that
# behave differently for anon vs. signed-in (e.g., health, marketing).
current_optional_user = fastapi_users.current_user(optional=True)


__all__ = [
    "fastapi_users",
    "current_user",
    "current_active_user",
    "current_superuser",
    "current_optional_user",
    "get_user_db",
    "get_user_manager",
]
