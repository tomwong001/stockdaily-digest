from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

# 获取 backend 目录的绝对路径
BACKEND_DIR = Path(__file__).parent.resolve()
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    # 数据库配置 (默认使用 SQLite 方便开发)
    DATABASE_URL: str = "sqlite:///./stockdaily.db"
    
    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379"
    
    # JWT 配置
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 天
    
    # AI Builder API
    AI_BUILDER_TOKEN: Optional[str] = None
    AI_BUILDER_API_URL: str = "https://space.ai-builders.com/backend"
    
    # 邮件配置
    SMTP_HOST: str = "smtp.sendgrid.net"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: str = "noreply@stockdaily.com"
    
    # 应用配置（生产环境默认关闭 DEBUG）
    DEBUG: bool = False

    # AI/外部请求并发控制（避免 rate limit / 超时风暴）
    MAX_CONCURRENT_AI_REQUESTS: int = 3

    # 定时发送日报（纽约时间每天 08:00）
    ENABLE_DAILY_EMAIL_SCHEDULER: bool = False
    DAILY_EMAIL_TIMEZONE: str = "America/New_York"
    DAILY_EMAIL_HOUR: int = 8
    DAILY_EMAIL_MINUTE: int = 0
    
    class Config:
        env_file = str(ENV_FILE) if ENV_FILE.exists() else ".env"
        env_file_encoding = "utf-8"


settings = Settings()
