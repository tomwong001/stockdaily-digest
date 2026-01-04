from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from config import settings

# 创建数据库引擎
# SQLite 需要 check_same_thread=False
database_url = settings.DATABASE_URL

# 兼容：当 .env 配置为 sqlite:///./stockdaily.db 时，路径会受“当前工作目录”影响。
# 这里把相对路径统一解析为 backend 目录下的 stockdaily.db，避免脚本/服务使用不同库文件。
if database_url.startswith("sqlite:///./"):
    rel = database_url[len("sqlite:///./") :]
    abs_path = (Path(__file__).parent / rel).resolve().as_posix()
    database_url = f"sqlite:///{abs_path}"

if database_url.startswith("sqlite"):
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(database_url)

# 创建 SessionLocal 类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建 Base 类
Base = declarative_base()


# 获取数据库 session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
