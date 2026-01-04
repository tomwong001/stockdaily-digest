"""快速测试：使用真实新闻发送邮件"""
import asyncio
import sys
import os
from datetime import datetime

# 设置编码
if sys.platform == 'win32':
    try:
        os.system('chcp 65001 >nul')
    except:
        pass

from services.email_sender import email_sender
from config import settings
from database import SessionLocal, Base, engine
from models import User, UserCompany
from routers.digests import generate_digest_for_user


async def main():
    print("=" * 60)
    print("使用真实新闻数据测试邮件发送")
    print("=" * 60)
    
    # 这里填写“已注册用户邮箱”，公司列表将从数据库 user_companies 自动读取（不再 hardcode）
    target_email = "2841969860w@gmail.com"
    
    # 检查配置
    print(f"\n检查配置...")
    print(f"  SMTP_HOST: {settings.SMTP_HOST}")
    print(f"  SMTP_PORT: {settings.SMTP_PORT}")
    print(f"  SMTP_USER: {settings.SMTP_USER if settings.SMTP_USER else '(未设置)'}")
    print(f"  SMTP_PASSWORD: {'已设置' if settings.SMTP_PASSWORD else '(未设置)'}")
    print(f"  FROM_EMAIL: {settings.FROM_EMAIL}")
    print(f"  AI_BUILDER_TOKEN: {'已设置' if settings.AI_BUILDER_TOKEN else '(未设置)'}")
    
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print("\n错误: SMTP 未配置！请检查 .env 文件")
        print(f"  .env 文件路径: {os.path.join(os.path.dirname(__file__), '.env')}")
        return
    
    if not settings.AI_BUILDER_TOKEN:
        print("\n错误: AI_BUILDER_TOKEN 未配置！请检查 .env 文件")
        return
    
    print(f"\n目标邮箱: {target_email}")
    print(f"收集前一天的真实新闻（按天）...")
    
    try:
        # 确保表已创建（防止脚本单独运行时出现 no such table）
        Base.metadata.create_all(bind=engine)

        # 从 DB 找到用户 + 其关注公司列表
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == target_email).first()
            if not user:
                print(f"\n错误: 数据库中未找到用户 {target_email}，请先注册并添加关注公司。")
                return

            user_companies = db.query(UserCompany).filter(UserCompany.user_id == user.id).all()
            if not user_companies:
                print(f"\n错误: 用户 {target_email} 尚未关注任何公司，请先在前端添加关注。")
                return

            print("\n将为用户生成日报（公司列表来自数据库）：")
            for uc in user_companies:
                print(f"  - {uc.company.ticker} ({uc.company.name})")

            # 生成日报内容（与真实接口一致）
            digest_content = await generate_digest_for_user(user, db)
        finally:
            db.close()
        
        # 4. 发送邮件
        print(f"\n正在发送邮件到 {target_email}...")
        date_str = datetime.now().strftime("%Y/%m/%d")
        
        success = await email_sender.send_digest_email(
            to_email=target_email,
            digest_content=digest_content,
            date_str=date_str
        )
        
        if success:
            print("\n邮件发送成功！")
            print(f"请检查 {target_email} 的收件箱（包括垃圾邮件文件夹）")
            print(f"\n邮件内容摘要:")
            company_news_count = len(digest_content.get("company_news", {}))
            print(f"   - 公司新闻: {company_news_count} 家公司")
            print(f"   - 行业信息: 已融合到公司摘要中（不再单独展示）")
        else:
            print("\n邮件发送失败")
            
    except Exception as e:
        print(f"\n处理过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试已取消")
        sys.exit(0)

