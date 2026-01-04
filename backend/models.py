from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Date, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    companies = relationship("UserCompany", back_populates="user", cascade="all, delete-orphan")
    digests = relationship("DailyDigest", back_populates="user", cascade="all, delete-orphan")


class Company(Base):
    __tablename__ = "companies"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    users = relationship("UserCompany", back_populates="company")
    news_mappings = relationship("NewsCompanyMapping", back_populates="company")


class UserCompany(Base):
    __tablename__ = "user_companies"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 唯一约束
    __table_args__ = (UniqueConstraint('user_id', 'company_id', name='uix_user_company'),)
    
    # 关系
    user = relationship("User", back_populates="companies")
    company = relationship("Company", back_populates="users")


class NewsArticle(Base):
    __tablename__ = "news_articles"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    source_url = Column(String(1000), unique=True, nullable=False)
    source_name = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    company_mappings = relationship("NewsCompanyMapping", back_populates="news")


class NewsCompanyMapping(Base):
    __tablename__ = "news_company_mappings"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    news_id = Column(String(36), ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # 关系
    news = relationship("NewsArticle", back_populates="company_mappings")
    company = relationship("Company", back_populates="news_mappings")


class DailyDigest(Base):
    __tablename__ = "daily_digests"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    content = Column(JSON, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 唯一约束
    __table_args__ = (UniqueConstraint('user_id', 'date', name='uix_user_date'),)
    
    # 关系
    user = relationship("User", back_populates="digests")
