"""Current-user endpoints — profile + mandatory first-login password reset."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users.password import PasswordHelper
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.auth.schemas import UserRead
from app.core.database import get_db
from app.models.user import User


router = APIRouter(tags=["me"])
_password_helper = PasswordHelper()


@router.get("/me", response_model=UserRead)
async def get_me(user: User = Depends(current_active_user)) -> User:
    """Returns the currently authenticated user."""
    return user


class MyAdminOrgsOut(BaseModel):
    is_superuser: bool
    admin_org_ids: list[str]


@router.get("/me/admin-orgs", response_model=MyAdminOrgsOut)
async def get_my_admin_orgs(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> MyAdminOrgsOut:
    """Returns the orgs the caller can admin. Used by the frontend to decide
    whether to show the Admin sidebar group."""
    from app.auth.guards import admin_org_ids_for

    org_ids = await admin_org_ids_for(session, user)
    return MyAdminOrgsOut(
        is_superuser=user.is_superuser,
        admin_org_ids=[str(i) for i in org_ids],
    )


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=10)


class PasswordChangeOut(BaseModel):
    ok: bool = True
    password_reset_required: bool = False


@router.post("/me/password", response_model=PasswordChangeOut)
async def change_password(
    body: PasswordChangeIn,
    user: Annotated[User, Depends(current_active_user)],
    session: AsyncSession = Depends(get_db),
) -> PasswordChangeOut:
    """Change current user's password.

    Used both for the mandatory first-login flow (where password_reset_required
    is True) and any voluntary password change.
    """
    verified, _new_hash = _password_helper.verify_and_update(
        body.current_password, user.hashed_password
    )
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    # Block re-using the same password
    if _password_helper.verify_and_update(body.new_password, user.hashed_password)[0]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from current password.",
        )

    user.hashed_password = _password_helper.hash(body.new_password)
    user.password_reset_required = False
    await session.flush()
    await session.commit()

    return PasswordChangeOut(ok=True, password_reset_required=False)
