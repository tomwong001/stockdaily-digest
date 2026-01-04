from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import List, Dict, Set
import asyncio

from database import get_db
from models import User, UserCompany, DailyDigest
from schemas import DigestResponse, GenerateDigestRequest
from auth import get_current_user
from services.news_collector import news_collector
from services.ai_summarizer import ai_summarizer
from services.email_sender import email_sender
from config import settings

router = APIRouter(prefix="/api/digests", tags=["日报"])


async def generate_digest_for_user(user: User, db: Session) -> dict:
    """为用户生成日报内容（过去的一天的新闻）"""
    
    # 获取用户关注的公司
    user_companies = db.query(UserCompany).filter(
        UserCompany.user_id == user.id
    ).all()
    
    if not user_companies:
        return {
            "company_news": {},
            "industry_news": [],
            "generated_at": datetime.utcnow().isoformat()
        }
    
    # 提取公司信息
    tickers = [uc.company.ticker for uc in user_companies]
    names = [uc.company.name for uc in user_companies]
    
    # 目标日期（前一天，按天）
    target_date, tz_name = news_collector._get_target_date(None)  # noqa: SLF001

    # 收集公司新闻（前一天）
    company_news_raw = await news_collector.collect_company_news(tickers, names, max_results_per_company=30)
    
    # 为每个公司生成摘要
    company_news: Dict[str, List[dict]] = {}

    # 并行生成摘要（限流）
    max_concurrency = max(1, int(getattr(settings, "MAX_CONCURRENT_AI_REQUESTS", 3)))
    sem = asyncio.Semaphore(max_concurrency)

    # 便于查公司名
    ticker_to_name = {uc.company.ticker: uc.company.name for uc in user_companies}

    async def _summarize_one(ticker: str, news_items: list[dict]) -> tuple[str, dict]:
        """为单个公司生成摘要。即使没有新闻也返回结果（不丢弃公司）。"""
        company_name = ticker_to_name.get(ticker, ticker)
        
        # 即使没有新闻，也不丢弃公司，而是返回"今日无重大新闻"
        if not news_items:
            return ticker, {
                "title": f"{company_name} 新闻摘要",
                "summary": f"**{target_date}** 未搜索到关于 **{company_name} ({ticker})** 的重大新闻。这可能意味着：\n\n1. 该公司当日没有重要的公开新闻发布\n2. 新闻尚未被索引或搜索服务暂时不可用\n\n建议关注公司官网或财经新闻网站获取最新信息。",
                "source": "AI 摘要",
                "items": [],
            }
        
        async with sem:
            try:
                summary = await ai_summarizer.generate_company_news_summary_with_references(
                    ticker=ticker,
                    company_name=company_name,
                    news_items=news_items,
                    target_date=target_date,
                    max_items=30,
                )
                return ticker, {
                    "title": f"{company_name} 新闻摘要",
                    "summary": summary,
                    "source": "AI 摘要",
                    "items": news_items[: min(len(news_items), 30)],
                }
            except Exception as e:
                # 单个失败不影响其他公司
                return ticker, {
                    "title": f"{company_name} 新闻摘要",
                    "summary": f"{target_date} 关于 {company_name} 的摘要生成失败：{str(e)}",
                    "source": "AI 摘要",
                    "items": news_items[: min(len(news_items), 30)],
                }

    # 确保所有用户关注的公司都有任务（即使 company_news_raw 中没有该公司的数据）
    all_tickers_set = set(tickers)
    for t in all_tickers_set:
        if t not in company_news_raw:
            company_news_raw[t] = []  # 确保每个公司都有条目
    
    tasks = [_summarize_one(t, items) for t, items in company_news_raw.items()]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    for r in results:
        if r is None:
            continue
        ticker, obj = r
        company_news[ticker] = [obj]
    
    return {
        "company_news": company_news,
        "industry_news": [],  # 行业新闻已融合进公司摘要（按需求取消独立板块）
        "generated_at": datetime.utcnow().isoformat()
    }


@router.post("/generate", response_model=DigestResponse)
async def generate_digest(
    request: GenerateDigestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """手动生成日报（用于测试）"""
    today = date.today()
    
    # 检查今日是否已有日报
    existing_digest = db.query(DailyDigest).filter(
        DailyDigest.user_id == current_user.id,
        DailyDigest.date == today
    ).first()
    
    # 生成日报内容
    content = await generate_digest_for_user(current_user, db)
    
    if existing_digest:
        # 更新现有日报
        existing_digest.content = content
        db.commit()
        db.refresh(existing_digest)
        digest = existing_digest
    else:
        # 创建新日报
        digest = DailyDigest(
            user_id=current_user.id,
            date=today,
            content=content
        )
        db.add(digest)
        db.commit()
        db.refresh(digest)
    
    # 如果需要发送邮件
    if request.send_email:
        date_str = today.strftime("%Y/%m/%d")
        sent = await email_sender.send_digest_email(
            to_email=current_user.email,
            digest_content=content,
            date_str=date_str
        )
        if sent:
            digest.sent_at = datetime.utcnow()
            db.commit()
            db.refresh(digest)
    
    return DigestResponse(
        id=digest.id,
        date=digest.date,
        content=digest.content,
        sent_at=digest.sent_at,
        created_at=digest.created_at
    )


@router.get("/today", response_model=DigestResponse)
def get_today_digest(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取今日日报"""
    today = date.today()
    
    digest = db.query(DailyDigest).filter(
        DailyDigest.user_id == current_user.id,
        DailyDigest.date == today
    ).first()
    
    if not digest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="今日日报尚未生成"
        )
    
    return DigestResponse(
        id=digest.id,
        date=digest.date,
        content=digest.content,
        sent_at=digest.sent_at,
        created_at=digest.created_at
    )


@router.get("", response_model=List[DigestResponse])
def get_digest_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 30
):
    """获取历史日报列表"""
    digests = db.query(DailyDigest).filter(
        DailyDigest.user_id == current_user.id
    ).order_by(DailyDigest.date.desc()).limit(limit).all()
    
    return [
        DigestResponse(
            id=d.id,
            date=d.date,
            content=d.content,
            sent_at=d.sent_at,
            created_at=d.created_at
        )
        for d in digests
    ]
