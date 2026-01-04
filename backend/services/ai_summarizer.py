import httpx
from typing import List, Dict, Any
import logging

from config import settings

logger = logging.getLogger(__name__)


class AISummarizer:
    """AI 摘要服务 - 使用 AI Builder Chat API"""
    
    def __init__(self):
        self.api_url = f"{settings.AI_BUILDER_API_URL}/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {settings.AI_BUILDER_TOKEN}",
            "Content-Type": "application/json"
        }
    
    async def summarize_news(self, news_items: List[Dict[str, Any]], company_name: str) -> str:
        """
        生成新闻摘要
        
        Args:
            news_items: 新闻列表
            company_name: 公司名称
            
        Returns:
            摘要文本
        """
        if not news_items:
            return f"过去24小时内没有关于 {company_name} 的重要新闻。"
        
        # 构建提示词
        news_text = "\n".join([
            f"- {item.get('title', '')}: {item.get('content', '')[:200]}..."
            for item in news_items[:5]  # 最多5条新闻
        ])
        
        prompt = f"""请用中文为以下关于 {company_name} 的新闻生成简洁的摘要（2-3句话），重点关注对投资者重要的信息：

{news_text}

请直接输出摘要，不要加任何前缀。"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json={
                        "model": "supermind-agent-v1",
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 500,
                        "temperature": 0.7
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    # 清理内容：移除可能的思考过程标记
                    # 如果包含"Here's my thinking"或类似标记，只保留最后部分
                    if "Here's my thinking" in content or "Here's my thinking process" in content:
                        # 尝试提取最终摘要（通常在"Final answer:"或类似标记之后）
                        parts = content.split("Final answer:")
                        if len(parts) > 1:
                            content = parts[-1].strip()
                        else:
                            # 如果没有"Final answer:"，尝试提取最后一段
                            paragraphs = content.split("\n\n")
                            # 找到最后一个非空段落，通常是摘要
                            for para in reversed(paragraphs):
                                para = para.strip()
                                if para and len(para) > 20 and not para.startswith("Here's"):
                                    content = para
                                    break
                    # 移除任何剩余的思考过程标记
                    content = content.replace("Here's my thinking process", "").replace("Here's my thinking", "").strip()
                    # 移除常见中文前缀（模型有时会加礼貌语/说明语）
                    chinese_prefixes = [
                        "好的，这是为您生成的摘要：",
                        "好的，这是摘要：",
                        "以下是摘要：",
                        "摘要：",
                        "总结：",
                    ]
                    for p in chinese_prefixes:
                        if content.startswith(p):
                            content = content[len(p):].strip()
                    # 如果内容以"1."或"*"开头，可能是列表格式，提取主要内容
                    if content.startswith("1.") or content.startswith("*"):
                        lines = content.split("\n")
                        # 提取前2-3行作为摘要
                        content = "\n".join(lines[:3]).strip()
                    return content
                else:
                    logger.error(f"AI 摘要失败: {response.status_code}")
                    return f"关于 {company_name} 有 {len(news_items)} 条新闻更新。"
                    
        except Exception as e:
            logger.error(f"AI 摘要时出错: {str(e)}")
            return f"关于 {company_name} 有 {len(news_items)} 条新闻更新。"

    async def generate_company_digest_summary(
        self,
        ticker: str,
        company_name: str,
        company_news: List[Dict[str, Any]],
        context_news: List[Dict[str, Any]],
        target_date: str,
    ) -> str:
        """
        生成“公司摘要（融合行业/竞争对手/技术突破）”：
        - company_news：公司直接相关新闻
        - context_news：围绕公司相关行业/竞争对手/核心技术突破的新闻
        """
        if not company_news and not context_news:
            return f"{target_date} 没有找到关于 {company_name} 的重要新闻。"

        def fmt(items: List[Dict[str, Any]]) -> str:
            lines = []
            for it in (items or [])[:5]:
                title = it.get("title", "")
                content = (it.get("content", "") or "")[:200]
                src = it.get("source", "未知")
                pd = it.get("published_date", "")
                lines.append(f"- [{pd}] {title}（{src}）: {content}")
            return "\n".join(lines)

        company_block = fmt(company_news)
        context_block = fmt(context_news)

        prompt = f"""请用中文输出 {ticker}（{company_name}）在 {target_date} 这一天的“投资者摘要”（2-3句话），要求：

