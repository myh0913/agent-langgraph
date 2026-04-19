# 知识库模块文档

## 概述

知识库模块为 Agent 提供 RAG（检索增强生成）能力，支持语义搜索和自动知识检索。

## 架构

```
知识库模块
├── knowledge/
│   ├── __init__.py          # 模块入口，统一导出
│   ├── config.py            # 配置（ChromaDB、Embedding、分块参数）
│   ├── chunker.py           # 文本分块器
│   ├── embedder.py          # 本地向量模型（all-MiniLM-L6-v2）
│   ├── chroma_client.py     # ChromaDB 客户端封装
│   ├── manager.py           # 核心管理器（统一接口）
│   ├── importers.py         # 导入器（文件/文本/API/记住指令）
│   └── chroma/              # ChromaDB 持久化数据
│
├── api/
│   └── knowledge_routes.py  # HTTP API 接口
│
└── scripts/
    ├── init_knowledge.py     # 初始化脚本
    ├── import_knowledge.py   # 命令行导入工具
    └── test_search.py        # 命令行搜索工具
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

需要安装：`chromadb`, `sentence-transformers`, `torch`

### 2. 初始化知识库

```bash
python scripts/init_knowledge.py
```

首次运行会下载向量模型（约 400MB）。

### 3. 启动服务

```bash
python main.py
```

服务地址：http://localhost:8008

---

## API 接口

所有接口前缀：`/api/ai/knowledge`

### 导入知识

#### 1. 导入文本

```bash
curl -X POST http://localhost:8008/api/ai/knowledge/import/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "基金投资需要注意以下几点：1. 不要追涨杀跌...",
    "title": "基金投资指南",
    "category": "投资理财",
    "tags": ["基金", "投资"]
  }'
```

**响应示例：**
```json
{
  "success": true,
  "total_chunks": 3,
  "indexed": 3,
  "failed": 0
}
```

#### 2. 上传文件

支持 `.md`、`.txt`、`.json` 文件：

```bash
curl -X POST http://localhost:8008/api/ai/knowledge/import/file \
  -F "file=@./guide.md" \
  -F "category=投资理财" \
  -F "tags=基金,股票"
```

#### 3. 接口抓取导入

从外部 API 获取内容并导入知识库：

```bash
curl -X POST http://localhost:8008/api/ai/knowledge/import/fetch \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.example.com/article/1",
    "method": "GET",
    "category": "文章",
    "tags": ["科技"],
    "json_key": "data.content"
  }'
```

**参数说明：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `url` | string | 接口地址（必填） |
| `method` | string | GET 或 POST（默认 GET） |
| `params` | object | GET 参数或 POST body |
| `headers` | object | 请求头 |
| `category` | string | 知识分类 |
| `tags` | array | 知识标签 |
| `title` | string | 知识标题（可从返回中提取） |
| `json_key` | string | 从响应 JSON 中提取 content 的路径，如 `"data.content"` |

#### 4. 批量导入目录

```bash
curl -X POST "http://localhost:8008/api/ai/knowledge/import/batch?dir_path=./knowledge/sources&category=投资理财&recursive=true"
```

### 查询知识

#### 5. 搜索

```bash
curl "http://localhost:8008/api/ai/knowledge/search?query=如何选择基金&top_k=5&category=投资理财"
```

**响应示例：**
```json
{
  "total": 2,
  "query": "如何选择基金",
  "results": [
    {
      "id": "chunk_投资_basdf123",
      "content": "选择基金时应该考虑以下几点...",
      "title": "基金投资指南",
      "category": "投资理财",
      "tags": ["基金", "投资"],
      "score": 0.8542,
      "source": "E:\\my project\\temp-agent\\knowledge\\sources\\投资指南.md"
    }
  ]
}
```

### 管理知识

#### 6. 知识库统计

```bash
curl http://localhost:8008/api/ai/knowledge/stats
```

**响应示例：**
```json
{
  "total_chunks": 15,
  "collection": "temp_agent_knowledge",
  "persist_dir": "E:\\my project\\temp-agent\\knowledge\\chroma",
  "config": {
    "chunk_size": 500,
    "embedding_model": "all-MiniLM-L6-v2",
    "embedding_dim": 384
  }
}
```

#### 7. 删除知识块

```bash
curl -X DELETE http://localhost:8008/api/ai/knowledge/chunk/chunk_投资_basdf123
```

#### 8. 清空知识库

```bash
# 清空全部
curl -X DELETE http://localhost:8008/api/ai/knowledge/clear

# 按分类删除
curl -X DELETE "http://localhost:8008/api/ai/knowledge/clear?category=投资理财"
```

### 记忆功能（对话中触发）

#### 9. 记住内容

当 Agent 检测到用户说"记住xxx"时自动调用：

```bash
curl -X POST http://localhost:8008/api/ai/knowledge/remember \
  -H "Content-Type: application/json" \
  -d '{"content": "用户偏好晚上9点后下单"}'
