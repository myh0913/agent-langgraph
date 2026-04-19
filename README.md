# FI-Agent - 基于 LangGraph 的 Agent 项目框架

本项目是一个模块化、可扩展的 Agent 框架，使用 LangGraph 作为核心编排引擎，支持多轮对话、意图分类、业务 API 调用、定时任务和 RAG 知识库检索。

## 功能特性

- ✅ **意图分类** - LLM 自动识别用户意图（BUSINESS / GENERAL / CONFIRM）
- ✅ **会话记忆** - Redis 持久化，支持多轮对话上下文和用户隔离
- ✅ **上下文压缩** - 基于 tiktoken token 计数，超过阈值自动 LLM 摘要压缩
- ✅ **并发处理** - ThreadPoolExecutor + 异步 FastAPI，支持高并发
- ✅ **定时任务** - APScheduler 支持 cron / interval / once 三种任务
- ✅ **后端 API 调用** - 业务意图由 LLM 规划 API 调用，httpx 请求后端，LLM 总结回复
- ✅ **知识库 RAG** - ChromaDB 语义搜索，自动注入知识到 LLM 上下文

## 技术栈

| 分类        | 技术                                                        |
| ----------- | ----------------------------------------------------------- |
| Agent 编排  | LangGraph                                                   |
| LLM 集成    | LangChain + langchain-openai（兼容 OpenAI/MiniMax/Qwen 等） |
| 会话存储    | Redis                                                       |
| 知识库      | ChromaDB（嵌入式）+ all-MiniLM-L6-v2 向量模型               |
| Web 框架    | FastAPI + Uvicorn                                           |
| 定时任务    | APScheduler                                                 |
| HTTP 客户端 | httpx                                                       |
| Token 计数  | tiktoken                                                    |

## 项目结构

```
temp-agent/
├── config/                 # 配置模块
│   ├── settings.py         # 配置类（从 env/.env 读取）
│   ├── prompts.py          # 提示词模板
│   ├── llm.py              # LLM 客户端封装（单例）
│   └── tool_registry.py    # 工具注册表
├── env/
│   └── .env                # 环境变量（API Key、Redis 等）
├── tools/                  # 工具实现
│   ├── base.py             # 工具基类 BaseToolNode
│   ├── intent_classifier.py # 意图分类
│   ├── business_handler.py  # 业务处理（含知识库检索）
│   └── intent_confirm.py    # 意图确认
├── graph/                  # LangGraph 定义
│   ├── agent.py            # Agent 图创建
│   ├── nodes.py            # 节点实现
│   └── edges.py            # 路由逻辑
├── knowledge/              # 知识库模块（RAG）
│   ├── config.py           # 知识库配置
│   ├── chunker.py          # 文本分块
│   ├── embedder.py         # 向量模型（all-MiniLM-L6-v2）
│   ├── chroma_client.py    # ChromaDB 客户端
│   ├── manager.py          # 核心管理器
│   ├── importers.py        # 导入器（文件/文本/API）
│   └── README.md           # 知识库详细文档
├── api/                    # API 路由
│   ├── routes.py           # 主 API 路由
│   ├── knowledge_routes.py # 知识库 API 路由
│   └── response.py         # 统一响应封装
├── memory/                 # 会话管理
│   ├── session.py          # Redis 会话存储
│   └── compression.py      # 上下文压缩
├── tasks/                  # 定时任务
│   └── scheduler.py        # APScheduler 调度器
├── scripts/                # 命令行工具
│   ├── init_knowledge.py  # 知识库初始化
│   ├── import_knowledge.py # 导入知识
│   └── test_search.py      # 测试搜索
├── main.py                 # 入口文件
├── test.html               # Web 测试页面
└── requirements.txt        # 依赖列表
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `env/.env` 文件：

```env
# LLM 配置
MODEL_API_KEY=your-api-key-here
MODEL_BASE_URL=https://api.minimaxi.com/v1
MODEL_NAME=MiniMax-M2.5

# Redis 配置
# REDIS_URL=redis://:fa@report@8.130.95.223:6380/0
REDIS_URL=redis://localhost:6380/0

# 服务器配置
API_HOST=0.0.0.0
API_PORT=8008

