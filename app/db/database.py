from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

# Reinstated global client and database object
client = AsyncIOMotorClient(settings.MONGODB_URL)
database: AsyncIOMotorDatabase = client[settings.DATABASE_NAME]

# Optional: if a getter function is preferred by any existing code, though direct import is also fine.
def get_database() -> AsyncIOMotorDatabase:
    return database

# Removed:
# _mongo_client = None
# def get_mongo_client() -> AsyncIOMotorClient: ...
# def set_mongo_client(client_instance: AsyncIOMotorClient): ...
# def get_central_db() -> AsyncIOMotorDatabase: ...
# def get_organisation_db(org_id: str) -> AsyncIOMotorDatabase: ...
