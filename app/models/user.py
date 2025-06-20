from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    organisation_id: str
    role_ids: List[str] = []

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    organisation_id: Optional[str] = None
    role_ids: Optional[List[str]] = None

class UserInDBBase(UserBase):
    id: str = Field(..., alias="_id") # MongoDB uses _id

    class Config:
        populate_by_name = True # Allow using alias _id
        from_attributes = True # Allow ORM mode (though Motor is not an ORM)

class User(UserInDBBase):
    pass

class UserInDB(UserInDBBase):
    hashed_password: str