# 后端业务接口
BACKEND_API_HOST=http://8.130.95.223:8688
BACKEND_API_PREFIX=/api
```

### 3. 初始化知识库（首次）

```bash
python scripts/init_knowledge.py
```

会下载向量模型（约 400MB），后续无需重复。

### 4. 启动服务

```bash
python main.py
# 服务地址: http://localhost:8008
```

### 5. 打开测试页面

直接用浏览器打开 `test.html` 即可测试所有功能。

---

## API 接口

### 主 API（消息/会话）

```bash
# 发送消息
curl -X POST http://localhost:8008/api/ai/message \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "message": "如何选择基金"}'

# 获取会话历史
curl http://localhost:8008/api/ai/history/{user_id}/{session_id}

# 获取用户所有会话
curl http://localhost:8008/api/ai/sessions/{user_id}
```

### 知识库 API

```bash
# 导入文本
curl -X POST http://localhost:8008/api/ai/knowledge/import/text \
  -H "Content-Type: application/json" \
  -d '{"text": "基金投资指南内容...", "title": "基金投资", "category": "理财", "tags": ["基金"]}'

# 上传文件
curl -X POST http://localhost:8008/api/ai/knowledge/import/file \
  -F "file=@./guide.md" -F "category=投资理财"

# API 抓取导入
curl -X POST http://localhost:8008/api/ai/knowledge/import/fetch \
  -H "Content-Type: application/json" \
  -d '{"url": "https://api.example.com/content/1", "category": "文章"}'

# 搜索
curl "http://localhost:8008/api/ai/knowledge/search?query=如何选择基金"

# 统计
curl http://localhost:8008/api/ai/knowledge/stats
```

详见 `knowledge/README.md`

---

## Agent 工作流程

```
用户消息
    │
    ▼
┌─────────────────────────┐
│   intent_classifier     │  ← LLM 判断意图类型
└───────────┬─────────────┘
            │
    ┌───────┴──────┐
    │              │
    ▼              ▼
BUSINESS         GENERAL/CONFIRM
    │              │
    ▼              ▼
┌─────────────────────┐   ┌──────────────────┐
│  business_handler   │   │ intent_confirm    │
│  (含知识库检索)      │   │ LLM 追问/提供选项 │
└─────────┬───────────┘   └──────────────────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
知识库能答   需要API
    │           │
    ▼           ▼
直接回答   调用后端
```

**知识库自动检索**：当 Agent 判断为 BUSINESS 意图时，会自动：

1. 从 ChromaDB 检索相关知识（top_k=3）
2. 将知识内容注入 LLM prompt
3. LLM 决策：直接回答 / 调用 API / 询问确认
4. 响应带来源标记：`📚 基于知识库回答` 或 `📊 基于后端API数据`

---

## 配置说明

| 配置项     | 来源                  | 说明                                              |
| ---------- | --------------------- | ------------------------------------------------- |
| LLM 相关   | `env/.env`            | `MODEL_API_KEY` / `MODEL_BASE_URL` / `MODEL_NAME` |
| Redis      | `env/.env`            | `REDIS_URL`                                       |
| 后端接口   | `env/.env`            | `BACKEND_API_HOST` / `BACKEND_API_PREFIX`         |
| 上下文压缩 | `env/.env`            | `CONTEXT_TOKEN_LIMIT` / `COMPRESSION_KEEP_RECENT` |
| 知识库     | `knowledge/config.py` | ChromaDB / Embedding / 分块参数                   |

---

## 扩展开发

### 添加新工具

1. 继承 `BaseToolNode`，实现 `_run_impl` 方法
2. 在 `tools/__init__.py` 中 `registry.register_class("name", YourClass)`
3. 在 `graph/nodes.py` 中添加节点调用逻辑
4. 在 `graph/agent.py` 中将节点加入图并连接边

### 知识库配置

在 `knowledge/config.py` 中修改：

```python
CHUNK_SIZE = 500       # 每块目标字数
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"  # 向量模型
SEARCH_TOP_K = 5       # 默认返回条数
```

---

## 测试页面

打开 `test.html` 可用 Web 界面测试：

- 💬 对话
- 📚 知识库导入（文本/文件/API）
- 🔍 知识库搜索
- 📋 会话管理

---

## License

MIT
