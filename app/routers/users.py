from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pydantic import BaseModel

from app.db import crud_user, crud_organisation
from app.models.user import User, UserCreate, UserUpdate
from app.schemas.token import Token
from app.security import create_access_token, verify_password
from datetime import timedelta

from app.config import settings
from app.dependencies import get_current_active_user, require_permission # Added require_permission

router = APIRouter(
    prefix="/users", # Keeping prefix as /users
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

# Custom form model for login to include org_id (remains unchanged)
class LoginForm(BaseModel):
    username: str
    password: str
    org_id: str

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_new_user(
    user_in: UserCreate,
    current_admin_user: User = Depends(require_permission("manage_users_in_org"))
):
    if not user_in.organisation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target Organisation ID must be provided in the payload.",
        )
    # Admin must create user in their own organisation
    if current_admin_user.organisation_id != user_in.organisation_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrators can only create users in their own organisation."
        )

    org = await crud_organisation.get_organisation_by_id(org_id=user_in.organisation_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target organisation with id '{user_in.organisation_id}' not found.",
        )

    existing_user = await crud_user.get_user_by_email(org_id=user_in.organisation_id, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{user_in.email}' already exists in organisation '{user_in.organisation_id}'.",
        )

    try:
        # crud_user.create_user now takes only user_in (which includes organisation_id)
        user = await crud_user.create_user(user_in=user_in)
        return user
    except ValueError as e: # Catch role validation errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: LoginForm):
    org = await crud_organisation.get_organisation_by_id(org_id=form_data.org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid organisation, email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await crud_user.get_user_by_email(org_id=form_data.org_id, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid organisation, email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "org_id": form_data.org_id},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.get("/{user_id}", response_model=User)
async def read_user_in_organisation(
    user_id: str,
    current_viewer: User = Depends(require_permission("view_users_in_org"))
):
    # require_permission ensures current_viewer is active and has permission.
    # User is fetched by globally unique user_id.
    user = await crud_user.get_user_by_id(user_id=user_id)
    # Then, check if the fetched user belongs to the current_viewer's organisation.
    if not user or user.organisation_id != current_viewer.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or not in your organisation")
    return user

@router.put("/{user_id}", response_model=User)
async def update_existing_user(
    user_id: str,
    user_in: UserUpdate,
    current_admin_user: User = Depends(require_permission("manage_users_in_org"))
):
    # Check if the user to be updated (target_user) exists and belongs to the admin's organisation.
    target_user = await crud_user.get_user_by_id(user_id=user_id)
    if not target_user or target_user.organisation_id != current_admin_user.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User to update not found in your organisation")

    # Prevent changing organisation_id via this route, even if present in UserUpdate model
    # This check is more of a safeguard; crud_user.update_user also prevents this.
    if user_in.organisation_id is not None and user_in.organisation_id != current_admin_user.organisation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change a user's organisation_id via this endpoint."
        )
    # Ensure user_in does not try to set organisation_id for an existing user if it's part of UserUpdate
    user_in_data = user_in.model_dump(exclude_unset=True)
    if 'organisation_id' in user_in_data:
        del user_in_data['organisation_id']

    # Re-create UserUpdate from filtered data if necessary to ensure organisation_id is not passed to CRUD if it was filtered
    # Or rely on CRUD to ignore it if not applicable for update.
    # Current crud_user.update_user already handles/ignores organisation_id in update_data.

    try:
        # Pass current_admin_user.organisation_id as current_org_id for role validation context
        updated_user = await crud_user.update_user(
            user_id=user_id,
            user_in=user_in, # Pass the original user_in, crud_user handles organisation_id
            current_org_id=current_admin_user.organisation_id
        )
        if updated_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or update failed")
        return updated_user
    except ValueError as e: # Catch role validation errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
