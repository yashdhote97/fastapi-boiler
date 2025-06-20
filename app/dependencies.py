from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from pydantic import ValidationError

from app.config import settings
from app.db import crud_user
from app.models.user import User
from app.schemas.token import TokenData
from app.security import verify_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login") # Relative to server root

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_payload = verify_access_token(token, credentials_exception)
        email: Optional[str] = token_payload.get("username")
        org_id: Optional[str] = token_payload.get("org_id")

        if email is None or org_id is None:
            raise credentials_exception

    except JWTError: # verify_access_token should raise credentials_exception directly
        raise credentials_exception
    # Pydantic validation error can also occur if TokenData model is used here, but verify_access_token returns dict
    # except ValidationError:
    #     raise credentials_exception

    user = await crud_user.get_user_by_email(org_id=org_id, email=email)
    if user is None:
        raise credentials_exception

    # Optional: Sanity check that the user retrieved belongs to the org_id from the token
    # This should be guaranteed by crud_user.get_user_by_email if it queries by org_id correctly
    if user.organisation_id != org_id:
        # This would indicate a critical issue or data inconsistency
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User organisation mismatch.",
        )

    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

from typing import Set # For require_permission
from app.db import crud_role # For require_permission

def require_permission(required_permission: str):
    async def _permission_checker(current_user: User = Depends(get_current_active_user)):
        if not current_user.role_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no roles assigned.",
            )

        # Fetch all roles for the user from their organisation's DB
        user_roles = await crud_role.get_roles_by_ids(
            org_id=current_user.organisation_id,
            role_ids=current_user.role_ids
        )

        if not user_roles:
            # This case implies role_ids on user are stale or invalid,
            # which ideally shouldn't happen if role assignment is robust.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not retrieve valid roles for user.",
            )

        # Aggregate all permissions from the user's roles
        all_permissions: Set[str] = set()
        for role in user_roles:
            all_permissions.update(role.permissions)

        if required_permission not in all_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have the required permission: {required_permission}",
            )
        return current_user # Return user for potential use in endpoint, or can be True/None
    return _permission_checker

# New dependency to verify user's access to a specific organisation via path {org_id}
from app.db import crud_organisation # Ensure this is imported
from fastapi import Path # Ensure this is imported

async def verify_user_org_access(
    org_id: str = Path(..., title="The ID of the organisation to access"),
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Verifies that the current user belongs to the organisation specified in the path
    and that the organisation exists. Returns the current_user if valid.
    """
    if current_user.organisation_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organisation.",
        )

    organisation = await crud_organisation.get_organisation_by_id(org_id)
    if not organisation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, # Or 403 if we want to hide existence
            detail=f"Organisation with id '{org_id}' not found or not accessible.",
        )
    return current_user
