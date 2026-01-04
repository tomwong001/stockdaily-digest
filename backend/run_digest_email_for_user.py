"""
一键全流程测试脚本：
- 从数据库读取指定用户（按邮箱）
- 读取该用户关注公司列表
- 为每家公司抓取最多 30 条新闻
- 生成带引用的摘要
- 发送邮件（与线上逻辑一致）

用法：
  python backend/run_digest_email_for_user.py
  python backend/run_digest_email_for_user.py 2841969860w@gmail.com
"""

import asyncio
import sys
import logging
from datetime import datetime

from config import settings
from database import SessionLocal, Base, engine
from models import User, UserCompany
from routers.digests import generate_digest_for_user
from services.email_sender import email_sender

# 设置日志以显示新闻收集进度
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


async def main():
    # 默认用户邮箱（可通过命令行参数覆盖）
    target_email = sys.argv[1].strip() if len(sys.argv) > 1 else "2841969860w@gmail.com"

    print("=" * 70)
    print("Full E2E Test: user companies -> digest (<=30/news) -> email")
    print("=" * 70)

    print("\n检查配置...")
    print(f"  SMTP_HOST: {settings.SMTP_HOST}")
    print(f"  SMTP_PORT: {settings.SMTP_PORT}")
    print(f"  SMTP_USER: {settings.SMTP_USER if settings.SMTP_USER else '(未设置)'}")
    print(f"  SMTP_PASSWORD: {'已设置' if settings.SMTP_PASSWORD else '(未设置)'}")
    print(f"  FROM_EMAIL: {settings.FROM_EMAIL}")
    print(f"  AI_BUILDER_TOKEN: {'已设置' if settings.AI_BUILDER_TOKEN else '(未设置)'}")
    print(f"  MAX_CONCURRENT_AI_REQUESTS: {getattr(settings, 'MAX_CONCURRENT_AI_REQUESTS', None)}")

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print("\n错误: SMTP 未配置！请检查 backend/.env")
        return
    if not settings.AI_BUILDER_TOKEN:
        print("\n错误: AI_BUILDER_TOKEN 未配置！请检查 backend/.env")
        return

    # 确保表已创建
    Base.metadata.create_all(bind=engine)

    print(f"\n目标用户邮箱: {target_email}")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == target_email).first()
        if not user:
            print(f"\n错误: 数据库中未找到用户 {target_email}（请先注册）")
            return

        user_companies = db.query(UserCompany).filter(UserCompany.user_id == user.id).all()
        if not user_companies:
            print(f"\n错误: 用户 {target_email} 尚未关注任何公司（请先添加关注）")
            return

        expected_count = len(user_companies)
        print(f"\n用户关注公司列表（共 {expected_count} 个）：")
        for uc in user_companies:
            print(f"  - {uc.company.ticker} ({uc.company.name})")

        print("\n生成日报（与线上一致：每家公司最多 30 条新闻）...")
        print("(正在收集新闻，可能需要几分钟...)\n")
        
        digest_content = await generate_digest_for_user(user, db)

        # 详细统计
        company_news = digest_content.get("company_news", {})
        actual_count = len(company_news)
        
        print("\n" + "=" * 70)
        print("新闻收集结果统计：")
        print("=" * 70)
        
        companies_with_news = 0
        companies_without_news = []
        
        for ticker, news_list in company_news.items():
            if news_list and len(news_list) > 0:
                items = news_list[0].get("items", [])
                item_count = len(items)
                if item_count > 0:
                    companies_with_news += 1
                    print(f"  ✅ {ticker}: {item_count} 条新闻")
                else:
                    companies_without_news.append(ticker)
                    print(f"  ⚠️  {ticker}: 0 条新闻（将显示'今日无重大新闻'）")
            else:
                companies_without_news.append(ticker)
                print(f"  ⚠️  {ticker}: 无数据")
        
        # 检查是否有缺失的公司
        expected_tickers = {uc.company.ticker for uc in user_companies}
        actual_tickers = set(company_news.keys())
        missing_tickers = expected_tickers - actual_tickers
        
        if missing_tickers:
            print(f"\n  ❌ 缺失公司: {', '.join(missing_tickers)}")
        
        print(f"\n  总计: {actual_count}/{expected_count} 个公司")
        print(f"  有新闻: {companies_with_news} 个")
        print(f"  无新闻: {len(companies_without_news)} 个")

        print(f"\n发送邮件到 {target_email} ...")
        date_str = datetime.now().strftime("%Y/%m/%d")
        ok = await email_sender.send_digest_email(
            to_email=target_email,
            digest_content=digest_content,
            date_str=date_str,
        )

        if ok:
            print("\n✅ 邮件发送成功！请检查收件箱/垃圾箱。")
            print(f"   - 公司数: {actual_count}/{expected_count}")
            if actual_count < expected_count:
                print(f"   ⚠️  注意: 预期 {expected_count} 个公司，实际 {actual_count} 个")
        else:
            print("\n❌ 邮件发送失败（请检查 SMTP 配置/日志）。")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())


