# MCP 工具使用指南

## 什么是 MCP？

MCP (Model Context Protocol) 是一个协议，允许 AI 助手访问外部工具和服务。在 Cursor IDE 中，MCP 工具可以直接被 AI 助手调用，帮助你完成各种任务。

## 已安装的 MCP 服务器

### 1. user-ai-builders-coach

这个 MCP 服务器提供了 AI Builder 平台相关的工具，帮助你了解和使用 AI Builder API。

#### 可用工具：

1. **get_api_specification**
   - 功能：获取 OpenAPI 规范文档
   - 用途：查看 API 端点的详细说明
   - 调用方式：在 Cursor 中直接询问 AI "获取 API 规范"

2. **get_auth_token**
   - 功能：获取 AI_BUILDER_TOKEN（默认会掩码显示）
   - 参数：`masked` (boolean, 默认 true)
   - 用途：查看你的认证令牌（用于 API 调用）

3. **get_deployment_guide**
   - 功能：获取部署指南（带缓存）
   - 参数：`service_type` (string, 默认 "fastapi")
   - 用途：获取特定服务类型的部署指导

4. **explain_authentication_model**
   - 功能：解释认证模型
   - 用途：了解共享部署和开发使用的认证机制

### 2. cursor-ide-browser

这个 MCP 服务器提供了浏览器自动化工具，可以用于测试网页应用和前端开发。

#### 可用工具：

1. **browser_navigate** - 导航到指定 URL
2. **browser_snapshot** - 捕获当前页面的可访问性快照（比截图更好）
3. **browser_click** - 点击页面元素
4. **browser_type** - 在输入框中输入文本
5. **browser_hover** - 悬停在元素上
6. **browser_press_key** - 按下键盘按键
7. **browser_select_option** - 选择下拉选项
8. **browser_wait_for** - 等待特定条件
9. **browser_navigate_back** - 返回上一页
10. **browser_resize** - 调整浏览器窗口大小
11. **browser_console_messages** - 获取控制台消息
12. **browser_network_requests** - 获取网络请求信息

## 如何使用 MCP 工具

### 方法 1：通过 Cursor AI 助手直接调用

在 Cursor 中，你可以直接向 AI 助手提问，它会自动调用相应的 MCP 工具：

**示例：**
- "获取 API 规范文档"
- "显示我的认证令牌"
- "获取 FastAPI 部署指南"
- "打开 http://localhost:8000 并截图"
- "测试我的 FastAPI 应用的 /api/chat 端点"

### 方法 2：在代码中集成（高级用法）

虽然 MCP 工具主要是为 AI 助手设计的，但你也可以在代码中通过 HTTP 请求调用这些功能。不过，更常见的做法是：

1. **使用 AI Builder API 工具**：直接在你的 FastAPI 应用中调用 AI Builder API（就像我们已经做的）
2. **使用浏览器自动化库**：对于浏览器功能，可以使用 Selenium 或 Playwright

## 实际应用示例

### 示例 1：获取 API 规范

在 Cursor 中询问：
```
"请获取 AI Builder API 的完整规范"
```

AI 会自动调用 `get_api_specification` 工具并返回结果。

### 示例 2：测试你的 FastAPI 应用

在 Cursor 中询问：
```
"打开 http://localhost:8000/docs 并截图，然后测试 /api/chat 端点"
```

AI 会使用浏览器工具：
1. 导航到你的 Swagger UI
2. 截图查看页面
3. 可能还会帮你测试 API

### 示例 3：获取部署帮助

在 Cursor 中询问：
```
"我需要部署这个 FastAPI 应用，请获取部署指南"
```

AI 会调用 `get_deployment_guide` 工具并为你提供详细的部署步骤。

## 注意事项

1. **MCP 工具主要在 Cursor IDE 中使用**：这些工具是为了增强 AI 助手的能力，而不是直接在代码中调用的库。

2. **浏览器工具需要应用运行**：使用 `cursor-ide-browser` 测试你的应用时，确保应用正在运行（`uvicorn main:app --reload`）。

3. **认证令牌安全**：`get_auth_token` 默认会掩码显示，保护你的敏感信息。

## 下一步

现在你可以：
1. 在 Cursor 中直接询问 AI 使用这些工具
2. 测试你的 FastAPI 应用（使用浏览器工具）
3. 获取部署帮助（使用 AI Builder Coach 工具）
4. 查看 API 文档（使用 API 规范工具）

试试在 Cursor 中问："请帮我测试一下我的 FastAPI 应用的 /api/chat 端点"

