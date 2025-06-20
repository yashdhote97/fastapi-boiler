from typing import List, Optional
from bson import ObjectId

from app.db.database import database # Use global database object
from app.models.role import RoleCreate, RoleUpdate, RoleInDBBase # These models will need organisation_id

roles_collection = database["roles"] # Define collection at module level

async def create_role(role_in: RoleCreate) -> RoleInDBBase: # org_id parameter removed
    # Assumes role_in contains organisation_id
    if not getattr(role_in, 'organisation_id', None):
        raise ValueError("organisation_id must be provided in RoleCreate model.")

    # Check if role with the same name already exists in this organisation
    existing_role = await roles_collection.find_one({
        "name": role_in.name,
        "organisation_id": role_in.organisation_id
    })
    if existing_role:
        raise ValueError(f"Role with name '{role_in.name}' already exists in organisation '{role_in.organisation_id}'.")

    role_db_data = role_in.model_dump()
    # Ensure organisation_id from role_in is part of role_db_data if model structure requires it explicitly
    # For now, model_dump() should include it if it's a field in RoleCreate.

    result = await roles_collection.insert_one(role_db_data)
    created_doc = await roles_collection.find_one({"_id": result.inserted_id})
    if not created_doc:
        raise Exception("Failed to create or retrieve role after insert.")
    return RoleInDBBase(**created_doc)


async def get_role_by_id(role_id: str) -> Optional[RoleInDBBase]: # org_id parameter removed
    if not ObjectId.is_valid(role_id):
        return None
    role_doc = await roles_collection.find_one({"_id": ObjectId(role_id)})
    if role_doc:
        return RoleInDBBase(**role_doc)
    return None

async def get_role_by_name(name: str, org_id: str) -> Optional[RoleInDBBase]: # Parameter order changed
    if not org_id: # Still need org_id to ensure name uniqueness within an org
        raise ValueError("Organisation ID must be provided to fetch role by name.")
    role_doc = await roles_collection.find_one({"name": name, "organisation_id": org_id})
    if role_doc:
        return RoleInDBBase(**role_doc)
    return None

async def get_all_roles(org_id: str, skip: int = 0, limit: int = 100) -> List[RoleInDBBase]:
    if not org_id:
        # Depending on desired behavior, could return empty list or raise error.
        # Raising error might be better if org_id is always expected.
        raise ValueError("Organisation ID must be provided to fetch all roles.")

    roles_cursor = roles_collection.find({"organisation_id": org_id}).skip(skip).limit(limit)
    roles = []
    async for role_doc in roles_cursor:
        roles.append(RoleInDBBase(**role_doc))
    return roles

async def update_role(role_id: str, role_in: RoleUpdate) -> Optional[RoleInDBBase]: # org_id parameter removed
    if not ObjectId.is_valid(role_id):
        return None

    update_data = role_in.model_dump(exclude_unset=True)

    # Prevent organisation_id from being changed via this update method
    if "organisation_id" in update_data:
        # Log a warning, or simply remove, or raise error.
        # For now, remove to prevent accidental changes.
        del update_data["organisation_id"]

    # If name is being updated, check for uniqueness again within its current organisation
    if "name" in update_data and update_data["name"] is not None:
        # Need the role's current organisation_id to check for name uniqueness
        current_role_doc = await roles_collection.find_one({"_id": ObjectId(role_id)})
        if not current_role_doc:
            return None # Role does not exist
        current_org_id = current_role_doc.get("organisation_id")
        if not current_org_id:
            # This implies data integrity issue; roles should always have an org_id
            raise Exception(f"Role {role_id} is missing organisation_id.")

        existing_role_with_name = await roles_collection.find_one({
            "name": update_data["name"],
            "organisation_id": current_org_id,
            "_id": {"$ne": ObjectId(role_id)} # Exclude the current role itself
        })
        if existing_role_with_name:
            raise ValueError(f"Another role with name '{update_data['name']}' already exists in organisation '{current_org_id}'.")

    if not update_data:
        return await get_role_by_id(role_id=role_id)

    result = await roles_collection.update_one(
        {"_id": ObjectId(role_id)},
        {"$set": update_data}
    )
    if result.matched_count > 0:
        return await get_role_by_id(role_id=role_id)
    return None

async def delete_role(role_id: str) -> bool: # org_id parameter removed
    if not ObjectId.is_valid(role_id):
        return False
    result = await roles_collection.delete_one({"_id": ObjectId(role_id)})
    return result.deleted_count == 1

async def get_roles_by_ids(role_ids: List[str], org_id: str) -> List[RoleInDBBase]: # Parameter order changed
    if not org_id: # org_id is crucial to ensure roles belong to the correct organisation
        raise ValueError("Organisation ID must be provided to fetch roles by IDs.")
    if not role_ids:
        return []

    object_ids = [ObjectId(r_id) for r_id in role_ids if ObjectId.is_valid(r_id)]
    if not object_ids: # If no valid ObjectIds were formed (e.g., list of empty strings)
        return []

    # Query includes organisation_id to ensure roles are fetched from the specified org
    roles_cursor = roles_collection.find({
        "_id": {"$in": object_ids},
        "organisation_id": org_id
    })
    roles = []
    async for role_doc in roles_cursor:
        roles.append(RoleInDBBase(**role_doc))
    return roles
