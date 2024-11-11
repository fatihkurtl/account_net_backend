from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime

class BusinessCreate(BaseModel):
    name: str
    sector: str
    yearly_income: float
    workers_count: int
    email: EmailStr
    phone: str
    address: str

class BusinessResponse(BusinessCreate):
    id: int
    table_name: str
    owner_id: int
    created_at: datetime

class TransactionCreate(BaseModel):
    customer_name: str
    product_name: str
    quantity: int
    unit_price: float
    total_amount: float
    payment_method: str
    notes: Optional[str] = None

class TransactionResponse(TransactionCreate):
    id: int
    transaction_date: datetime
    created_at: datetime