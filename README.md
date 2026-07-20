# 课程选课与推荐系统

面向高校课程选课场景的全栈系统，覆盖学生端、教务端、微信小程序端、后端服务和本地 RAG 推荐增强。

## 项目组成

```
ai-course-select-system/
├── packages/shared/          # 跨应用共享包 (@course-select/shared)
├── backend/                  # FastAPI Python 后端（支持 memory / MySQL 双存储）
├── admin-web/                # 教务端 Vue 3 SPA（端口 5174）
├── student-web/              # 学生端 Vue 3 SPA（端口 5173）
├── weixin/                   # 微信小程序端（TypeScript）
├── scripts/                  # 开发与测试脚本
├── openapi/                  # OpenAPI 规范
├── storage/rag/              # RAG 索引与缓存
├── scripts/                  # 开发、测试与构建脚本
├── dream_query2.py           # 梦境查询辅助脚本
└── package.json              # 根工作区配置（npm workspaces）
```

## 主要能力

### 学生端
- 浏览课程目录，支持搜索、筛选、时间匹配
- 选课、退课、候补队列管理
- 周课表可视化
- AI 课程推荐（DeepSeek + 可选本地 RAG）
- 个人审计日志查看

### 教务端
- 课程管理：创建、编辑、扩容、调课、停课
- 课程操作审批工作流
- 例外审批（豁免规则）
- 候补队列重算
- 审计日志查询与导出

### 微信小程序
- 学生和教务门户的移动原生版本
- 微信登录集成
- 与 Web 端功能对齐

### 后端服务
- 双存储模式：内存（开发）/ MySQL（生产）
- JWT 认证与角色权限控制
- 三级推荐：确定性降级 → DeepSeek LLM → 本地 RAG
- 统一审计留痕
- OpenAPI 规范自动生成

## 技术栈

| 层 | 技术 |
|---|---|
| 共享包 | TypeScript |
| 学生端 | Vue 3 + Vite + Element Plus + Vue Router |
| 管理端 | Vue 3 + Vite + Element Plus + Vue Router |
| 后端 | FastAPI + SQLAlchemy + Pydantic |
| 微信小程序 | TypeScript + 微信框架 |
| 推荐系统 | DeepSeek API + LlamaIndex + HuggingFace |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+（可选，用于生产模式）
- 微信开发者工具（可选，用于小程序开发）

### 1. 安装前端依赖

```powershell
# 在项目根目录安装所有前端依赖（npm workspaces）
npm install
```

### 2. 启动后端

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

后端启动后访问 http://localhost:8000/docs 查看 API 文档。

### 3. 启动前端

```powershell
# 并行启动学生端和管理端
npm run dev
```

- 学生端：http://localhost:5173
- 管理端：http://localhost:5174

### 4. 打开微信小程序

用微信开发者工具打开 `weixin/miniprogram` 目录。

### 5. 运行测试

```powershell
# 后端测试
cd backend
pytest

# 前端测试（学生端 + 管理端）
npm run test

# 开发配置测试
npm run test:dev-config
```

## 项目架构

### 共享包 (`packages/shared`)

提供跨应用共享的 TypeScript 工具：

- `api-envelope.ts` - 统一 API 响应解析，兼容内存模式和数据库模式
- `course-time.ts` - 课程时间常量和工具函数
- `idempotency.ts` - 请求幂等键生成

### 后端架构

```
backend/app/
├── main.py              # FastAPI 应用入口
├── config.py            # 配置管理
├── auth.py              # JWT 认证
├── contracts.py         # Pydantic 契约
├── storage.py           # 条件 DB 依赖
├── store.py             # 内存存储
├── utils.py             # 共享工具函数
├── domain/              # 纯领域逻辑（规则引擎）
├── models/              # SQLAlchemy ORM 模型
├── ports/               # 抽象接口定义
├── schemas/             # Pydantic 模式
├── services/            # 业务逻辑层
├── routers/             # API 路由处理器
├── integrations/        # 外部服务适配器（DeepSeek、RAG）
└── tasks/               # 后台任务（候补队列重算）
```

**双存储模式**：通过 `get_optional_db()` 依赖，所有路由同时支持内存模式和 MySQL 模式。内存模式用于开发和测试，MySQL 模式用于生产环境。

### 前端架构

**学生端**：标准 Vue 3 SPA，使用 Vue Router 进行页面导航，提供完整的选课、推荐、课表功能。

**管理端**：Vue 3 SPA，使用 Vue Router 进行页面导航，提供课程管理、审批中心、审计日志、重算记录四个主要视图。

**共享代码**：通过 `@course-select/shared` 包共享 API 响应解析、课程时间逻辑等核心工具。

### 开发脚本 (`scripts/`)

| 脚本 | 说明 |
|---|---|
| `dev.mjs` | 并行启动学生端和管理端 Vite 开发服务器 |
| `dev-config.mjs` | 开发服务器配置生成（端口、环境变量） |
| `dev-config.test.mjs` | 开发配置单元测试 |
| `test.mjs` | 运行所有前端测试（dev-config + student-web + admin-web） |
| `generate-openapi.mjs` | 从 FastAPI 生成 OpenAPI 规范到 `openapi/` 目录 |

## 配置

### 环境变量

复制 `.env.example` 为 `.env` 并配置：

```env
# 存储模式：memory（开发）或 mysql（生产）
APP_STORAGE=memory

# MySQL 配置（仅 mysql 模式需要）
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/course_selection

# JWT 配置
JWT_SECRET=your-secret-key
JWT_EXPIRE_MINUTES=60

# DeepSeek API（可选）
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_MODEL=deepseek-chat

# RAG 配置（可选）
RAG_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
RAG_INDEX_DIR=./storage/rag
```

## 开发指南

### 添加新 API 端点

1. 在 `backend/app/contracts.py` 中定义请求/响应模型
2. 在 `backend/app/routers/` 中添加路由处理器
3. 在 `backend/app/services/` 中实现业务逻辑
4. 添加测试到 `backend/tests/`

### 添加新前端页面

1. 在 `src/views/` 中创建视图组件（如 `src/views/NewView.vue`）
2. 在 `src/router/index.js` 中添加路由配置
3. 在 `src/api/` 中添加 API 调用函数（如 `src/api/student.js`）
4. 若为学生端，可在 `src/components/` 中添加可复用组件

### 运行 OpenAPI 规范生成

```powershell
npm run generate-openapi
```

### 开发服务器配置

开发服务器支持以下环境变量自定义：

```powershell
# 自定义端口
$env:STUDENT_WEB_PORT = "5173"
$env:ADMIN_WEB_PORT = "5174"

# 自定义主机
$env:DEV_HOST = "0.0.0.0"

# 启动并自动检测就绪状态（smoke test）
npm run dev:smoke
```

## 测试

### 后端测试

```powershell
cd backend
pytest                          # 运行所有测试
pytest tests/test_auth.py       # 运行特定测试文件
pytest -v                       # 详细输出
```

### 前端测试

```powershell
# 运行所有前端测试（推荐）
npm run test

# 或单独运行
cd student-web && npm test      # 学生端（vitest）
cd admin-web && npm test        # 管理端（node:test）

# 开发配置测试
npm run test:dev-config
```

## 部署

### 后端部署

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 前端构建

```powershell
# 构建学生端和管理端
npm run build
```

构建产物位于各前端的 `dist/` 目录。

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。
