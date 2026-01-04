import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from datetime import datetime
import logging
import re

from config import settings

logger = logging.getLogger(__name__)


class EmailSender:
    """邮件发送服务"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
    
    def _generate_html_content(self, digest_content: Dict[str, Any], user_email: str) -> str:
        """生成 HTML 邮件内容"""
        company_news = digest_content.get("company_news", {})
        generated_at = digest_content.get("generated_at", datetime.utcnow().isoformat())
        
        # 生成公司新闻 HTML
        company_sections = ""
        for ticker, news_list in company_news.items():
            if news_list:
                # 优先显示摘要，如果没有摘要则显示第一条新闻的摘要
                summary_news = news_list[0] if news_list else None
                if summary_news and summary_news.get('summary'):
                    # 显示摘要
                    company_name = summary_news.get('title', ticker).replace(' 新闻摘要', '')
                    summary_text = (summary_news.get('summary', '') or '').replace("\n", "<br/>")
                    items = summary_news.get("items") or []

                    # 解析摘要里的引用 [1] [2]...
                    cited_numbers = []
                    for m in re.findall(r"\[(\d{1,3})\]", summary_news.get("summary", "") or ""):
                        try:
                            n = int(m)
                        except Exception:
                            continue
                        if 1 <= n <= len(items) and n not in cited_numbers:
                            cited_numbers.append(n)

                    # 构建 references（优先展示被引用的；如果没有引用，则展示前 3 条）
                    ref_numbers = cited_numbers if cited_numbers else list(range(1, min(len(items), 3) + 1))
                    references_html = ""
                    if ref_numbers:
                        references_html += """
                        <div style="margin-top: 14px; padding-top: 12px; border-top: 1px solid #e5e7eb;">
                            <p style="color: #6b7280; font-size: 13px; margin: 0 0 8px 0;">References：</p>
                            <ul style="list-style: none; padding: 0; margin: 0;">
                        """
                        for n in ref_numbers:
                            it = items[n - 1] if (n - 1) < len(items) else {}
                            title = it.get("title", "无标题")
                            url = it.get("url", "#")
                            src = it.get("source", "未知")
                            references_html += f"""
                                <li style="margin-bottom: 6px;">
                                    <span style="color: #9ca3af; font-size: 12px; margin-right: 6px;">[{n}]</span>
                                    <a href="{url}" style="color: #2563eb; text-decoration: none; font-size: 13px;">
                                        {title}
                                    </a>
                                    <span style="color: #9ca3af; font-size: 12px; margin-left: 8px;">
                                        来源: {src}
                                    </span>
                                </li>
                            """
                        references_html += """
                            </ul>
                        </div>
                        """

                    company_sections += f"""
                    <div style="margin-bottom: 24px;">
                        <h3 style="color: #1f2937; font-size: 18px; margin-bottom: 12px; border-left: 4px solid #3b82f6; padding-left: 12px;">
                            {ticker}
                        </h3>
                        <p style="color: #374151; font-size: 15px; line-height: 1.7; margin-bottom: 12px;">
                            {summary_text}
                        </p>
                        {references_html}
                    </div>
                    """
                else:
                    # 如果没有摘要，使用原来的格式
                    news_items_html = ""
                    for news in news_list[:3]:  # 每个公司最多3条新闻
                        summary_text = news.get('summary', '')
                        if not summary_text and news.get('content'):
                            summary_text = news.get('content', '')[:200]
                        
                        news_items_html += f"""
                        <li style="margin-bottom: 10px;">
                            <a href="{news.get('url', '#')}" style="color: #2563eb; text-decoration: none; font-weight: 500;">
                                {news.get('title', '无标题')}
                            </a>
                            <p style="margin: 5px 0 0 0; color: #6b7280; font-size: 14px;">
                                {summary_text}
                            </p>
                            <span style="color: #9ca3af; font-size: 12px;">
                                来源: {news.get('source', '未知')}
                            </span>
                        </li>
                        """
                    
                    company_sections += f"""
                    <div style="margin-bottom: 24px;">
                        <h3 style="color: #1f2937; font-size: 18px; margin-bottom: 12px; border-left: 4px solid #3b82f6; padding-left: 12px;">
                            {ticker}
                        </h3>
                        <ul style="list-style: none; padding: 0; margin: 0;">
                            {news_items_html}
                        </ul>
                    </div>
                    """
        
        # 行业新闻已融合到“公司摘要”中，此处不再单独展示
        industry_section = ""
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #374151; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 24px; border-radius: 12px 12px 0 0;">
                <h1 style="margin: 0; font-size: 24px;">📈 StockDaily Digest</h1>
                <p style="margin: 8px 0 0 0; opacity: 0.9;">您的每日美股新闻摘要</p>
            </div>
            
            <div style="background: #ffffff; padding: 24px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 12px 12px;">
                <p style="color: #6b7280; font-size: 14px; margin-bottom: 24px;">
                    📅 {datetime.fromisoformat(generated_at).strftime('%Y年%m月%d日')} | 发送至: {user_email}
                </p>
                
                <h2 style="color: #1f2937; font-size: 20px; margin-bottom: 16px;">
                    🏢 公司新闻
                </h2>
                
                {company_sections if company_sections else '<p style="color: #6b7280;">暂无公司新闻</p>'}
                {industry_section}
                
                <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid #e5e7eb; text-align: center; color: #9ca3af; font-size: 12px;">
                    <p>此邮件由 StockDaily Digest 自动发送</p>
                    <p>如需修改关注列表，请访问 <a href="#" style="color: #3b82f6;">网站</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    async def send_digest_email(
        self,
        to_email: str,
        digest_content: Dict[str, Any],
        date_str: str
    ) -> bool:
        """
        发送日报邮件
        
        Args:
            to_email: 收件人邮箱
            digest_content: 日报内容
            date_str: 日期字符串
            
        Returns:
            是否发送成功
        """
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP 未配置，跳过邮件发送")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"📈 您的每日美股新闻摘要 - {date_str}"
            msg["From"] = self.from_email
            msg["To"] = to_email
            
            # HTML 内容
            html_content = self._generate_html_content(digest_content, to_email)
            html_part = MIMEText(html_content, "html", "utf-8")
            msg.attach(html_part)
            
            # 发送邮件
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=True
            )
            
            logger.info(f"邮件已发送至 {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"发送邮件失败: {str(e)}")
            return False


# 单例实例
email_sender = EmailSender()
