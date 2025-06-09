from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class OrganisationSettings(BaseModel):
    custom_fields: Optional[Dict[str, Any]] = None
    theme: Optional[str] = None

class OrganisationBase(BaseModel):
    name: str
    description: Optional[str] = None

class OrganisationCreate(OrganisationBase):
    pass

class OrganisationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[OrganisationSettings] = None

class OrganisationInDBBase(OrganisationBase):
    id: str = Field(..., alias="_id")
    settings: OrganisationSettings = Field(default_factory=OrganisationSettings)

    class Config:
        populate_by_name = True
        from_attributes = True

class Organisation(OrganisationInDBBase):
    pass
