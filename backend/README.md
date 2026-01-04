# StockDaily Digest 后端

美股投资日报 - 每日新闻摘要平台后端 API

## 技术栈

- FastAPI (Python Web 框架)
- SQLAlchemy (ORM)
- PostgreSQL (数据库)
- JWT (认证)
- Celery + Redis (定时任务，可选)

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

### 3. 创建数据库

确保 PostgreSQL 运行中，然后创建数据库：

```sql
CREATE DATABASE stockdaily;
```

### 4. 启动服务

```bash
# 开发模式
uvicorn main:app --reload --port 8000

# 或者
python main.py
```

API 文档: http://localhost:8000/docs

## API 接口

### 认证 API
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录

### 公司管理 API
- `GET /api/companies/search?q={query}` - 搜索公司
- `GET /api/user/companies` - 获取用户关注列表
- `POST /api/user/companies` - 添加关注公司
- `DELETE /api/user/companies/{company_id}` - 取消关注

### 日报 API
- `POST /api/digests/generate` - 手动生成日报
- `GET /api/digests/today` - 获取今日日报
- `GET /api/digests` - 获取历史日报列表

## 目录结构

```
backend/
├── main.py              # FastAPI 应用入口
├── config.py            # 配置文件
├── database.py          # 数据库连接
├── models.py            # SQLAlchemy 模型
├── schemas.py           # Pydantic 模型
├── auth.py              # JWT 认证
├── routers/
│   ├── auth.py          # 认证路由
│   ├── companies.py     # 公司管理路由
│   └── digests.py       # 日报路由
├── services/
│   ├── news_collector.py    # 新闻收集服务
│   ├── ai_summarizer.py     # AI 摘要服务
│   └── email_sender.py      # 邮件发送服务
├── requirements.txt
└── .env.example
```

## 使用 SQLite（开发用）

如果不想配置 PostgreSQL，可以使用 SQLite：

修改 `config.py`：
```python
DATABASE_URL: str = "sqlite:///./stockdaily.db"
```

修改 `database.py`：
```python
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False}  # SQLite 需要
)
```
