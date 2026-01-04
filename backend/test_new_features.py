"""
测试新功能：AI行业分类、改进的摘要格式、细分行业新闻
"""
import asyncio
import sys
import os
from datetime import datetime

# 设置 Windows 控制台编码为 UTF-8
if sys.platform == 'win32':
    try:
        os.system('chcp 65001 >nul')
    except:
        pass

from services.email_sender import email_sender
from services.ai_summarizer import ai_summarizer
from services.news_collector import news_collector
from config import settings


async def test_ai_industry_classification():
    """测试AI行业分类功能"""
    print("=" * 60)
    print("🤖 测试AI行业分类功能")
    print("=" * 60)
    
    if not settings.AI_BUILDER_TOKEN:
        print("❌ 错误: AI_BUILDER_TOKEN 未配置！请检查 .env 文件")
        return
    
    test_cases = [
        ("AAPL", "Apple Inc.", "Technology"),
        ("TSLA", "Tesla Inc.", "Automotive"),
        ("MSFT", "Microsoft Corporation", "Technology"),
        ("NVDA", "NVIDIA Corporation", "Technology"),
        ("JPM", "JPMorgan Chase & Co.", "Financial Services"),
    ]
    
    print("\n正在测试以下公司的行业分类：\n")
    for ticker, name, main_industry in test_cases:
        print(f"  {ticker} ({name}) - 大类行业: {main_industry}")
        try:
            sub_industries = await ai_summarizer.classify_sub_industries(
                ticker=ticker,
                company_name=name,
                main_industry=main_industry
            )
            print(f"    → 细分行业: {', '.join(sub_industries)}")
        except Exception as e:
            print(f"    ❌ 错误: {str(e)}")
        print()
    
    print("✅ AI行业分类测试完成\n")


