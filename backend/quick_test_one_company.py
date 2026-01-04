"""
快速测试（控制台输出）：只跑 1 家公司（默认 AAPL），不发邮件。

输出：
- 公司新闻：前一天（按天）的新闻标题（最多 30 条） + AI 摘要（带引用 [1]）
"""

import asyncio
import sys
import os

from services.news_collector import news_collector
from services.ai_summarizer import ai_summarizer
from config import settings


# 设置 Windows 控制台编码为 UTF-8
if sys.platform == "win32":
    try:
        os.system("chcp 65001 >nul")
    except Exception:
        pass


async def main():
    # 你也可以在这里改成别的 ticker/name
    ticker = "AAPL"
    company_name = "Apple Inc"
    main_industry = "Technology"

    if not settings.AI_BUILDER_TOKEN:
        print("ERROR: AI_BUILDER_TOKEN 未配置！请检查 backend/.env")
        return

    # 目标日期（前一天，只精确到天）
    target_date, tz_name = news_collector._get_target_date(None)  # noqa: SLF001
    print("=" * 70)
    print(f"Quick Test (console) | {ticker} ({company_name})")
    print(f"目标日期: {target_date} ({tz_name})")
    print("=" * 70)

    # 1) 公司新闻（减少 max_results = 3，加速）
    print("\n## 公司新闻（只要具体新进展，排除泛泛股价/估值文）")
    company_query = (
        f"{company_name} ({ticker}) breaking news leak rumor product roadmap "
        f"Apple Intelligence Siri China mainland beta rollout iPhone Fold chip roadmap "
        f"supply chain regulatory approval competitor partnership acquisition"
    )
    company_items = await news_collector.search_news_via_agent(
        search_query=company_query,
        target_date=target_date,
        tz_name=tz_name,
        max_results=30,
    )

    if not company_items:
        print("(未找到新闻，或搜索结果不满足日期过滤)")
    else:
        for i, it in enumerate(company_items, 1):
            print(f"{i}. {it.get('title', '')}")
            print(f"   - source: {it.get('source', '')}")
            print(f"   - published_date: {it.get('published_date', '')}")
            print(f"   - url: {it.get('url', '')}")

        summary = await ai_summarizer.generate_company_news_summary_with_references(
            ticker=ticker,
            company_name=company_name,
            news_items=company_items,
            target_date=target_date,
            max_items=30,
        )
        print("\n### 公司新闻摘要")
        print(summary)

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())