1) 第1句：概括公司本身的关键新进展（产品/监管/供应链/战略/合作/诉讼/业绩指引等），必须是“具体事件”，不要只写股价/估值。
2) 第2句：补充与该公司相关的“行业/竞争对手/核心技术突破/市场观点变化”（例如：AR/VR、手机产业链、AI/自动驾驶、芯片、模型能力等），点出可能影响。
3) 如果当天没有真正的事件，只允许输出：“{target_date} 没有显著公司事件，市场主要是观点/预期类讨论。”（不要编造）
4) 严格不要加任何前缀（如“好的/以下是摘要/摘要：”）。

公司直接相关新闻（只来自 {target_date}）：
{company_block if company_block else "(无)"} 

行业/竞争对手/技术突破相关新闻（只来自 {target_date}）：
{context_block if context_block else "(无)"}"""

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json={
                        "model": "supermind-agent-v1",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 500,
                        "temperature": 0.4,
                    },
                )

                if response.status_code != 200:
                    logger.error(f"融合公司摘要失败: {response.status_code}")
                    return f"{target_date} 关于 {company_name} 有新闻更新。"

                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()

                # 复用已有清理逻辑（思考过程/前缀）
                if "Here's my thinking" in content or "Here's my thinking process" in content:
                    parts = content.split("Final answer:")
                    content = parts[-1].strip() if len(parts) > 1 else content.strip()

                content = content.replace("Here's my thinking process", "").replace("Here's my thinking", "").strip()
                chinese_prefixes = ["好的，这是为您生成的摘要：", "好的，这是摘要：", "以下是摘要：", "摘要：", "总结："]
                for p in chinese_prefixes:
                    if content.startswith(p):
                        content = content[len(p):].strip()

                return content
        except Exception as e:
            logger.error(f"融合公司摘要时出错: {str(e)}")
            return f"{target_date} 关于 {company_name} 有新闻更新。"

    async def generate_company_news_summary_with_references(
        self,
        *,
        ticker: str,
        company_name: str,
        news_items: List[Dict[str, Any]],
        target_date: str,
        max_items: int = 30,
    ) -> str:
        """
        只基于“公司相关新闻”生成投资者摘要，并在句子中用 [1] [2] 形式做引用标注。
        引用编号对应下方新闻清单序号（1..N）。
        """
        items = (news_items or [])[: min(max_items, 30)]
        if not items:
            return f"{target_date} 没有找到关于 {company_name} 的重要新闻。"

        lines = []
        for i, it in enumerate(items, 1):
            title = (it.get("title", "") or "")[:200]
            content = (it.get("content", "") or "")[:220]
            src = (it.get("source", "未知") or "未知")[:60]
            url = (it.get("url", "") or "")[:300]
            pd = (it.get("published_date", "") or "")[:20]
            lines.append(f"{i}. [{pd}] {title}（{src}）: {content} | {url}")

        def build_prompt(extra_rules: str = "") -> str:
            return f"""请用中文输出 {ticker}（{company_name}）在 {target_date} 这一天的“投资者摘要”（2-4 句话），要求：

1) 只基于下面提供的新闻清单，不要编造。
2) 重点写“发生了什么 + 可能影响（基本面/竞争格局/监管/供应链/需求/利润率等）”。
3) **每句话**必须至少包含 1 个引用编号，格式必须是 [数字]，例如：[1] 或 [2][5]。
4) 引用编号只能引用下面清单中的条目序号（1..{len(items)}）。
5) 不要输出空泛的“没有显著公司事件/主要是观点”作为整段结论；即使信息偏观点，也要指出**最具体**的 1-2 条内容是什么，并引用。
6) 严格不要加任何前缀（如“好的/以下是摘要/摘要：”）。
{extra_rules}

