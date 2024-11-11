from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from sqlalchemy import insert, select as sa_select, MetaData, Table
from datetime import timedelta, datetime
from typing import List

from database.db import (
    get_session, 
    create_db_and_tables, 
    generate_table_name,
    create_business_table,
    get_business_table,
    engine
)
from models.business import User, BusinessInfo
from schemas.business import (
    UserCreate, 
    UserResponse, 
    BusinessCreate, 
    BusinessResponse,
    TransactionCreate,
    TransactionResponse,
    Token
)
from authenticate.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(title="Business Management API")

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Kullanıcı işlemleri
@app.post("/register", response_model=UserResponse, tags=["Authentication"])
def register_user(user: UserCreate, session: Session = Depends(get_session)):
    # Kullanıcı adı veya email kontrolü
    db_user = session.exec(
        select(User).where(
            (User.username == user.username) | (User.email == user.email)
        )
    ).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Bu kullanıcı adı veya email zaten kayıtlı"
        )

    # Yeni kullanıcı oluştur
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@app.post("/token", response_model=Token, tags=["Authentication"])
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    user = session.exec(
        select(User).where(User.username == form_data.username)
    ).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı adı veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# İşletme işlemleri
@app.post("/businesses/", response_model=BusinessResponse, tags=["Businesses"])
def create_business(
    business: BusinessCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Benzersiz tablo adı oluştur
    table_name = generate_table_name(business.name, current_user.id)
    
    # İşletme bilgilerini kaydet
    db_business = BusinessInfo(
        **business.dict(),
        table_name=table_name,
        owner_id=current_user.id
    )
    session.add(db_business)
    
    # İşletme için yeni tablo oluştur
    create_business_table(table_name)
    
    session.commit()
    session.refresh(db_business)
    return db_business

@app.get("/businesses/", response_model=List[BusinessResponse], tags=["Businesses"])
def get_user_businesses(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Kullanıcının kendi işletmelerini listeler"""
    statement = select(BusinessInfo).where(BusinessInfo.owner_id == current_user.id)
    businesses = session.exec(statement).all()
    return businesses

@app.get("/businesses/{business_id}", response_model=BusinessResponse, tags=["Businesses"])
def get_business_detail(
    business_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    business = session.get(BusinessInfo, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="İşletme bulunamadı")
    
    if business.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Bu işletmeye erişim yetkiniz yok"
        )
    
    return business

# İşlem kayıtları
@app.post("/businesses/{business_id}/transactions/", response_model=TransactionResponse, tags=["Transactions"])
def add_transaction(
    business_id: int,
    transaction: TransactionCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # İşletme kontrolü
    business = session.get(BusinessInfo, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="İşletme bulunamadı")
    if business.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bu işletmeye erişim yetkiniz yok")
    
    # İşletmenin tablosunu al
    business_table = get_business_table(business.table_name)
    
    # Yeni işlem kaydı ekle
    stmt = insert(business_table).values(
        **transaction.dict(),
        transaction_date=datetime.utcnow()
    )
    
    with engine.connect() as conn:
        result = conn.execute(stmt)
        conn.commit()
        
        # Eklenen kaydı getir
        new_transaction = conn.execute(
            sa_select(business_table).where(business_table.c.id == result.inserted_primary_key[0])
        ).first()
    
    return new_transaction

@app.get("/businesses/{business_id}/transactions/", response_model=List[TransactionResponse], tags=["Transactions"])
def get_business_transactions(
    business_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # İşletme kontrolü
    business = session.get(BusinessInfo, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="İşletme bulunamadı")
    if business.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bu işletmeye erişim yetkiniz yok")
    
    # İşletmenin tablosunu al
    business_table = get_business_table(business.table_name)
    
    # Tüm işlemleri getir
    with engine.connect() as conn:
        results = conn.execute(sa_select(business_table)).fetchall()
    
    return results

@app.delete("/businesses/{business_id}", tags=["Businesses"])
def delete_business(
    business_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # İşletme kontrolü
    business = session.get(BusinessInfo, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="İşletme bulunamadı")
    if business.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bu işletmeye erişim yetkiniz yok")
    
    # İşletme tablosunu sil
    metadata = MetaData()
    table = Table(business.table_name, metadata)
    table.drop(engine)
    
    # İşletme bilgilerini sil
    session.delete(business)
    session.commit()
    
    return {"message": "İşletme ve tüm verileri başarıyla silindi"}