from typing import Optional, List
from bson import ObjectId

from app.db.database import database # Use global database object
from app.db import crud_role
from app.models.user import UserCreate, UserInDB, UserUpdate
from app.security import get_password_hash

users_collection = database["users"] # Define collection at module level

async def create_user(user_in: UserCreate) -> UserInDB: # org_id parameter removed
    if not user_in.organisation_id: # Ensure organisation_id is part of UserCreate
        raise ValueError("Organisation ID must be provided in user data.")

    # Validate role_ids
    if user_in.role_ids:
        unique_role_ids = list(set(user_in.role_ids))
        # crud_role.get_roles_by_ids will also need to be updated to not require org_id in its signature
        # if roles are global, or take org_id if roles are still per-org but in same DB.
        # Assuming roles are still conceptually per-org, so org_id passed to get_roles_by_ids.
        found_roles = await crud_role.get_roles_by_ids(org_id=user_in.organisation_id, role_ids=unique_role_ids)
        if len(found_roles) != len(unique_role_ids):
            raise ValueError("One or more role_ids are invalid for the specified organisation.")

    hashed_password = get_password_hash(user_in.password)
    user_db_data = user_in.model_dump(exclude={"password"})
    user_db_data["hashed_password"] = hashed_password

    result = await users_collection.insert_one(user_db_data)
    # After insert, retrieve the full user doc including the generated _id
    created_user_doc = await users_collection.find_one({"_id": result.inserted_id})
    if not created_user_doc:
        raise Exception("Failed to create or retrieve user after insert.")
    return UserInDB(**created_user_doc)


async def get_user_by_email(email: str, org_id: str) -> Optional[UserInDB]: # Parameter order changed for preference
    if not org_id:
        raise ValueError("Organisation ID must be provided to fetch user by email.")
    # Query includes organisation_id to ensure uniqueness of email per organisation
    user_doc = await users_collection.find_one({"email": email, "organisation_id": org_id})
    if user_doc:
        return UserInDB(**user_doc)
    return None

async def get_user_by_id(user_id: str) -> Optional[UserInDB]: # org_id parameter removed
    if not ObjectId.is_valid(user_id):
        return None
    user_doc = await users_collection.find_one({"_id": ObjectId(user_id)})
    if user_doc:
        return UserInDB(**user_doc)
    return None

async def update_user(user_id: str, user_in: UserUpdate, current_org_id: str) -> Optional[UserInDB]:
    if not ObjectId.is_valid(user_id):
        return None

    update_data = user_in.model_dump(exclude_unset=True)

    # Prevent organisation_id from being changed via this update method
    if "organisation_id" in update_data:
        del update_data["organisation_id"]

    if "password" in update_data and update_data["password"] is not None:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    elif "password" in update_data: # password field exists but is None
        update_data.pop("password")

    # Validate role_ids if present in update_data, against the user's current organisation context
    if user_in.role_ids is not None:
        unique_role_ids = list(set(user_in.role_ids))
        if unique_role_ids: # Only query if there are actual IDs
            # Assuming roles are still conceptually per-org, validated against current_org_id
            found_roles = await crud_role.get_roles_by_ids(org_id=current_org_id, role_ids=unique_role_ids)
            if len(found_roles) != len(unique_role_ids):
                raise ValueError("One or more role_ids are invalid for the user's organisation when updating.")
        # If user_in.role_ids is an empty list [], it means "remove all roles".
        # update_data will correctly have "role_ids": [] from model_dump.
        # If unique_role_ids is empty (e.g. from an empty list input), no DB call needed.

    if not update_data: # If, after processing, there's nothing to update (e.g. only org_id was passed)
        # Fetch and return existing user to indicate no change, or handle as error/None
        return await get_user_by_id(user_id=user_id)


    result = await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    if result.matched_count > 0:
        return await get_user_by_id(user_id=user_id)
    return None


async def delete_user(user_id: str) -> bool: # org_id parameter removed
    if not ObjectId.is_valid(user_id):
        return False
    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    return result.deleted_count == 1