新闻清单（仅供引用）：
{chr(10).join(lines)}
"""
        async def call_once(prompt_text: str, *, temperature: float) -> str:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json={
                        "model": "supermind-agent-v1",
                        "messages": [{"role": "user", "content": prompt_text}],
                        "max_tokens": 650,
                        "temperature": temperature,
                    },
                )
                if response.status_code != 200:
                    raise RuntimeError(f"summary request failed: {response.status_code}")
                data = response.json()
                content = (data["choices"][0]["message"]["content"] or "").strip()

                # 清理（保留 [1] 这种引用标注）
                if "Here's my thinking" in content or "Here's my thinking process" in content:
                    parts = content.split("Final answer:")
                    content = parts[-1].strip() if len(parts) > 1 else content.strip()
                content = content.replace("Here's my thinking process", "").replace("Here's my thinking", "").strip()
                chinese_prefixes = ["好的，这是为您生成的摘要：", "好的，这是摘要：", "以下是摘要：", "摘要：", "总结："]
                for p in chinese_prefixes:
                    if content.startswith(p):
                        content = content[len(p):].strip()
                return content

        def has_citations(text: str) -> bool:
            import re
            return bool(re.search(r"\[\d{1,3}\]", text or ""))

        try:
            content = await call_once(build_prompt(), temperature=0.4)

            # 如果模型输出了“没有显著公司事件/观点”这种空泛结论，或没有引用，自动重试一次（更严格）。
            if ("没有显著公司事件" in content) or ("主要是观点" in content) or (not has_citations(content)):
                retry_rules = (
                    "7) 必须从清单中挑出至少 2 条最具体的“事件/进展”（例如诉讼/监管/供应链/产品计划/安全事件），分别点出影响并引用。\n"
                    "8) 每句话都必须包含引用编号；不要输出“没有显著公司事件”。"
                )
                content = await call_once(build_prompt(extra_rules=retry_rules), temperature=0.2)

            # 最后兜底：如果仍无引用，则用标题做一个安全摘要（保证不空泛）
            if not has_citations(content):
                t1 = (items[0].get("title") or "").strip()
                t2 = (items[1].get("title") or "").strip() if len(items) > 1 else ""
                parts = [p for p in [t1, t2] if p]
                if parts:
                    content = f"{target_date} 相关新闻主要包括：{parts[0]}[1]" + (f"；以及 {parts[1]}[2]" if len(parts) > 1 else "。")
            return content
        except Exception as e:
            logger.error(f"公司摘要(引用)时出错: {str(e)}")
            return f"{target_date} 关于 {company_name} 有新闻更新。"
    
    async def generate_industry_summary(self, industry: str, news_items: List[Dict[str, Any]], related_companies: List[str] = None) -> str:
        """
        生成行业新闻摘要（与用户关注公司相关的行业动态）
        
        Args:
            industry: 行业名称
            news_items: 新闻列表
            related_companies: 相关公司列表（用户关注的）
            
        Returns:
            摘要文本
        """
        if not news_items:
            return f"过去24小时内没有关于 {industry} 行业的重要新闻。"
        
        news_text = "\n".join([
            f"- {item.get('title', '')}: {item.get('content', '')[:200]}..."
            for item in news_items[:5]
        ])
        
        # 如果有相关公司，在prompt中提及
        company_context = ""
        if related_companies:
            company_context = f"（您关注的相关公司：{', '.join(related_companies[:3])}）"
        
        prompt = f"""请用中文为以下 {industry} 行业新闻生成简洁的摘要（2-3句话）{company_context}。

重点关注：
1. 行业整体趋势和动态
2. 竞争对手情况
3. 市场分析和对投资者的影响

新闻内容：
{news_text}

