"""Schemas Pydantic simplifies"""
# app/schemas.py
from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    user: dict

class ImportResponse(BaseModel):
    success: bool
    import_id: int
    batch_id: str
    entity_type: str
    files_uploaded: Optional[int] = 0