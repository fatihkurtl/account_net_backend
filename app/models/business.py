from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime
from pydantic import EmailStr

class UserBase(SQLModel):
    username: str = Field(unique=True, index=True)
    email: EmailStr = Field(unique=True, index=True)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class BusinessInfo(SQLModel, table=True):
    """İşletmelerin genel bilgilerini tutan tablo"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    table_name: str = Field(unique=True)
    sector: str
    yearly_income: float
    workers_count: int
    email: EmailStr
    phone: str
    address: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    owner_id: int = Field(foreign_key="user.id")