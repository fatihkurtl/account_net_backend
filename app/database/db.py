from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy import MetaData, Table, Column, Integer, String, Float, DateTime, Text
from datetime import datetime
import string
import random

DATABASE_URL = "sqlite:///./business_db.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

def generate_table_name(business_name: str, user_id: int) -> str:
    """İşletme için benzersiz tablo adı oluşturur"""
    base_name = "".join(c.lower() for c in business_name if c.isalnum())
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"business_{user_id}_{base_name}_{random_str}"

def create_business_table(table_name: str):
    """Dinamik olarak yeni işletme tablosu oluşturur"""
    metadata = MetaData()
    
    new_table = Table(
        table_name, 
        metadata,
        Column('id', Integer, primary_key=True),
        Column('transaction_date', DateTime, default=datetime.utcnow),
        Column('customer_name', String),
        Column('product_name', String),
        Column('quantity', Integer),
        Column('unit_price', Float),
        Column('total_amount', Float),
        Column('payment_method', String),
        Column('notes', Text, nullable=True),
        Column('created_at', DateTime, default=datetime.utcnow),
    )
    
    metadata.create_all(engine)
    return new_table

def get_business_table(table_name: str):
    """Var olan işletme tablosunu getirir"""
    metadata = MetaData()
    return Table(table_name, metadata, autoload_with=engine)