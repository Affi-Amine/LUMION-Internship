from pydantic import BaseModel, EmailStr
from typing import Optional

class CustomerCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    role: Optional[str] = None
    company_id: Optional[str] = None

class CustomerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    company_id: Optional[str] = None