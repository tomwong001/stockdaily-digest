# 产品需求文档 (PRD) - MVP版本
## 美股投资日报 - 每日新闻摘要平台

**版本**: MVP 1.0  
**日期**: 2026 Jan 3rd  
**产品名称**: StockDaily Digest (美股日报)

---

## 1. 产品概述

### 1.1 产品定位
StockDaily Digest 是一个面向美股投资者的每日新闻摘要平台，通过 AI 技术自动收集、分析和总结过去 24 小时内与用户关注公司及行业相关的新闻，以日报形式发送给投资者。

### 1.2 核心价值
- **时效性**: 每日自动收集过去 24 小时的最新新闻
- **精准性**: AI 智能筛选与公司及行业相关的关键信息
- **便捷性**: 登录后即可使用，无需付费

---

## 2. MVP 功能需求

### 2.1 用户登录
- **简单登录系统**
  - 邮箱 + 密码登录
  - 用户注册（邮箱验证）
  - 登录后即可使用所有功能

### 2.2 公司关注管理
- **添加关注公司**
  - 通过股票代码搜索（如：AAPL, TSLA, MSFT）
  - 显示公司名称和基本信息
  - 添加后立即生效

- **删除关注公司**
  - 从关注列表中移除

### 2.3 新闻收集与处理
- **自动新闻收集**
  - 每日定时任务（早上 8:00 ET）
  - 收集过去 24 小时内的新闻
  - 使用 AI Builder API 的搜索功能收集新闻

- **AI 内容分析**
  - 使用 AI Builder API 进行新闻摘要
  - 识别新闻与公司的关联性
  - 生成简洁的新闻摘要（2-3句话）

### 2.4 日报生成
- **日报内容结构**
  1. **公司新闻** (Company News)
     - 按关注公司分组
     - 每条新闻包含：
       - 标题
       - AI 生成的摘要
       - 来源链接
       - 发布时间

  2. **行业新闻** (Industry News)
     - 关注公司所在行业的动态
     - 行业相关新闻摘要

- **生成时机**
  - 每日早上自动生成
  - 用户也可手动触发生成

### 2.5 日报发送
- **邮件发送**
  - 每日早上 8:00 ET 自动发送邮件
  - 简单的 HTML 邮件模板
  - 移动端友好

### 2.6 Web 平台（基础版）
- **公司管理页面**
  - 显示关注公司列表
  - 添加关注公司功能
  - 删除关注公司功能
  - example 日报的图片

**注意**: 日报仅通过邮件发送，不在Web平台显示

---

## 3. 技术架构

### 3.1 技术栈

#### 后端
- **框架**: FastAPI (Python)
- **数据库**: PostgreSQL
- **任务队列**: Celery + Redis（用于定时任务）
- **ORM**: SQLAlchemy
- **认证**: JWT Token

#### AI 服务集成
- **AI Builder API** (通过 MCP)
  - `/v1/chat/completions` - 使用 `supermind-agent-v1` 进行新闻摘要
  - `/v1/search/` - 使用 Tavily 搜索收集新闻

#### 前端
- **框架**: React + TypeScript
- **UI 库**: Tailwind CSS
- **路由**: React Router
- **HTTP 客户端**: Axios

#### 基础设施
- **部署平台**: AI Builder Space（通过 MCP 部署指南）
- **邮件服务**: SendGrid 或 AWS SES
- **新闻数据源**: 通过 AI Builder Search API 搜索

### 3.2 数据流程

1. **新闻收集流程**:
   ```
   定时任务触发 → 获取用户关注列表 → 
   调用 AI Builder Search API 搜索新闻 → 
   存储到数据库 → 触发摘要任务
   ```

2. **日报生成流程**:
   ```
   获取过去24小时新闻 → 
   调用 AI Builder Chat API 进行摘要 → 
   生成日报内容 → 存储日报 → 发送邮件
   ```

---

## 4. 数据模型（简化版）

### 4.1 核心数据表

#### Users (用户表)
- id (UUID, Primary Key)
- email (String, Unique)
- password_hash (String)
- name (String, Optional)
- created_at (DateTime)

#### Companies (公司表)
- id (UUID, Primary Key)
- ticker (String, Unique) - 股票代码
- name (String) - 公司名称
- industry (String, Optional) - 行业
- created_at (DateTime)

#### UserCompanies (用户关注表)
- id (UUID, Primary Key)
- user_id (UUID, Foreign Key)
- company_id (UUID, Foreign Key)
- created_at (DateTime)
- Unique(user_id, company_id)

#### NewsArticles (新闻表)
- id (UUID, Primary Key)
- title (String)
- content (Text)
- summary (Text) - AI 生成的摘要
- source_url (String, Unique)
- source_name (String)
- published_at (DateTime)
- created_at (DateTime)

#### NewsCompanyMapping (新闻-公司关联表)
- id (UUID, Primary Key)
- news_id (UUID, Foreign Key)
- company_id (UUID, Foreign Key)

#### DailyDigests (日报表)
- id (UUID, Primary Key)
- user_id (UUID, Foreign Key)
- date (Date)
- content (JSON) - 日报完整内容
- sent_at (DateTime, Nullable)
- created_at (DateTime)
- Unique(user_id, date)

---

## 5. API 设计（MVP）

### 5.1 认证 API
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录

### 5.2 公司管理 API
- `GET /api/companies/search?q={query}` - 搜索公司
- `GET /api/user/companies` - 获取用户关注列表
- `POST /api/user/companies` - 添加关注公司
- `DELETE /api/user/companies/{company_id}` - 取消关注

### 5.3 日报 API（仅用于测试）
- `POST /api/digests/generate` - 手动生成日报（测试用）

**注意**: 日报仅通过邮件发送，不提供Web API查看接口

---

## 6. 部署方案

### 6.1 使用 AI Builder Space 部署

根据 MCP 中的 `get_deployment_guide`，使用 FastAPI 部署指南：

1. **准备部署文件**
   - `requirements.txt` - Python 依赖
   - 环境变量配置

2. **部署步骤**
   - 使用 AI Builder Space 的部署功能
   - 配置环境变量（数据库连接、API Keys 等）
   - 设置定时任务（Celery Beat）

### 6.2 环境变量配置

```env
# 数据库
DATABASE_URL=postgresql://user:pass@host/dbname
REDIS_URL=redis://host:port

# AI Builder API
AI_BUILDER_TOKEN=your_token_here
AI_BUILDER_API_URL=https://api.aibuilder.space/backend

# 邮件服务
SENDGRID_API_KEY=your_key_here
FROM_EMAIL=noreply@stockdaily.com

# JWT
JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256

# 应用配置
ENVIRONMENT=production
DEBUG=false
```

---



---

## 8. 成功指标

### MVP 验证指标
- 用户能够成功注册和登录
- 用户能够在Web平台添加/删除关注公司
- 系统能够自动收集新闻并生成日报
- 日报能够成功发送到用户邮箱

---

## 9. 技术风险

### 主要风险
- **AI API 调用失败**: 实现重试机制和错误处理
- **新闻数据源不稳定**: 使用 AI Builder Search API 的 Tavily 搜索
- **邮件发送失败**: 实现重试机制和日志记录

---

## 10. 未来扩展（非 MVP）

以下功能不在 MVP 范围内，可在后续版本添加：
- 用户偏好设置
- 日报格式自定义
- 新闻重要性评级
- 市场概览数据
- 历史搜索功能
- PDF 导出
- 移动端 App

---

**文档维护**: 本文档专注于 MVP 版本，后续功能将在验证 MVP 后规划
