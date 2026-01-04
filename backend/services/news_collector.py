import httpx
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import logging
import json
import re

from config import settings

logger = logging.getLogger(__name__)


class NewsCollector:
    """新闻收集服务 - 使用 supermind-agent-v1 进行搜索"""
    
    def __init__(self):
        self.api_url = f"{settings.AI_BUILDER_API_URL}/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {settings.AI_BUILDER_TOKEN}",
            "Content-Type": "application/json"
        }

    async def _chat_completion(
        self,
        prompt: str,
        *,
        max_tokens: int = 800,
        temperature: float = 0.2,
        timeout: float = 60.0,
    ) -> str:
        """调用 Chat Completions（不做 web search），返回纯文本 content。"""
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self.api_url,
                headers=self.headers,
                json={
                    "model": "supermind-agent-v1",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            if response.status_code != 200:
                raise RuntimeError(f"chat completion failed: {response.status_code} - {response.text}")
            data = response.json()
            return (data["choices"][0]["message"]["content"] or "").strip()

    def _extract_json_array(self, content: str) -> list:
        """从模型返回文本中尽量提取 JSON 数组；失败则返回空数组。"""
        if not content:
            return []
        json_match = re.search(r"\[[\s\S]*\]", content)
        if not json_match:
            return []
        try:
            parsed = json.loads(json_match.group(0))
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []

    def _dedupe_news_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按 url/标题去重，保留先出现的条目。"""
        seen: set[str] = set()
        out: List[Dict[str, Any]] = []
        for it in items or []:
            url = (it.get("url") or "").strip()
            title = (it.get("title") or "").strip()
            key = url or title
            if not key:
                continue
            key_norm = key.lower()
            if key_norm in seen:
                continue
            seen.add(key_norm)
            out.append(it)
        return out

    async def propose_industry_context_queries(
        self,
        *,
        ticker: str,
        company_name: str,
        main_industry: str,
        sub_industries: List[str],
        target_date: str,
        tz_name: str,
        max_queries: int = 3,
    ) -> List[str]:
        """
        让 AI 生成“行业级”的 web search 查询词（默认不包含公司名/ticker），用于找可能影响公司的重大行业事件。
        """
        sub = ", ".join([s for s in (sub_industries or []) if s][:3])
        prompt = f"""You are a professional public equities investor.
Generate {max_queries} web search queries to find MAJOR industry/competitor/supply-chain/regulatory/technology-breakthrough news
that could affect {company_name} ({ticker}) on {target_date} (timezone context: {tz_name}).

Company context:
- Main industry: {main_industry or "Unknown"}
- Sub-industries (if any): {sub or "Unknown"}

Rules (critical):
1) Do NOT include the company name "{company_name}" nor the ticker "{ticker}" in the queries unless absolutely necessary.
2) Focus on: competitors moves, key suppliers/components, channel checks/demand signals, pricing, recalls, export controls,
   regulation/antitrust, standards, major product launches by peers, M&A, investigations, sanctions.
