"""Pydantic schemas used by FastAPI-Users for User CRUD."""

from uuid import UUID

from fastapi_users import schemas
from pydantic import EmailStr


class UserRead(schemas.BaseUser[UUID]):
    full_name: str | None = None
    password_reset_required: bool = False


class UserCreate(schemas.BaseUserCreate):
    """Used internally by FastAPI-Users. Not exposed at public endpoint —
    user creation goes through the admin route (app/api/v1/admin.py)
    which generates a temp password and sets password_reset_required=True.
    """
    full_name: str | None = None


class UserUpdate(schemas.BaseUserUpdate):
    full_name: str | None = None