```

#### 10. 检测记住指令

自动检测用户消息是否包含"记住"指令：

```bash
curl -X POST http://localhost:8008/api/ai/knowledge/remember/detect \
  -H "Content-Type: application/json" \
  -d '{"user_message": "记住我喜欢低风险的投资产品"}'
```

**响应示例：**
```json
{
  "matched": true,
  "remembered": true,
  "content": "用户偏好晚上9点后下单",
  "chunks_created": 1
}
```

---

## Agent 集成（自动使用知识库）

当用户发送消息给 Agent 时，流程如下：

```
用户消息
    ↓
意图分类（BUSINESS/GENERAL/CONFIRM）
    ↓
BUSINESS 时：
    ↓
Step 1: 查知识库（ChromaDB ANN 搜索，top_k=3）
    ↓
Step 2: 将知识库内容注入 LLM prompt
    ↓
Step 3: LLM 决策：
    ├─ 知识库能答 → 直接回答（标记"📚 基于知识库回答"）
    ├─ 需要 API   → 调用后端（标记"📊 基于后端API数据"）
    └─ 意图不清   → 询问确认
    ↓
返回响应
```

### 自动使用场景

Agent 会自动检索知识库的场景包括：
- 用户问"怎么选基金"
- 用户问"什么是价值投资"
- 用户问产品相关问题

### 来源标记

| 来源 | 响应前缀 |
|------|---------|
| 知识库 | `📚 基于知识库回答（相关度: 0.85）` |
| 后端API | `📊 基于后端API数据` |
| LLM发挥 | 无标记 |

---

## 配置

在 `knowledge/config.py` 中修改：

```python
# ChromaDB 配置
CHROMA_PERSIST_DIR = "knowledge/chroma"      # 数据存储目录
CHROMA_COLLECTION = "temp_agent_knowledge"   # Collection 名称

# Embedding 模型配置
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"    # 模型名称
EMBEDDING_DEVICE = "cpu"                     # cpu 或 cuda
EMBEDDING_DIM = 384                          # 向量维度

# 分块配置
CHUNK_SIZE = 500      # 每块目标字数
CHUNK_OVERLAP = 50    # 块之间重叠字数

# 检索配置
SEARCH_TOP_K = 5                          # 默认返回条数
SEARCH_SCORE_THRESHOLD = 0.7              # 最低相似度阈值
```

---

## 命令行工具

### 初始化

```bash
python scripts/init_knowledge.py
```

### 导入知识

```bash
# 导入单个文件
python scripts/import_knowledge.py --file ./knowledge/sources/xxx.md --category 投资理财 --tags 基金 --tags 股票

# 批量导入目录
python scripts/import_knowledge.py --dir ./knowledge/sources --category 投资理财 --tags 基金 --recursive

# 直接导入文本
python scripts/import_knowledge.py --text "基金投资需要注意..." --title "基金投资指南" --category 投资理财
```

### 测试搜索

```bash
python scripts/test_search.py --query "如何选择基金" --top 5
```

---

## 代码调用

### Python API

```python
from knowledge import get_knowledge_manager, get_file_importer, get_text_importer, get_api_importer

# 获取管理器
manager = get_knowledge_manager()

# 导入文件
result = manager.import_file("./knowledge/sources/guide.md", category="投资理财", tags=["基金"])

# 导入文本
result = manager.import_text("基金投资需要注意...", title="基金投资指南", category="投资理财")

# 搜索
results = manager.search("如何选择基金", top_k=5)

# 查看统计
stats = manager.get_stats()

# 删除
manager.delete("chunk_xxx")

# 重建索引
manager.rebuild_index()
```

---

## 流程图

```
                    ┌─────────────────┐
                    │   用户消息      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   意图分类      │
                    │  BUSINESS ?      │
                    └────────┬────────┘
                             │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             │             ▼
        YES                  │           NO
              │             │             │
    ┌─────────▼─────────┐   │   ┌─────────▼─────────┐
    │   查知识库        │   │   │   GENERAL/CONFIRM │
    │  (ChromaDB ANN)   │   │   │   原有处理流程     │
    └─────────┬─────────┘   │   └───────────────────┘
              │             │
    ┌─────────▼─────────┐   │
    │   注入 LLM prompt │   │
    │   知识库内容      │   │
    └─────────┬─────────┘   │
              │             │
    ┌─────────▼─────────┐   │
    │   LLM 决策        │   │
    ├───────────────────┤   │
    │ answer: 直接回答  │   │
    │ api_call: 调API   │   │
    │ confirm: 询问     │   │
    └───────────────────┘   │
              │             │
              └─────────────┘
```

---

## 注意事项

1. **首次运行**：会自动下载向量模型（~400MB），后续运行无需再次下载
2. **知识格式**：不需要固定格式，系统会自动分块处理
3. **向量模型**：使用 `all-MiniLM-L6-v2`，384维，CPU 友好
4. **持久化**：ChromaDB 使用 `PersistentClient`，数据存储在 `knowledge/chroma/`
5. **删除操作**：清空操作不可恢复，请谨慎使用 `DELETE /clear`