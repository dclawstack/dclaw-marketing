"""FastAPI-Users router mounts — login / logout / refresh / reset."""

from fastapi import APIRouter

from app.auth import auth_backend, fastapi_users
from app.auth.schemas import UserRead, UserUpdate


router = APIRouter()

# /jwt/login, /jwt/logout — Bearer JWT login/logout
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
    tags=["auth"],
)

# /reset-password/forgot, /reset-password/reset — server-side reset by email
# token. Used when user has FORGOTTEN their password.
router.include_router(
    fastapi_users.get_reset_password_router(),
    tags=["auth"],
)

# /verify, /verify/request — email verification flow. Not in MVP but
# wired for completeness; emails won't fire until Resend creds are set.
router.include_router(
    fastapi_users.get_verify_router(UserRead),
    tags=["auth"],
)