3) Prefer concise English queries that work well for web search.
4) Output ONLY a valid JSON array of strings. No explanation.
"""
        try:
            content = await self._chat_completion(prompt, max_tokens=400, temperature=0.2, timeout=45.0)
            arr = self._extract_json_array(content)
            queries = [q.strip() for q in arr if isinstance(q, str) and q.strip()]
            return queries[:max_queries] if queries else []
        except Exception as e:
            logger.warning(f"生成行业 context queries 失败，回退到模板：{e}")
            # 兜底：不包含公司名/ticker，仅用行业词
            seed = sub_industries[0] if sub_industries else (main_industry or "technology hardware")
            return [
                f"{seed} industry major news regulatory supply chain competitor developments",
                f"{seed} market demand channel checks pricing inventory competitor launches",
                f"{seed} export controls sanctions antitrust investigation standards",
            ][:max_queries]

    async def filter_relevant_context_news(
        self,
        *,
        ticker: str,
        company_name: str,
        main_industry: str,
        sub_industries: List[str],
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        让 AI 从“行业级新闻候选集”里筛选出最可能影响该公司的条目（即使标题不含公司名/ticker）。
        返回筛选后的 news_items（按相关度降序）。
        """
        if not candidates:
            return []

        sub = ", ".join([s for s in (sub_industries or []) if s][:3])

        # 为了控制 token，候选只取前 12 条
        trimmed = (candidates or [])[:12]
        lines = []
        for i, it in enumerate(trimmed):
            title = (it.get("title") or "")[:180]
            content = (it.get("content") or "")[:220]
            source = (it.get("source") or "unknown")[:60]
            url = (it.get("url") or "")[:240]
            pd = (it.get("published_date") or "")[:20]
            lines.append(f'{i}. [{pd}] {title} ({source}) :: {content} :: {url}')

        prompt = f"""You are an experienced investor building an "industry context" section.
Select the items that are most likely to impact {company_name} ({ticker}) within 6-12 months.

Company profile (high-level):
- Main industry: {main_industry or "Unknown"}
- Sub-industries: {sub or "Unknown"}

Candidate news items (may NOT mention the company; that's OK):
{chr(10).join(lines)}

Selection rules (critical):
1) Prefer concrete new developments (regulation, supply chain disruption, major competitor action, tech breakthrough, investigations, sanctions).
2) Avoid generic "stock up/down", "year outlook" with no new event.
3) Choose up to {top_k} items. Rank by impact.

Output format (ONLY valid JSON array, no explanation):
Each element: {{"index": <int>, "relevance_score": <0-100>, "why": "<short chinese reason>" }}
"""
        try:
            content = await self._chat_completion(prompt, max_tokens=600, temperature=0.2, timeout=60.0)
            arr = self._extract_json_array(content)
            picks = []
            for obj in arr:
                if not isinstance(obj, dict):
                    continue
                idx = obj.get("index")
                score = obj.get("relevance_score", 0)
                if isinstance(idx, int) and 0 <= idx < len(trimmed):
                    try:
                        score_int = int(score)
                    except Exception:
                        score_int = 0
                    picks.append((idx, score_int))
            # 去重 + 排序
            best: Dict[int, int] = {}
            for idx, sc in picks:
                best[idx] = max(best.get(idx, 0), sc)
            ranked = sorted(best.items(), key=lambda x: x[1], reverse=True)[:top_k]
            selected = [trimmed[idx] for idx, _ in ranked]
            return selected
        except Exception as e:
            logger.warning(f"AI 相关性筛选失败，回退为前 {top_k} 条：{e}")
            return trimmed[:top_k]

    async def collect_context_news_for_company(
        self,
        *,
        ticker: str,
        company_name: str,
        main_industry: str,
        sub_industries: List[str],
        user_timezone: Optional[str] = None,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        收集“行业/竞争/技术突破”的 context 新闻：
        - 先由 AI 生成行业级 query（默认不含公司名/ticker）
        - 拉取候选集
        - 再由 AI 选择最可能影响该公司的 Top N
        """
        target_date, tz_name = self._get_target_date(user_timezone)
        queries = await self.propose_industry_context_queries(
            ticker=ticker,
            company_name=company_name,
            main_industry=main_industry,
            sub_industries=sub_industries,
            target_date=target_date,
            tz_name=tz_name,
            max_queries=3,
        )

        candidates: List[Dict[str, Any]] = []
        # 每个 query 拉 5 条，避免太慢/太贵
        per_query = 5
        for q in queries[:3]:
            items = await self.search_news_via_agent(
                search_query=q,
                target_date=target_date,
                tz_name=tz_name,
                max_results=per_query,
            )
            candidates.extend(items or [])

        candidates = self._dedupe_news_items(candidates)
        if not candidates:
            return []

        selected = await self.filter_relevant_context_news(
            ticker=ticker,
            company_name=company_name,
            main_industry=main_industry,
            sub_industries=sub_industries,
            candidates=candidates,
            top_k=max_results,
        )
        return selected
    
    def _get_target_date(self, user_timezone: Optional[str] = None) -> tuple[str, str]:
        """
        获取目标日期（前一天），只精确到“天”。
        
        Args:
            user_timezone: 用户时区（如 "America/New_York"），如果为 None 则使用美东时间（部署每日早上8点更符合美股语境）
        
        Returns:
            (target_date, tz_name)  e.g. ("2026-01-03", "America/New_York")
        """
        tz_name = user_timezone or "America/New_York"
        now: datetime
        try:
            import pytz
            tz = pytz.timezone(tz_name)
            now = datetime.now(tz)
        except Exception as e:
            logger.warning(f"无法解析/使用时区 {tz_name}，回退到 UTC: {e}")
            tz_name = "UTC"
            now = datetime.now(timezone.utc)

        target_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        return target_date, tz_name
    
    async def search_news_via_agent(
        self, 
        search_query: str, 
        target_date: str,
        tz_name: str,
        max_results: int = 5,
        max_retries: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        使用 supermind-agent-v1 进行新闻搜索（带重试机制）
        
        Args:
            search_query: 搜索查询内容
            target_date: 目标日期（YYYY-MM-DD，前一天）
            tz_name: 时区名称（用于展示给模型）
            max_results: 最多返回的结果数
            max_retries: 最大重试次数（默认2次，总共最多3次尝试）
            
        Returns:
            新闻列表
        """
        prompt = f"""你是一个面向投资者的"美股新闻检索器"。请使用 web search 工具搜索，并**只返回**在以下日期发布的新闻：

目标日期（严格遵守，只要这一天）：{target_date}（时区语境：{tz_name}）

检索主题：{search_query}

筛选要求（非常重要）：
1) **只要"具体新进展/爆料/公告/监管/供应链/产品路线图/竞争对手动作/核心技术突破/市场观点变化"**。
2) **排除**：泛泛的"估值高/便宜""年初展望""仅复述股价涨跌/收盘价/盘中波动"但没有新事件的文章。
3) 如果同一事件有多篇重复报道，只保留信息量最大的 1 篇。

输出要求：
- 返回 {max_results} 条，按"信息量/影响力"排序
- **必须输出有效 JSON 数组**，不要输出任何解释文字
- 每条包含字段：
  - title
  - content（<=200字，突出"发生了什么 + 可能影响"，不要只写股价表现）
  - url
  - source
  - published_date（YYYY-MM-DD；必须等于 {target_date}。如果网页未给出，请尽量从页面中推断；推断不了则不要返回该条）
"""

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                # 增加超时时间到 300 秒（5分钟），因为 AI agent 搜索可能需要更长时间
                async with httpx.AsyncClient(timeout=300.0) as client:
                    if attempt > 0:
                        logger.info(f"重试第 {attempt} 次: {search_query[:50]}...")
                    else:
                        logger.info(f"使用 supermind-agent-v1 搜索: {search_query[:60]}... (date: {target_date}, tz={tz_name})")
                    
                    # max_results 增大时，模型输出 JSON 会更长，需要更多 token
                    max_tokens = 3000 if max_results <= 5 else 6500
                    response = await client.post(
                        self.api_url,
                        headers=self.headers,
                        json={
                            "model": "supermind-agent-v1",
                            "messages": [
                                {"role": "user", "content": prompt}
                            ],
                            "max_tokens": max_tokens,
                            "temperature": 0.3
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        content = data["choices"][0]["message"]["content"].strip()
                        
                        # 解析 AI 返回的内容
                        news_items = self._parse_agent_response(content)
                        news_items = self._filter_by_target_date(news_items, target_date)
                        logger.info(f"搜索到 {len(news_items)} 条新闻")
                        return news_items
                    else:
                        last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                        logger.warning(f"搜索失败 (attempt {attempt+1}/{max_retries+1}): {last_error}")
                        if attempt < max_retries:
                            await asyncio.sleep(2 * (attempt + 1))  # 递增延迟：2s, 4s
                        continue
                        
            except httpx.ReadTimeout as e:
                last_error = f"超时: {str(e)}"
                logger.warning(f"搜索超时 (attempt {attempt+1}/{max_retries+1}): {search_query[:50]}...")
                if attempt < max_retries:
                    await asyncio.sleep(3 * (attempt + 1))  # 超时重试延迟更长：3s, 6s
                continue
            except Exception as e:
                last_error = str(e)
                logger.warning(f"搜索出错 (attempt {attempt+1}/{max_retries+1}): {last_error}")
                if attempt < max_retries:
                    await asyncio.sleep(2 * (attempt + 1))
                continue
        
        # 所有重试都失败
        logger.error(f"搜索最终失败（已重试 {max_retries} 次）: {search_query[:50]}... 最后错误: {last_error}")
        return []
    
    def _parse_agent_response(self, content: str) -> List[Dict[str, Any]]:
        """
        解析 AI agent 返回的内容
        
        Args:
            content: AI 返回的文本内容
            
        Returns:
            新闻列表
        """
        news_items = []
        
        # 尝试提取 JSON 数组
        # 方法1: 查找 JSON 数组（可能在代码块中）
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            try:
                json_str = json_match.group(0)
                news_items = json.loads(json_str)
                # 验证格式
                if isinstance(news_items, list):
                    for item in news_items:
                        if not isinstance(item, dict):
                            continue
                        # 确保必要字段存在
                        if 'title' not in item:
                            item['title'] = item.get('headline', '无标题')
                        if 'url' not in item:
                            item['url'] = item.get('link', '#')
                        if 'source' not in item:
                            item['source'] = '未知'
                        # 统一字段：published_date
                        if 'published_date' not in item:
                            item['published_date'] = item.get('published_at', '') or ''
                    return news_items
            except json.JSONDecodeError:
                pass
        
        # 方法2: 如果没有找到 JSON，尝试从文本中提取信息
        # 查找列表格式的内容
        lines = content.split('\n')
        current_item = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_item:
                    news_items.append(current_item)
                    current_item = {}
                continue
            
            # 尝试匹配标题
            if re.match(r'^\d+[\.\)]?\s*(.+)$', line) or line.startswith('-') or line.startswith('*'):
                if current_item:
                    news_items.append(current_item)
                title = re.sub(r'^\d+[\.\)]?\s*', '', line).strip('- *').strip()
                current_item = {
                    'title': title,
                    'content': '',
                    'url': '#',
                    'source': '未知',
                    'published_date': ''
                }
            elif 'http' in line.lower():
                current_item['url'] = line
            elif current_item and not current_item.get('content'):
                current_item['content'] = line[:200]
        
        if current_item:
            news_items.append(current_item)
        
        return news_items

    def _filter_by_target_date(self, news_items: List[Dict[str, Any]], target_date: str) -> List[Dict[str, Any]]:
        """基于 published_date 做“前一天”的硬过滤（只精确到天）。"""
        kept: List[Dict[str, Any]] = []
        fallback: List[Dict[str, Any]] = []

        for item in news_items or []:
            published_date = (item.get("published_date") or "").strip()
            if published_date == target_date:
                kept.append(item)
            else:
                fallback.append(item)

        # 理论上 prompt 已经强约束；这里兜底避免空列表
        return kept if kept else fallback[:2]
    
    async def collect_company_news(
        self, 
        tickers: List[str], 
        company_names: List[str],
        user_timezone: Optional[str] = None,
        max_results_per_company: int = 30,
    ) -> Dict[str, List[Dict]]:
        """
        收集公司相关新闻（过去的一天）
        
        Args:
            tickers: 股票代码列表
            company_names: 公司名称列表
            user_timezone: 用户时区（可选）
            
        Returns:
            Dict[ticker, List[news_items]]
        """
        target_date, tz_name = self._get_target_date(user_timezone)
        logger.info(f"收集公司新闻日期: {target_date} ({tz_name})")

        max_concurrency = max(1, int(getattr(settings, "MAX_CONCURRENT_AI_REQUESTS", 3)))
        sem = asyncio.Semaphore(max_concurrency)
        logger.info(f"公司新闻并行抓取并发度: {max_concurrency}")

        async def _fetch_one(ticker: str, name: str) -> tuple[str, List[Dict[str, Any]]]:
            async with sem:
                try:
                    search_query = (
                        f"{name} ({ticker}) breaking news leak rumor product roadmap "
                        f"earnings guidance SEC filing investigation lawsuit antitrust regulatory "
                        f"supply chain recall partnership acquisition competitor product launch "
                        f"\"last day\""
                    )

                    news_items = await self.search_news_via_agent(
                        search_query=search_query,
                        target_date=target_date,
                        tz_name=tz_name,
                        max_results=min(max_results_per_company, 30),
                    )
                    kept = (news_items or [])[: min(max_results_per_company, 30)]
                    logger.info(f"✅ {ticker} ({name}): 收集到 {len(kept)} 条新闻")
                    return ticker, kept
                except Exception as e:
                    logger.error(f"❌ {ticker} ({name}) 收集新闻失败: {str(e)}")
                    return ticker, []

        pairs = list(zip(tickers, company_names))
        tasks = [_fetch_one(t, n) for t, n in pairs]
        results_list = await asyncio.gather(*tasks, return_exceptions=False)
        return {t: items for t, items in results_list}
    
    async def collect_company_industry_news(
        self, 
        tickers: List[str], 
        company_names: List[str],
        sub_industries: Dict[str, List[str]],
        user_timezone: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        收集与用户关注公司相关的行业新闻（过去的一天）
        包括：竞争对手动态、市场分析、行业趋势等
        
        Args:
            tickers: 股票代码列表
            company_names: 公司名称列表
            sub_industries: 每个公司的细分行业 Dict[ticker, List[sub_industry]]
            user_timezone: 用户时区（可选）
            
        Returns:
            Dict[sub_industry, {news_items, related_companies}]
        """
        target_date, tz_name = self._get_target_date(user_timezone)
        logger.info(f"收集行业新闻日期: {target_date} ({tz_name})")
        
        # 收集所有唯一的细分行业
        all_sub_industries = set()
        industry_to_companies: Dict[str, List[str]] = {}  # 行业 -> 相关公司列表
        
        for ticker, industries in sub_industries.items():
            company_name = company_names[tickers.index(ticker)] if ticker in tickers else ticker
            for industry in industries:
                all_sub_industries.add(industry)
                if industry not in industry_to_companies:
                    industry_to_companies[industry] = []
                industry_to_companies[industry].append(f"{ticker} ({company_name})")
        
        results = {}
        
        # 为每个细分行业搜索新闻
        for industry in all_sub_industries:
            related_companies = industry_to_companies.get(industry, [])
            company_tickers = [c.split(" ")[0] for c in related_companies]
            related_names = []
            for c in related_companies[:3]:
                m = re.search(r'\((.+)\)', c)
                if m:
                    related_names.append(m.group(1))
            
            # 构建搜索查询：行业 + 竞争对手 + 市场分析 + 相关公司
            search_query = (
                f"{industry} industry news competitor supply chain regulatory "
                f"market sentiment analyst view channel checks "
                f"{' '.join(company_tickers[:3])} {' '.join(related_names[:3])} "
                f"\"last day\""
            )
            
            # 使用 AI agent 搜索
            news_items = await self.search_news_via_agent(
                search_query=search_query,
                target_date=target_date,
                tz_name=tz_name,
                max_results=5
            )
            
            results[industry] = {
                "news_items": news_items,
                "related_companies": related_companies
            }
        
        return results


# 单例实例
news_collector = NewsCollector()
