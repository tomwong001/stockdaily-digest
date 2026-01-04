"""
测试邮件发送和新闻总结功能的脚本
"""
import asyncio
import sys
import os
from datetime import datetime
from services.email_sender import email_sender
from services.ai_summarizer import ai_summarizer
from services.news_collector import news_collector
from config import settings

# 设置 Windows 控制台编码为 UTF-8
if sys.platform == 'win32':
    try:
        os.system('chcp 65001 >nul')
    except:
        pass


async def test_email_with_real_news():
    """使用真实新闻数据测试邮件发送功能"""
    print("=" * 60)
    print("📧 使用真实新闻数据测试邮件发送")
    print("=" * 60)
    
    # 目标邮箱
    target_email = "2841969860w@gmail.com"
    
    # 检查配置
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print("\n❌ 错误: SMTP 未配置！请检查 .env 文件")
        return False
    
    if not settings.AI_BUILDER_TOKEN:
        print("\n❌ 错误: AI_BUILDER_TOKEN 未配置！请检查 .env 文件")
        return False
    
    print(f"\n📬 目标邮箱: {target_email}")
    print(f"📅 收集过去24小时的真实新闻...")
    
    # 使用一些热门股票代码收集真实新闻
    test_companies = ["AAPL", "TSLA", "MSFT", "GOOGL", "NVDA"]
    test_names = ["Apple Inc", "Tesla Inc", "Microsoft Corporation", "Alphabet Inc", "NVIDIA Corporation"]
    
    print(f"\n正在搜索以下公司的新闻:")
    for ticker, name in zip(test_companies, test_names):
        print(f"  - {ticker} ({name})")
    
    try:
        # 1. 收集公司新闻
        print("\n📰 步骤 1/3: 收集公司新闻...")
        company_news_raw = await news_collector.collect_company_news(test_companies, test_names)
        
        # 2. 生成摘要
        print("🤖 步骤 2/3: 使用AI生成新闻摘要...")
        company_news = {}
        for ticker, news_items in company_news_raw.items():
            if news_items:
                # 找到公司名称
                company_name = test_names[test_companies.index(ticker)] if ticker in test_companies else ticker
                
                # 生成摘要
                summary = await ai_summarizer.summarize_news(news_items, company_name)
                
                # 格式化新闻数据（使用新的格式：摘要 + 新闻来源）
                company_news[ticker] = [{
                    "title": f"{company_name} 新闻摘要",
                    "summary": summary,
                    "url": news_items[0].get("url", "#") if news_items else "#",
                    "source": "AI 摘要",
                    "items": news_items[:3]  # 保留原始新闻
                }]
                print(f"  ✅ {ticker}: 找到 {len(news_items)} 条新闻，已生成摘要")
        
        # 3. 使用AI判断细分行业
        print("\n📊 步骤 3/4: 使用AI判断细分行业...")
        company_sub_industries = {}
        test_industries = ["Technology", "Automotive", "Technology", "Technology", "Technology"]  # 对应各公司
        
        for ticker, name, main_industry in zip(test_companies, test_names, test_industries):
            sub_industries = await ai_summarizer.classify_sub_industries(ticker, name, main_industry)
            company_sub_industries[ticker] = sub_industries
            print(f"  ✅ {ticker} ({name}): {', '.join(sub_industries)}")
        
        # 4. 收集与公司相关的行业新闻（过去的一天，包括竞争对手、市场分析等）
        print(f"\n📊 步骤 4/4: 收集与公司相关的行业新闻（过去的一天）...")
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
        
        # 构建日报内容
        digest_content = {
            "company_news": company_news,
            "industry_news": industry_news,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # 4. 发送邮件
        print(f"\n📧 正在发送邮件到 {target_email}...")
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
            print(f"   - 行业新闻: {len(industry_news)} 个行业")
            return True
        else:
            print("\n❌ 邮件发送失败")
            return False
            
    except Exception as e:
        print(f"\n❌ 处理过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_email_sending():
    """测试邮件发送功能（使用模拟数据）"""
    print("=" * 60)
    print("📧 测试邮件发送功能（模拟数据）")
    print("=" * 60)
    
    # 创建测试日报内容
    test_digest = {
        "company_news": {
            "AAPL": [
                {
                    "title": "苹果公司发布新款iPhone",
                    "summary": "苹果公司今日发布了最新款iPhone，配备更强大的A17芯片和升级的摄像头系统。",
                    "url": "https://example.com/apple-news",
                    "source": "Tech News"
                },
                {
                    "title": "苹果股价上涨3%",
                    "summary": "受新产品发布影响，苹果股价在盘后交易中上涨超过3%。",
                    "url": "https://example.com/apple-stock",
                    "source": "Financial Times"
                }
            ],
            "TSLA": [
                {
                    "title": "特斯拉交付量创新高",
                    "summary": "特斯拉第三季度全球交付量达到43.5万辆，同比增长27%，创历史新高。",
                    "url": "https://example.com/tesla-delivery",
                    "source": "Reuters"
                }
            ]
        },
        "industry_news": [
            {
                "title": "科技股整体上涨",
                "summary": "受AI技术推动，科技股板块今日整体上涨2.5%，多家公司股价创新高。",
                "url": "https://example.com/tech-stocks",
                "industry": "Technology"
            }
        ],
        "generated_at": datetime.utcnow().isoformat()
    }
    
    # 测试邮箱（请修改为你的邮箱）
    test_email = input("请输入测试邮箱地址（直接回车使用 business@steplify.ai）: ").strip()
    if not test_email:
        test_email = "business@steplify.ai"
    
    print(f"\n准备发送测试邮件到: {test_email}")
    print(f"SMTP配置:")
    print(f"  Host: {settings.SMTP_HOST}")
    print(f"  Port: {settings.SMTP_PORT}")
    print(f"  User: {settings.SMTP_USER}")
    print(f"  From: {settings.FROM_EMAIL}")
    
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print("\n❌ 错误: SMTP 未配置！请检查 .env 文件")
        return False
    
    date_str = datetime.now().strftime("%Y/%m/%d")
    
    print(f"\n正在发送邮件...")
    try:
        success = await email_sender.send_digest_email(
            to_email=test_email,
            digest_content=test_digest,
            date_str=date_str
        )
        
        if success:
            print("✅ 邮件发送成功！请检查收件箱（包括垃圾邮件文件夹）")
            return True
        else:
            print("❌ 邮件发送失败")
            return False
            
    except Exception as e:
        print(f"❌ 发送邮件时出错: {str(e)}")
        return False


async def test_news_collection():
    """测试新闻收集功能"""
    print("\n" + "=" * 60)
    print("📰 测试新闻收集功能")
    print("=" * 60)
    
    if not settings.AI_BUILDER_TOKEN:
        print("❌ 错误: AI_BUILDER_TOKEN 未配置！请检查 .env 文件")
        return None
    
    # 测试搜索一些公司新闻
    test_companies = ["AAPL", "TSLA"]
    test_names = ["Apple Inc", "Tesla Inc"]
    
    print(f"\n正在搜索以下公司的新闻:")
    for ticker, name in zip(test_companies, test_names):
        print(f"  - {ticker} ({name})")
    
    try:
        print("\n正在收集新闻...")
        company_news = await news_collector.collect_company_news(test_companies, test_names)
        
        print("\n📊 收集结果:")
        for ticker, news_list in company_news.items():
            print(f"\n{ticker}:")
            if news_list:
                print(f"  找到 {len(news_list)} 条新闻")
                for i, news in enumerate(news_list[:3], 1):
                    print(f"  {i}. {news.get('title', '无标题')[:60]}...")
                    print(f"     来源: {news.get('source', '未知')}")
            else:
                print("  未找到新闻")
        
        return company_news
        
    except Exception as e:
        print(f"❌ 收集新闻时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def test_news_summarization(news_data=None):
    """测试新闻总结功能"""
    print("\n" + "=" * 60)
    print("🤖 测试AI新闻总结功能")
    print("=" * 60)
    
    if not settings.AI_BUILDER_TOKEN:
        print("❌ 错误: AI_BUILDER_TOKEN 未配置！请检查 .env 文件")
        return None
    
    # 如果没有提供新闻数据，使用测试数据
    if not news_data:
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
    else:
        # 使用收集到的新闻
        test_news = []
        for ticker, news_list in news_data.items():
            if news_list:
                test_news.extend(news_list[:2])
                break
    
    if not test_news:
        print("❌ 没有可用的新闻数据进行总结")
        return None
    
    print(f"\n正在为以下新闻生成摘要:")
    for i, news in enumerate(test_news[:3], 1):
        print(f"  {i}. {news.get('title', '无标题')[:60]}...")
    
    try:
        print("\n正在生成摘要...")
        summary = await ai_summarizer.summarize_news(test_news, "Apple Inc")
        
        print("\n📝 AI生成的摘要:")
        print("-" * 60)
        print(summary)
        print("-" * 60)
        
        return summary
        
    except Exception as e:
        print(f"❌ 生成摘要时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def test_full_workflow():
    """测试完整工作流程：收集新闻 -> 生成摘要 -> 发送邮件"""
    print("\n" + "=" * 60)
    print("🔄 测试完整工作流程")
    print("=" * 60)
    
    # 1. 收集新闻
    news_data = await test_news_collection()
    if not news_data:
        print("\n⚠️  跳过后续步骤（新闻收集失败）")
        return
    
    # 2. 生成摘要
    summary = await test_news_summarization(news_data)
    if not summary:
        print("\n⚠️  跳过邮件发送（摘要生成失败）")
        return
    
    # 3. 询问是否发送测试邮件
    send_email = input("\n是否发送包含摘要的测试邮件？(y/n): ").strip().lower()
    if send_email == 'y':
        await test_email_sending()


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🧪 StockDaily Digest 功能测试工具")
    print("=" * 60)
    
    print("\n请选择测试项目:")
    print("1. 🚀 使用真实新闻发送邮件到 2841969860w@gmail.com（推荐）")
    print("2. 测试邮件发送（使用模拟数据）")
    print("3. 测试新闻收集")
    print("4. 测试AI新闻总结（使用模拟数据）")
    print("5. 测试完整工作流程（收集 -> 总结 -> 发送）")
    print("6. 全部测试")
    
    choice = input("\n请输入选项 (1-6): ").strip()
    
    if choice == "1":
        await test_email_with_real_news()
    elif choice == "2":
        await test_email_sending()
    elif choice == "3":
        await test_news_collection()
    elif choice == "4":
        await test_news_summarization()
    elif choice == "5":
        await test_full_workflow()
    elif choice == "6":
        await test_email_with_real_news()
        await test_email_sending()
        news_data = await test_news_collection()
        await test_news_summarization(news_data)
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

