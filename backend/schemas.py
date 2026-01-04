from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime, date


# ============ Auth Schemas ============

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    
    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


# ============ Company Schemas ============

class CompanyBase(BaseModel):
    ticker: str
    name: str
    industry: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyResponse(CompanyBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class CompanySearchResult(BaseModel):
    ticker: str
    name: str
    industry: Optional[str] = None


class UserCompanyResponse(BaseModel):
    id: str
    ticker: str
    name: str
    industry: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ News Schemas ============

class NewsArticleResponse(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    source_url: str
    source_name: Optional[str] = None
    published_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============ Digest Schemas ============

class DigestContent(BaseModel):
    company_news: dict[str, List[dict]]  # ticker -> list of news
    industry_news: List[dict]
    generated_at: datetime


class DigestResponse(BaseModel):
    id: str
    date: date
    content: Optional[Any] = None
    sent_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class GenerateDigestRequest(BaseModel):
    send_email: bool = False
