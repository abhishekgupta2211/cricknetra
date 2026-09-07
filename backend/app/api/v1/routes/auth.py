"""Auth & profile endpoints — /api/v1/auth/*."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import (
    get_account_service,
    get_activity_repo,
    get_auth_service,
    get_current_active_user,
    get_ownership_repo,
    get_photo_service,
    get_profile_service,
    get_role_service,
    get_social_service,
    get_user_repo,
    member_records,
)
from app.repositories.user_repository import UserRepository
from app.core.permissions import capabilities_for
from app.repositories.member_activity_repository import MemberActivityRepository
from app.repositories.ownership_repository import OwnershipRepository
from app.repositories.user_repository import UserRecord
from app.core.config import settings
from app.core.ratelimit import rate_limit
from app.schemas.auth import (
    EmailUpdate,
    ForgotPasswordRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserLogin,
    UserSignup,
    VerifyConfirmRequest,
)
from app.schemas.profile import ProfileCompleteRequest, ProfileResponse
from app.schemas.user import UserResponse
from app.services.account_service import AccountError, AccountService
from app.services.auth_service import AuthError, AuthService
from app.services.photo_service import PhotoError, PhotoService
from app.services.profile_service import ProfileError, ProfileService
from app.services.role_service import RoleService
from app.services.social_service import SocialService

router = APIRouter(prefix="/auth", tags=["auth"])

# Per-IP rate limits on the abuse-prone endpoints (no-op when disabled / in tests).
_login_rl = rate_limit(10, 60, "login")
_register_rl = rate_limit(5, 60, "register")
_forgot_rl = rate_limit(5, 60, "forgot")


def _user_out(rec: UserRecord) -> UserResponse:
    out = UserResponse.model_validate(rec)
    out.capabilities = capabilities_for(rec.role)
    return out


@router.post("/register", response_model=UserResponse, status_code=201, dependencies=[Depends(_register_rl)])
def register(
    payload: UserSignup,
    svc: AuthService = Depends(get_auth_service),
    roles: RoleService = Depends(get_role_service),
):
    try:
        user = svc.register(payload)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    out = _user_out(user)
    out.role_pending, out.requested_role = roles.status_for(user.id)
    return out


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(_login_rl)])
def login(payload: UserLogin, svc: AuthService = Depends(get_auth_service)):
    try:
        return svc.login(payload)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, svc: AuthService = Depends(get_auth_service)):
    try:
        return svc.refresh(payload.refresh_token)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/logout", status_code=204)
def logout(payload: RefreshRequest, svc: AuthService = Depends(get_auth_service)):
    svc.logout(payload.refresh_token)  # revokes the refresh token; always 204


@router.post("/logout-all", status_code=204)
def logout_all(
    user: UserRecord = Depends(get_current_active_user),
    svc: AuthService = Depends(get_auth_service),
    social: SocialService = Depends(get_social_service),
):
    """Sign out on every device: revoke all refresh tokens + forget push devices."""
    svc.logout_all(user.id)
    social.remove_all_push_subscriptions(user.id)


@router.get("/me", response_model=UserResponse)
def me(
    user: UserRecord = Depends(get_current_active_user),
    owners: OwnershipRepository = Depends(get_ownership_repo),
    activity: MemberActivityRepository = Depends(get_activity_repo),
    photos: PhotoService = Depends(get_photo_service),
    roles: RoleService = Depends(get_role_service),
):
    out = _user_out(user)
    out.records = member_records(user.id, owners, activity)
    out.has_photo = photos.has("user", user.id)
    out.role_pending, out.requested_role = roles.status_for(user.id)
    return out


@router.patch("/email", response_model=UserResponse)
def update_email(
    payload: EmailUpdate,
    user: UserRecord = Depends(get_current_active_user),
    users: UserRepository = Depends(get_user_repo),
    roles: RoleService = Depends(get_role_service),
):
    """Add or change the signed-in user's email (where OTP / reset codes go)."""
    updated = users.set_email(user.id, payload.email) or user
    out = _user_out(updated)
    out.role_pending, out.requested_role = roles.status_for(user.id)
    return out


@router.post("/profile", response_model=ProfileResponse, status_code=201)
def complete_profile(
    payload: ProfileCompleteRequest,
    user: UserRecord = Depends(get_current_active_user),
    svc: ProfileService = Depends(get_profile_service),
):
    try:
        return ProfileResponse.model_validate(svc.complete(user, payload))
    except ProfileError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    user: UserRecord = Depends(get_current_active_user),
    svc: ProfileService = Depends(get_profile_service),
):
    try:
        return ProfileResponse.model_validate(svc.get(user))
    except ProfileError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.patch("/profile", response_model=ProfileResponse)
def update_profile(
    payload: ProfileCompleteRequest,
    user: UserRecord = Depends(get_current_active_user),
    svc: ProfileService = Depends(get_profile_service),
):
    try:
        return ProfileResponse.model_validate(svc.update(user, payload))
    except ProfileError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/profile/photo", status_code=204)
async def upload_my_photo(
    file: UploadFile = File(...),
    user: UserRecord = Depends(get_current_active_user),
    photos: PhotoService = Depends(get_photo_service),
):
    data = await file.read()
    try:
        photos.save("user", user.id, file.content_type, data)
    except PhotoError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/profile/photo", status_code=204)
def delete_my_photo(
    user: UserRecord = Depends(get_current_active_user),
    photos: PhotoService = Depends(get_photo_service),
):
    photos.delete("user", user.id)


# ----- mobile verification --------------------------------------------------
@router.post("/verify/request")
def request_verification(
    user: UserRecord = Depends(get_current_active_user),
    svc: AccountService = Depends(get_account_service),
):
    """Send a verification code to the signed-in user's mobile."""
    code = svc.request_verification(user)
    if code is None:
        return {"sent": False, "already_verified": True}
    out: dict = {"sent": True}
    if settings.auth_dev_delivery:  # no SMS provider yet → return it so it's testable
        out["dev_code"] = code
    return out


@router.post("/verify/confirm")
def confirm_verification(
    payload: VerifyConfirmRequest,
    user: UserRecord = Depends(get_current_active_user),
    svc: AccountService = Depends(get_account_service),
):
    try:
        svc.confirm_verification(user, payload.code)
    except AccountError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return {"verified": True}


# ----- password reset (no auth — you've forgotten your password) -------------
@router.post("/password/forgot", dependencies=[Depends(_forgot_rl)])
def forgot_password(
    payload: ForgotPasswordRequest,
    svc: AccountService = Depends(get_account_service),
):
    token = svc.request_reset(payload.identifier)
    out: dict = {"sent": True}  # always generic — never reveal if the account exists
    if settings.auth_dev_delivery and token:
        out["dev_token"] = token
    return out


@router.post("/password/reset")
def reset_password(
    payload: ResetPasswordRequest,
    svc: AccountService = Depends(get_account_service),
):
    try:
        svc.reset_password(payload.token, payload.new_password)
    except AccountError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return {"ok": True}
