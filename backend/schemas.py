from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_admin: bool

    class Config:
        from_attributes = True

class CertificateBase(BaseModel):
    student_name: str
    course_name: str
    data_payload: Dict[str, Any]

class CertificateCreate(CertificateBase):
    pass

class Certificate(CertificateBase):
    id: str
    student_id: Optional[int]
    signature: str
    issued_at: datetime
    revoked: bool

    class Config:
        from_attributes = True

class VerificationRequest(BaseModel):
    certificate_id: str
    # In a real scenario, you might upload the full JSON.
    # Here we simulate verifying by ID or by providing the payload + signature manually
    data_payload: Optional[Dict[str, Any]] = None
    signature: Optional[str] = None
