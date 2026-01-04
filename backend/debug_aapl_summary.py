"""
调试脚本：复现 AAPL 在指定日期的抓取结果 + 摘要输出，方便定位“为何输出没有显著事件”。

用法：
  python backend/debug_aapl_summary.py
"""

import asyncio

from services.news_collector import news_collector
from services.ai_summarizer import ai_summarizer


async def main():
    ticker = "AAPL"
    company_name = "Apple Inc."
    target_date = "2026-01-02"
    tz_name = "America/New_York"

    query = (
        f"{company_name} ({ticker}) breaking news leak rumor product roadmap "
        f"earnings guidance SEC filing investigation lawsuit antitrust regulatory "
        f"supply chain recall partnership acquisition competitor product launch "
        f"\"last day\""
    )

    print("=" * 70)
    print(f"DEBUG AAPL | target_date={target_date} tz={tz_name}")
    print("=" * 70)
    print("Query:", query)

    items = await news_collector.search_news_via_agent(
        search_query=query,
        target_date=target_date,
        tz_name=tz_name,
        max_results=10,
    )

    print("\nFetched items:", len(items))
    for i, it in enumerate(items, 1):
        print(f"{i}. [{it.get('published_date','')}] {it.get('title','')}")
        print("   - source:", it.get("source", ""))
        print("   - url:", it.get("url", ""))
        content = (it.get("content", "") or "").replace("\n", " ")[:200]
        print("   - content:", content)

    summary = await ai_summarizer.generate_company_news_summary_with_references(
        ticker=ticker,
        company_name=company_name,
        news_items=items,
        target_date=target_date,
        max_items=10,
    )

    print("\nSUMMARY:")
    print(summary)


if __name__ == "__main__":
    asyncio.run(main())


