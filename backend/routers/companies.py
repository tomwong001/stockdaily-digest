from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import User, Company, UserCompany
from schemas import CompanyCreate, CompanySearchResult, UserCompanyResponse
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["公司管理"])

# 常用美股公司数据（用于搜索）
STOCK_DATA = {
    "AAPL": {"name": "Apple Inc.", "industry": "Technology"},
    "MSFT": {"name": "Microsoft Corporation", "industry": "Technology"},
    "GOOGL": {"name": "Alphabet Inc.", "industry": "Technology"},
    "GOOG": {"name": "Alphabet Inc. (Class C)", "industry": "Technology"},
    "AMZN": {"name": "Amazon.com Inc.", "industry": "Consumer Cyclical"},
    "NVDA": {"name": "NVIDIA Corporation", "industry": "Technology"},
    "META": {"name": "Meta Platforms Inc.", "industry": "Technology"},
    "TSLA": {"name": "Tesla Inc.", "industry": "Automotive"},
    "BRK.B": {"name": "Berkshire Hathaway Inc.", "industry": "Financial Services"},
    "JPM": {"name": "JPMorgan Chase & Co.", "industry": "Financial Services"},
    "V": {"name": "Visa Inc.", "industry": "Financial Services"},
    "JNJ": {"name": "Johnson & Johnson", "industry": "Healthcare"},
    "WMT": {"name": "Walmart Inc.", "industry": "Consumer Defensive"},
    "PG": {"name": "Procter & Gamble Co.", "industry": "Consumer Defensive"},
    "MA": {"name": "Mastercard Inc.", "industry": "Financial Services"},
    "UNH": {"name": "UnitedHealth Group Inc.", "industry": "Healthcare"},
    "HD": {"name": "Home Depot Inc.", "industry": "Consumer Cyclical"},
    "DIS": {"name": "Walt Disney Co.", "industry": "Communication Services"},
    "BAC": {"name": "Bank of America Corp.", "industry": "Financial Services"},
    "ADBE": {"name": "Adobe Inc.", "industry": "Technology"},
    "CRM": {"name": "Salesforce Inc.", "industry": "Technology"},
    "NFLX": {"name": "Netflix Inc.", "industry": "Communication Services"},
    "AMD": {"name": "Advanced Micro Devices Inc.", "industry": "Technology"},
    "INTC": {"name": "Intel Corporation", "industry": "Technology"},
    "PYPL": {"name": "PayPal Holdings Inc.", "industry": "Financial Services"},
    "COST": {"name": "Costco Wholesale Corp.", "industry": "Consumer Defensive"},
    "PEP": {"name": "PepsiCo Inc.", "industry": "Consumer Defensive"},
    "KO": {"name": "Coca-Cola Co.", "industry": "Consumer Defensive"},
    "NKE": {"name": "Nike Inc.", "industry": "Consumer Cyclical"},
    "SBUX": {"name": "Starbucks Corp.", "industry": "Consumer Cyclical"},
    "BABA": {"name": "Alibaba Group Holding Ltd.", "industry": "Consumer Cyclical"},
    "TSM": {"name": "Taiwan Semiconductor Manufacturing", "industry": "Technology"},
    "ORCL": {"name": "Oracle Corporation", "industry": "Technology"},
    "CSCO": {"name": "Cisco Systems Inc.", "industry": "Technology"},
    "IBM": {"name": "International Business Machines", "industry": "Technology"},
    "UBER": {"name": "Uber Technologies Inc.", "industry": "Technology"},
    "SNAP": {"name": "Snap Inc.", "industry": "Communication Services"},
    "SPOT": {"name": "Spotify Technology S.A.", "industry": "Communication Services"},
    "SQ": {"name": "Block Inc.", "industry": "Technology"},
    "COIN": {"name": "Coinbase Global Inc.", "industry": "Financial Services"},
    "PLTR": {"name": "Palantir Technologies Inc.", "industry": "Technology"},
    "ROKU": {"name": "Roku Inc.", "industry": "Communication Services"},
    "ZM": {"name": "Zoom Video Communications", "industry": "Technology"},
    "ABNB": {"name": "Airbnb Inc.", "industry": "Consumer Cyclical"},
    "DOCU": {"name": "DocuSign Inc.", "industry": "Technology"},
    "SNOW": {"name": "Snowflake Inc.", "industry": "Technology"},
    "NET": {"name": "Cloudflare Inc.", "industry": "Technology"},
    "DDOG": {"name": "Datadog Inc.", "industry": "Technology"},
    "MDB": {"name": "MongoDB Inc.", "industry": "Technology"},
    "CRWD": {"name": "CrowdStrike Holdings Inc.", "industry": "Technology"},
}


@router.get("/companies/search", response_model=List[CompanySearchResult])
def search_companies(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    current_user: User = Depends(get_current_user)
):
    """搜索公司（通过股票代码或公司名称）"""
    query = q.upper().strip()
    results = []
    
    for ticker, info in STOCK_DATA.items():
        # 匹配股票代码或公司名称
        if query in ticker or query.lower() in info["name"].lower():
            results.append(CompanySearchResult(
                ticker=ticker,
                name=info["name"],
                industry=info.get("industry")
            ))
    
    # 最多返回 10 个结果
    return results[:10]


@router.get("/user/companies", response_model=List[UserCompanyResponse])
def get_user_companies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户关注的公司列表"""
    user_companies = db.query(UserCompany).filter(
        UserCompany.user_id == current_user.id
    ).all()
    
    result = []
    for uc in user_companies:
        company = uc.company
        result.append(UserCompanyResponse(
            id=company.id,
            ticker=company.ticker,
            name=company.name,
            industry=company.industry,
            created_at=uc.created_at
        ))
    
    return result


@router.post("/user/companies", response_model=UserCompanyResponse)
def add_company(
    company_data: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添加关注公司"""
    ticker = company_data.ticker.upper()
    
    # 查找或创建公司
    company = db.query(Company).filter(Company.ticker == ticker).first()
    if not company:
        company = Company(
            ticker=ticker,
            name=company_data.name,
            industry=company_data.industry
        )
        db.add(company)
        db.commit()
        db.refresh(company)
    
    # 检查是否已关注
    existing = db.query(UserCompany).filter(
        UserCompany.user_id == current_user.id,
        UserCompany.company_id == company.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已关注该公司"
        )
    
    # 创建关注关系
    user_company = UserCompany(
        user_id=current_user.id,
        company_id=company.id
    )
    db.add(user_company)
    db.commit()
    db.refresh(user_company)
    
    return UserCompanyResponse(
        id=company.id,
        ticker=company.ticker,
        name=company.name,
        industry=company.industry,
        created_at=user_company.created_at
    )


@router.delete("/user/companies/{company_id}")
def remove_company(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消关注公司"""
    user_company = db.query(UserCompany).filter(
        UserCompany.user_id == current_user.id,
        UserCompany.company_id == company_id
    ).first()
    
    if not user_company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到该关注记录"
        )
    
    db.delete(user_company)
    db.commit()
    
    return {"message": "已取消关注"}
