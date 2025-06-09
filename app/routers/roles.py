from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import List

from app.models.role import Role, RoleCreate, RoleUpdate
from app.models.user import User
from app.db import crud_role
# crud_organisation is not directly used here anymore as verify_user_org_access handles org checks
from app.dependencies import require_permission, verify_user_org_access # Updated imports

router = APIRouter(
    prefix="/organisations/{org_id}/roles",
    tags=["roles"],
    responses={404: {"description": "Not found"}},
)

# verify_user_org_access now returns the current_user if valid.
# We can capture it if needed, or let it just perform validation.
# Path parameters like org_id are directly available to endpoint functions if named in signature.

@router.post(
    "/",
    response_model=Role,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(verify_user_org_access),
        Depends(require_permission("manage_roles_in_org")) # Renamed permission
    ]
)
async def create_new_role(
    org_id: str, # from path, validated by verify_user_org_access
    role_in: RoleCreate
):
    # verify_user_org_access ensures user belongs to org_id and org exists.
    # require_permission("manage_roles_in_org") ensures the user has the permission.

    # Add check: role_in.organisation_id must match org_id from path
    if role_in.organisation_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role's organisation_id in body must match organisation_id in path"
        )

    try:
        # crud_role.create_role now only takes role_in (which includes organisation_id)
        role = await crud_role.create_role(role_in=role_in)
        return role
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get(
    "/",
    response_model=List[Role],
    dependencies=[
        Depends(verify_user_org_access),
        Depends(require_permission("view_roles_in_org"))
    ]
)
async def list_all_roles(org_id: str, skip: int = 0, limit: int = 100):
    roles = await crud_role.get_all_roles(org_id=org_id, skip=skip, limit=limit)
    return roles

@router.get(
    "/{role_id}",
    response_model=Role,
    dependencies=[
        Depends(verify_user_org_access),
        Depends(require_permission("view_roles_in_org"))
    ]
)
async def get_role_details(org_id: str, role_id: str):
    # crud_role.get_role_by_id now only takes role_id
    role = await crud_role.get_role_by_id(role_id=role_id)
    # Add check: if role exists and its organisation_id matches path org_id
    if not role or role.organisation_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found in this organisation")
    return role

@router.put(
    "/{role_id}",
    response_model=Role,
    dependencies=[
        Depends(verify_user_org_access),
        Depends(require_permission("manage_roles_in_org"))
    ]
)
async def update_existing_role(org_id: str, role_id: str, role_in: RoleUpdate):
    # First, verify the role exists and belongs to the specified organisation
    existing_role = await crud_role.get_role_by_id(role_id=role_id)
    if not existing_role or existing_role.organisation_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found in this organisation")

    try:
        # crud_role.update_role now only takes role_id and role_in
        updated_role = await crud_role.update_role(role_id=role_id, role_in=role_in)
        if updated_role is None: # Should not happen if previous check passed, but good for safety
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found or update failed")
        return updated_role
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(verify_user_org_access),
        Depends(require_permission("manage_roles_in_org"))
    ]
)
async def delete_existing_role(org_id: str, role_id: str):
    # First, verify the role exists and belongs to the specified organisation
    existing_role = await crud_role.get_role_by_id(role_id=role_id)
    if not existing_role or existing_role.organisation_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found in this organisation")

    # TODO: Check if role is assigned before deletion (application-level concern)
    # crud_role.delete_role now only takes role_id
    deleted = await crud_role.delete_role(role_id=role_id)
    if not deleted: # Should not happen if previous check passed, but good for safety
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role could not be deleted")
    return
