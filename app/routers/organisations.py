from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.models.organisation import Organisation, OrganisationCreate, OrganisationUpdate
from app.models.user import User # For dependency type hinting
from app.db import crud_organisation
from app.dependencies import get_current_active_user, require_permission, verify_user_org_access # Added

router = APIRouter(
    prefix="/organisations",
    tags=["organisations"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=Organisation, status_code=status.HTTP_201_CREATED)
async def create_new_organisation(
    org_in: OrganisationCreate,
    current_user: User = Depends(get_current_active_user) # Any authenticated user can create an org for now
):
    # TODO: Potentially restrict org creation to superadmins or specific user types later.
    # TODO: After creating an org, the creator should perhaps be made an admin of it. (Covered in later step)
    existing_org = await crud_organisation.get_organisation_by_name(name=org_in.name)
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organisation with name '{org_in.name}' already exists.",
        )
    organisation = await crud_organisation.create_organisation(org_in=org_in)
    # The calling user is NOT automatically associated with this new org yet.
    # This needs to be handled in a subsequent step (e.g. assign creator as admin).
    return organisation

@router.get(
    "/",
    response_model=List[Organisation],
    dependencies=[Depends(require_permission("list_all_organisations"))] # Example: only superadmin type
)
async def list_all_organisations(skip: int = 0, limit: int = 100):
    # This is a sensitive endpoint, assuming only a superadmin should see ALL orgs.
    # Normal users should perhaps only see their own org via /users/me or a dedicated /organisations/myorg endpoint.
    organisations = await crud_organisation.get_all_organisations(skip=skip, limit=limit)
    return organisations

@router.get(
    "/{org_id}",
    response_model=Organisation,
    dependencies=[
        Depends(verify_user_org_access),
        Depends(require_permission("view_organisation_settings"))
    ]
)
async def get_organisation_details(org_id: str): # org_id from path, validated by verify_user_org_access
    # verify_user_org_access ensures user belongs to this org_id.
    # require_permission ensures user has 'view_organisation_settings' permission.
    organisation = await crud_organisation.get_organisation_by_id(org_id)
    # This should always be found if verify_user_org_access passed, as it checks org existence.
    if organisation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return organisation

@router.put(
    "/{org_id}",
    response_model=Organisation,
    dependencies=[
        Depends(verify_user_org_access),
        Depends(require_permission("edit_organisation_settings"))
    ]
)
async def update_existing_organisation(org_id: str, org_in: OrganisationUpdate):
    updated_organisation = await crud_organisation.update_organisation(org_id=org_id, org_in=org_in)
    if updated_organisation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found or no changes made")
    return updated_organisation

@router.delete(
    "/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(verify_user_org_access),
        Depends(require_permission("delete_organisation")) # This is a very sensitive permission
    ]
)
async def delete_existing_organisation(org_id: str):
    # TODO: Consider implications: what happens to users, data in org-specific DBs?
    # This should be a "soft delete" or have significant warnings/checks.
    deleted = await crud_organisation.delete_organisation(org_id=org_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found or could not be deleted")
    return
