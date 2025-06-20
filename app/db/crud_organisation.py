from typing import List, Optional
from bson import ObjectId

from app.db.database import database # Changed import: using the global database object
from app.models.organisation import OrganisationCreate, OrganisationUpdate, OrganisationInDBBase, OrganisationSettings

# Define collection at module level using the imported database object
ORGANISATIONS_COLLECTION = database["organisations"]

async def create_organisation(org_in: OrganisationCreate) -> OrganisationInDBBase:
    org_db_data = org_in.model_dump()

    if 'settings' not in org_db_data or org_db_data['settings'] is None:
         org_db_data['settings'] = OrganisationSettings().model_dump()

    result = await ORGANISATIONS_COLLECTION.insert_one(org_db_data)
    created_doc = await ORGANISATIONS_COLLECTION.find_one({"_id": result.inserted_id})
    if created_doc:
        return OrganisationInDBBase(**created_doc, _id=str(created_doc["_id"]))
    raise Exception("Failed to create or retrieve organisation after insert.")

async def get_organisation_by_id(org_id: str) -> Optional[OrganisationInDBBase]:
    if not ObjectId.is_valid(org_id):
        return None
    org_doc = await ORGANISATIONS_COLLECTION.find_one({"_id": ObjectId(org_id)})
    if org_doc:
        return OrganisationInDBBase(**org_doc, _id=str(org_doc["_id"]))
    return None

async def get_organisation_by_name(name: str) -> Optional[OrganisationInDBBase]:
    org_doc = await ORGANISATIONS_COLLECTION.find_one({"name": name})
    if org_doc:
        return OrganisationInDBBase(**org_doc, _id=str(org_doc["_id"]))
    return None

async def get_all_organisations(skip: int = 0, limit: int = 100) -> List[OrganisationInDBBase]:
    organisations_cursor = ORGANISATIONS_COLLECTION.find().skip(skip).limit(limit)
    organisations = []
    async for org_doc in organisations_cursor:
        organisations.append(OrganisationInDBBase(**org_doc, _id=str(org_doc["_id"])))
    return organisations

async def update_organisation(org_id: str, org_in: OrganisationUpdate) -> Optional[OrganisationInDBBase]:
    if not ObjectId.is_valid(org_id):
        return None

    existing_org_doc = await ORGANISATIONS_COLLECTION.find_one({"_id": ObjectId(org_id)})
    if not existing_org_doc:
        return None

    update_data = org_in.model_dump(exclude_unset=True)

    if "settings" in update_data and update_data["settings"] is not None:
        update_data["settings"] = OrganisationSettings(**update_data["settings"]).model_dump()
    elif "settings" in update_data and update_data["settings"] is None:
         update_data["settings"] = OrganisationSettings().model_dump()

    if not update_data:
        return OrganisationInDBBase(**existing_org_doc, _id=str(existing_org_doc["_id"]))

    result = await ORGANISATIONS_COLLECTION.update_one(
        {"_id": ObjectId(org_id)},
        {"$set": update_data}
    )

    if result.matched_count > 0 :
        updated_org_doc = await ORGANISATIONS_COLLECTION.find_one({"_id": ObjectId(org_id)})
        if updated_org_doc:
            return OrganisationInDBBase(**updated_org_doc, _id=str(updated_org_doc["_id"]))
    return None

async def delete_organisation(org_id: str) -> bool:
    if not ObjectId.is_valid(org_id):
        return False
    result = await ORGANISATIONS_COLLECTION.delete_one({"_id": ObjectId(org_id)})
    return result.deleted_count == 1
