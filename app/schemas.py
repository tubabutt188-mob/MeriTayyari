"""
Pydantic schemas — request/response validation.
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class NoteCreate(BaseModel):
    title: str
    content: str
    grade: Optional[str] = None
    subject: Optional[str] = None
    diagram_svg: Optional[str] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    grade: Optional[str] = None
    subject: Optional[str] = None
    diagram_svg: Optional[str] = None


class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    grade: Optional[str] = None
    subject: Optional[str] = None
    diagram_svg: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True