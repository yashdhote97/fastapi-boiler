from typing import Optional, List
from pydantic import BaseModel, Field

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[str] = []
    organisation_id: str # New field

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class RoleInDBBase(RoleBase):
    id: str = Field(..., alias="_id")

    class Config:
        populate_by_name = True
        from_attributes = True

class Role(RoleInDBBase):
    pass
