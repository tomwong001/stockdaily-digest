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
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 应用
app = FastAPI(
    title="StockDaily Digest API",
    description="美股投资日报 - 每日新闻摘要平台 API",
    version="1.0.0"
)

# 配置 CORS（允许部署后的域名访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "https://*.ai-builders.space",  # 部署后的域名
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(digests.router)


@app.on_event("startup")
async def _startup():
    # 可选：纽约时间每天 08:00 自动发送日报邮件
    start_daily_email_scheduler()


@app.get("/")
def root():
    """健康检查"""
    return {
        "status": "ok",
        "message": "StockDaily Digest API is running",
        "version": "1.0.0"
    }


@app.get("/api/health")
def health_check():
    """API 健康检查"""
    return {"status": "healthy"}


# 静态文件服务（生产环境：前端构建后的文件）
# 在部署时，前端会被构建并复制到 /app/static 目录
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    # 挂载静态资源（JS, CSS, images 等）
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    
    # 所有非 API 路由返回 index.html（支持前端 SPA 路由）
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # API 路由不走这里（已经被上面的路由处理）
        if full_path.startswith("api/"):
            return {"error": "Not found"}
        
        # 检查是否是静态文件请求
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # 其他路由返回 index.html（SPA 路由）
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        
        return {"error": "Frontend not built"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
