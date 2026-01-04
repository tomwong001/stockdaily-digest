import logging
from datetime import datetime

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models import User
from routers.digests import generate_digest_for_user
from services.email_sender import email_sender

logger = logging.getLogger(__name__)


async def _send_daily_digests_job():
    """
    遍历所有用户，生成日报并发送邮件。
    注意：这会触发新闻检索 + AI 总结，耗时较长；用户量大时需要队列化（Celery/任务队列）。
    """
    if not settings.ENABLE_DAILY_EMAIL_SCHEDULER:
        return

    tz = pytz.timezone(settings.DAILY_EMAIL_TIMEZONE)
    now_local = datetime.now(tz)
    logger.info(f"[scheduler] daily digest job started at {now_local.isoformat()}")

    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        logger.info(f"[scheduler] users={len(users)}")
        for u in users:
            try:
                content = await generate_digest_for_user(u, db)
                date_str = now_local.strftime("%Y/%m/%d")
                await email_sender.send_digest_email(
                    to_email=u.email,
                    digest_content=content,
                    date_str=date_str,
                )
            except Exception as e:
                logger.exception(f"[scheduler] failed for user={u.email}: {e}")
    finally:
        db.close()

    logger.info("[scheduler] daily digest job finished")


def start_daily_email_scheduler() -> AsyncIOScheduler | None:
    """
    在 FastAPI 启动时调用。默认关闭，通过 .env 打开。
    纽约时间每天 08:00 触发一次。
    """
    if not settings.ENABLE_DAILY_EMAIL_SCHEDULER:
        logger.info("[scheduler] ENABLE_DAILY_EMAIL_SCHEDULER=false, scheduler disabled")
        return None

    tz = pytz.timezone(settings.DAILY_EMAIL_TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)
    trigger = CronTrigger(
        hour=settings.DAILY_EMAIL_HOUR,
        minute=settings.DAILY_EMAIL_MINUTE,
        timezone=tz,
    )
    scheduler.add_job(
        _send_daily_digests_job,
        trigger=trigger,
        id="daily_digest_email",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60 * 30,
    )
    scheduler.start()
    logger.info(
        f"[scheduler] started: {settings.DAILY_EMAIL_TIMEZONE} {settings.DAILY_EMAIL_HOUR:02d}:{settings.DAILY_EMAIL_MINUTE:02d}"
    )
    return scheduler


