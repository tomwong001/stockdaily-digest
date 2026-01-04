import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging

from database import engine, Base
from routers import auth, companies, digests
from config import settings
from services.digest_scheduler import start_daily_email_scheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 应用
app = FastAPI(
    title="StockDaily Digest API",
    description="美股投资日报 - 每日新闻摘要平台 API",
    version="1.0.0"
)

# 配置 CORS（允许所有来源，部署环境需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(digests.router)

# 静态文件目录（前端构建后的文件）
STATIC_DIR = Path(__file__).parent / "static"


@app.on_event("startup")
async def _startup():
    """应用启动时执行"""
    logger.info(f"Static directory: {STATIC_DIR}")
    logger.info(f"Static directory exists: {STATIC_DIR.exists()}")
    if STATIC_DIR.exists():
        logger.info(f"Static directory contents: {list(STATIC_DIR.iterdir())}")
    
    # 挂载静态资源目录（在启动时检查，而不是模块加载时）
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        logger.info(f"Mounted /assets from {assets_dir}")
    
    # 启动每日邮件调度器（AsyncIOScheduler 在同一事件循环中运行，不是独立进程）
    start_daily_email_scheduler()


@app.get("/api/health")
def health_check():
    """API 健康检查"""
    return {"status": "healthy"}


@app.get("/api/status")
def api_status():
    """API 状态"""
    return {
        "status": "ok",
        "message": "StockDaily Digest API is running",
        "version": "1.0.0",
        "static_dir_exists": STATIC_DIR.exists(),
        "index_exists": (STATIC_DIR / "index.html").exists() if STATIC_DIR.exists() else False,
    }


# 根路由：返回前端页面
@app.get("/")
async def serve_root():
    """根路由：返回前端页面"""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    # 如果没有前端，返回 API 状态
    return {
        "status": "ok",
        "message": "StockDaily Digest API is running",
        "version": "1.0.0",
        "note": "Frontend not available. Use /api/* endpoints or /docs for API documentation.",
        "static_dir": str(STATIC_DIR),
        "static_exists": STATIC_DIR.exists(),
    }


# SPA 路由 fallback（必须放在最后）
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """SPA 路由：所有非 API 路由返回 index.html"""
    # 检查是否是静态文件请求
    file_path = STATIC_DIR / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    
    # 其他路由返回 index.html（SPA 路由）
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    
    return {"error": "Not found", "path": full_path}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
