# StockDaily Digest 前端

美股投资日报 - 每日新闻摘要平台前端

## 技术栈

- React 18 + TypeScript
- Vite (构建工具)
- Tailwind CSS (样式)
- React Router (路由)
- Axios (HTTP 客户端)

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

前端将在 http://localhost:3000 运行

### 3. 构建生产版本

```bash
npm run build
```

## 页面说明

- `/login` - 登录页面
- `/register` - 注册页面
- `/dashboard` - 主页面（管理关注公司列表）

## API 接口

前端会调用后端 API：

- `POST /api/auth/login` - 用户登录
- `POST /api/auth/register` - 用户注册
- `GET /api/companies/search?q={query}` - 搜索公司
- `GET /api/user/companies` - 获取关注列表
- `POST /api/user/companies` - 添加关注公司
- `DELETE /api/user/companies/{id}` - 删除关注公司

## 目录结构

```
frontend/
├── public/
│   └── vite.svg
├── src/
│   ├── api/
│   │   └── index.ts          # API 客户端配置
│   ├── components/
│   │   ├── Navbar.tsx        # 导航栏
│   │   └── CompanyCard.tsx   # 公司卡片组件
│   ├── context/
│   │   └── AuthContext.tsx   # 认证上下文
│   ├── pages/
│   │   ├── Login.tsx         # 登录页
│   │   ├── Register.tsx      # 注册页
│   │   └── Dashboard.tsx     # 主页面
│   ├── App.tsx               # 应用入口
│   ├── main.tsx              # React 入口
│   └── index.css             # 全局样式
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```