请直接输出摘要，不要加任何前缀。"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json={
                        "model": "supermind-agent-v1",
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 500,
                        "temperature": 0.7
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    # 清理内容：移除可能的思考过程标记
                    if "Here's my thinking" in content or "Here's my thinking process" in content:
                        parts = content.split("Final answer:")
                        if len(parts) > 1:
                            content = parts[-1].strip()
                        else:
                            paragraphs = content.split("\n\n")
                            for para in reversed(paragraphs):
                                para = para.strip()
                                if para and len(para) > 20 and not para.startswith("Here's"):
                                    content = para
                                    break
                    content = content.replace("Here's my thinking process", "").replace("Here's my thinking", "").strip()
                    # 移除常见中文前缀（模型有时会加礼貌语/说明语）
                    chinese_prefixes = [
                        "好的，这是为您生成的摘要：",
                        "好的，这是摘要：",
                        "以下是摘要：",
                        "摘要：",
                        "总结：",
                    ]
                    for p in chinese_prefixes:
                        if content.startswith(p):
                            content = content[len(p):].strip()
                    if content.startswith("1.") or content.startswith("*"):
                        lines = content.split("\n")
                        content = "\n".join(lines[:3]).strip()
                    return content
                else:
                    logger.error(f"行业摘要失败: {response.status_code}")
                    return f"{industry} 行业有 {len(news_items)} 条新闻更新。"
                    
        except Exception as e:
            logger.error(f"行业摘要时出错: {str(e)}")
            return f"{industry} 行业有 {len(news_items)} 条新闻更新。"
    
    async def classify_sub_industries(self, ticker: str, company_name: str, main_industry: str) -> List[str]:
        """
        使用 AI 判断公司所属的细分行业
        
        Args:
            ticker: 股票代码
            company_name: 公司名称
            main_industry: 大类行业名称
            
        Returns:
            细分行业列表（中文）
        """
        prompt = f"""请根据以下公司信息，判断该公司属于哪些细分行业（子行业）。

公司信息：
- 股票代码: {ticker}
- 公司名称: {company_name}
- 大类行业: {main_industry}

请从以下细分行业类别中选择最相关的1-3个（用中文回答，用逗号分隔）：
- 芯片半导体
- 软件云服务
- 人工智能
- 硬件设备
- 电动汽车
- 自动驾驶
- 生物医药
- 医疗设备
- 银行
- 金融科技
- 零售
- 电商
- 社交媒体
- 流媒体

如果以上类别都不合适，请根据公司业务特点，提供一个简洁的中文细分行业名称（1-3个，用逗号分隔）。

请直接输出细分行业名称，不要加任何前缀或解释。例如：芯片半导体,人工智能"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json={
                        "model": "supermind-agent-v1",
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 200,
                        "temperature": 0.3  # 降低温度以获得更一致的结果
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    
                    # 清理内容：移除可能的思考过程标记
                    if "Here's my thinking" in content or "Here's my thinking process" in content:
                        parts = content.split("Final answer:")
                        if len(parts) > 1:
                            content = parts[-1].strip()
                        else:
                            paragraphs = content.split("\n\n")
                            for para in reversed(paragraphs):
                                para = para.strip()
                                if para and len(para) > 5 and not para.startswith("Here's"):
                                    content = para
                                    break
                    
                    content = content.replace("Here's my thinking process", "").replace("Here's my thinking", "").strip()
                    
                    # 解析结果：按逗号分割，清理空白
                    sub_industries = [s.strip() for s in content.split(",") if s.strip()]
                    
                    # 如果结果为空，返回默认值
                    if not sub_industries:
                        logger.warning(f"AI 未返回细分行业，使用默认值: {main_industry}")
                        return [main_industry] if main_industry else []
                    
                    return sub_industries
                else:
                    logger.error(f"AI 行业分类失败: {response.status_code}")
                    return [main_industry] if main_industry else []
                    
        except Exception as e:
            logger.error(f"AI 行业分类时出错: {str(e)}")
            return [main_industry] if main_industry else []


# 单例实例
ai_summarizer = AISummarizer()