async def test_full_workflow_with_new_features():
    """测试完整工作流程（包含新功能）"""
    print("=" * 60)
    print("🚀 测试完整工作流程（包含新功能）")
    print("=" * 60)
    
    target_email = input("\n请输入测试邮箱地址（直接回车使用 2841969860w@gmail.com）: ").strip()
    if not target_email:
        target_email = "2841969860w@gmail.com"
    
    # 检查配置
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print("\n❌ 错误: SMTP 未配置！请检查 .env 文件")
        return False
    
    if not settings.AI_BUILDER_TOKEN:
        print("\n❌ 错误: AI_BUILDER_TOKEN 未配置！请检查 .env 文件")
        return False
    
    print(f"\n📬 目标邮箱: {target_email}")
    
    # 测试公司
    test_companies = ["AAPL", "TSLA", "MSFT"]
    test_names = ["Apple Inc", "Tesla Inc", "Microsoft Corporation"]
    test_industries = ["Technology", "Automotive", "Technology"]
    
    print(f"\n正在测试以下公司:")
    for ticker, name in zip(test_companies, test_names):
        print(f"  - {ticker} ({name})")
    
    try:
        # 1. 收集公司新闻
        print("\n📰 步骤 1/5: 收集公司新闻...")
        company_news_raw = await news_collector.collect_company_news(test_companies, test_names)
        
        # 2. 生成公司新闻摘要
        print("🤖 步骤 2/5: 使用AI生成公司新闻摘要...")
        company_news = {}
        for ticker, news_items in company_news_raw.items():
            if news_items:
                company_name = test_names[test_companies.index(ticker)] if ticker in test_companies else ticker
                summary = await ai_summarizer.summarize_news(news_items, company_name)
                
                company_news[ticker] = [{
                    "title": f"{company_name} 新闻摘要",
                    "summary": summary,
                    "url": news_items[0].get("url", "#") if news_items else "#",
                    "source": "AI 摘要",
                    "items": news_items[:3]
                }]
                print(f"  ✅ {ticker}: 找到 {len(news_items)} 条新闻，已生成摘要")
        
        # 3. 使用AI判断细分行业
        print("\n🎯 步骤 3/5: 使用AI判断细分行业...")
        sub_industries_set = set()
        company_sub_industries = {}
        for ticker, name, main_industry in zip(test_companies, test_names, test_industries):
            sub_industries = await ai_summarizer.classify_sub_industries(ticker, name, main_industry)
            company_sub_industries[ticker] = sub_industries
            sub_industries_set.update(sub_industries)
            print(f"  ✅ {ticker} ({name}): {', '.join(sub_industries)}")
        
        print(f"\n  汇总细分行业: {', '.join(sub_industries_set)}")
        
        # 4. 收集与公司相关的行业新闻（过去的一天）
        print("\n📊 步骤 4/5: 收集与公司相关的行业新闻（过去的一天）...")
        
        # company_sub_industries 已在步骤3中构建
        
        industry_news_raw = await news_collector.collect_company_industry_news(
            tickers=test_companies,
            company_names=test_names,
            sub_industries=company_sub_industries
        )
        
        industry_news = []
        for industry, data in industry_news_raw.items():
            news_items = data.get("news_items", [])
            related_companies = data.get("related_companies", [])
            if news_items:
                summary = await ai_summarizer.generate_industry_summary(industry, news_items, related_companies)
                industry_news.append({
                    "industry": industry,
                    "title": f"{industry} 行业动态",
                    "summary": summary,
                    "url": news_items[0].get("url", "#") if news_items else "#",
                    "related_companies": related_companies
                })
                print(f"  ✅ {industry}: 找到 {len(news_items)} 条新闻，相关公司: {', '.join(related_companies)}")
        
        # 5. 构建并发送邮件
        digest_content = {
            "company_news": company_news,
            "industry_news": industry_news,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        print(f"\n📧 步骤 5/5: 发送邮件到 {target_email}...")
        date_str = datetime.now().strftime("%Y/%m/%d")
        
        success = await email_sender.send_digest_email(
            to_email=target_email,
            digest_content=digest_content,
            date_str=date_str
        )
        
        if success:
            print("\n✅ 邮件发送成功！")
            print(f"   请检查 {target_email} 的收件箱（包括垃圾邮件文件夹）")
            print(f"\n📊 邮件内容摘要:")
            print(f"   - 公司新闻: {len(company_news)} 家公司")
            print(f"   - 细分行业新闻: {len(industry_news)} 个行业")
            for industry_item in industry_news:
                print(f"     • {industry_item['industry']}")
            return True
        else:
            print("\n❌ 邮件发送失败")
            return False
            
    except Exception as e:
        print(f"\n❌ 处理过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_summary_format():
    """测试摘要格式（确保没有'...'）"""
    print("=" * 60)
    print("📝 测试摘要格式")
    print("=" * 60)
    
    if not settings.AI_BUILDER_TOKEN:
        print("❌ 错误: AI_BUILDER_TOKEN 未配置！")
        return
    
    test_news = [
        {
            "title": "Apple announces new iPhone with advanced AI features",
            "content": "Apple Inc. unveiled its latest iPhone model featuring groundbreaking AI capabilities. The new device includes enhanced camera systems powered by machine learning and improved battery life. Analysts predict strong sales for the holiday season.",
            "url": "https://example.com/apple-ai",
            "source": "Tech News"
        },
        {
            "title": "Apple stock rises on strong earnings report",
            "content": "Apple shares jumped 5% in after-hours trading following better-than-expected quarterly earnings. Revenue reached $89.5 billion, driven by strong iPhone and services sales.",
            "url": "https://example.com/apple-earnings",
            "source": "Financial Times"
        }
    ]
    
    print("\n正在生成摘要...")
    try:
        summary = await ai_summarizer.summarize_news(test_news, "Apple Inc")
        
        print("\n📝 AI生成的摘要:")
        print("-" * 60)
        print(summary)
        print("-" * 60)
        
        # 检查是否包含"..."（不应该有）
        if "..." in summary:
            print("\n⚠️  警告: 摘要中包含'...'，可能需要检查")
        else:
            print("\n✅ 摘要格式正确（没有多余的'...'）")
        
        return summary
        
    except Exception as e:
        print(f"❌ 生成摘要时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🧪 StockDaily Digest 新功能测试工具")
    print("=" * 60)
    
    print("\n请选择测试项目:")
    print("1. 🤖 测试AI行业分类功能")
    print("2. 📝 测试摘要格式（确保没有'...'）")
    print("3. 🚀 测试完整工作流程（包含所有新功能）")
    print("4. 🔄 全部测试")
    
    choice = input("\n请输入选项 (1-4): ").strip()
    
    if choice == "1":
        await test_ai_industry_classification()
    elif choice == "2":
        await test_summary_format()
    elif choice == "3":
        await test_full_workflow_with_new_features()
    elif choice == "4":
        await test_ai_industry_classification()
        await test_summary_format()
        await test_full_workflow_with_new_features()
    else:
        print("无效选项")
        return
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试已取消")
        sys.exit(0)

