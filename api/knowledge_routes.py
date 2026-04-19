"""
知识库 API 接口
提供 HTTP 接口用于导入和搜索知识
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import shutil
from pathlib import Path

from knowledge.importers import (
    get_file_importer,
    get_text_importer,
    get_api_importer,
    get_remember_handler
)
from knowledge.manager import get_knowledge_manager

router = APIRouter(prefix="/knowledge", tags=["知识库"])

# ============ 请求模型 ============


class TextImportRequest(BaseModel):
    """文本导入请求"""
    text: str
    title: Optional[str] = ""
    category: Optional[str] = ""
    tags: Optional[List[str]] = []


class ApiFetchRequest(BaseModel):
    """API 抓取导入请求"""
    url: str
    method: str = "GET"
    params: Optional[dict] = None
    headers: Optional[dict] = None
    category: Optional[str] = ""
    tags: Optional[List[str]] = []
    title: Optional[str] = ""
    json_key: Optional[str] = None  # 如 "data.content"


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str
    top_k: int = 5
    category: Optional[str] = None
    tags: Optional[List[str]] = None


# ============ 导入接口 ============


@router.post("/import/text")
async def import_text(req: TextImportRequest):
    """
    导入文本内容

    用法：
    ```bash
    curl -X POST http://localhost:8008/api/ai/knowledge/import/text \\
      -H "Content-Type: application/json" \\
      -d '{
        "text": "基金投资需要注意以下几点...",
        "title": "基金投资指南",
        "category": "投资理财",
        "tags": ["基金", "投资"]
      }'
    ```
    """
    importer = get_text_importer()
    result = importer.import_text(
        text=req.text,
        title=req.title,
        category=req.category,
        tags=req.tags or []
    )
    return result


@router.post("/import/file")
async def import_file(
    file: UploadFile = File(...),
    category: str = Form(""),
    tags: str = Form("")
):
    """
    上传文件导入（支持 md/txt/json）

    用法：
    ```bash
    curl -X POST http://localhost:8008/api/ai/knowledge/import/file \\
      -F "file=@./guide.md" \\
      -F "category=投资理财" \\
      -F "tags=基金,股票"
    ```
    """
    # 验证文件类型
    allowed_exts = {".md", ".txt", ".json"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，支持的类型: {allowed_exts}"
        )

    # 保存临时文件
    temp_dir = Path("knowledge/sources")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / file.filename

    try:
        with temp_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        # 解析 tags
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        importer = get_file_importer()
        result = importer.import_file(
            file_path=str(temp_path),
            category=category,
            tags=tag_list
        )
        return result

    finally:
        # 删除临时文件
        temp_path.unlink(missing_ok=True)


@router.post("/import/fetch")
async def fetch_and_import(req: ApiFetchRequest):
    """
    请求接口并导入内容

    用法：
    ```bash
    curl -X POST http://localhost:8008/api/ai/knowledge/import/fetch \\
      -H "Content-Type: application/json" \\
      -d '{
        "url": "https://api.example.com/article/1",
        "method": "GET",
        "category": "文章",
        "tags": ["科技"],
        "json_key": "data.content"
      }'
    ```
    """
    importer = get_api_importer()
    result = importer.fetch_and_import(
        url=req.url,
        method=req.method,
        params=req.params,
        headers=req.headers,
        category=req.category,
        tags=req.tags or [],
        title=req.title or "",
        json_key=req.json_key
    )
    return result


@router.post("/import/batch")
async def import_batch(
    dir_path: str,
    category: str = Form(""),
    tags: str = Form(""),
    recursive: bool = Form(True)
):
    """
    批量导入目录

    用法：
    ```bash
    curl -X POST "http://localhost:8008/api/ai/knowledge/import/batch?dir_path=./knowledge/sources&category=投资理财&recursive=true"
    ```
    """
    importer = get_file_importer()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    result = importer.import_batch(
        dir_path=dir_path,
        category=category,
        tags=tag_list,
        recursive=recursive
    )
    return result


# ============ 查询接口 ============


@router.get("/search")
async def search(
    query: str,
    top_k: int = 5,
    category: str = None,
    tags: str = None
):
    """
    搜索知识库

    用法：
    ```bash
    curl "http://localhost:8008/api/ai/knowledge/search?query=如何选择基金&top_k=5&category=投资理财"
    ```
    """
    manager = get_knowledge_manager()

    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    results = manager.search(
        query=query,
        top_k=top_k,
        category=category,
        tags=tag_list
    )

    return {
        "total": len(results),
        "query": query,
        "results": results
    }


@router.get("/stats")
async def stats():
    """
    获取知识库统计信息

    用法：
    ```bash
    curl http://localhost:8008/api/ai/knowledge/stats
    ```
    """
    manager = get_knowledge_manager()
    return manager.get_stats()


@router.get("/chunk/{chunk_id}")
async def get_chunk(chunk_id: str):
    """
    获取单条知识详情

    用法：
    ```bash
    curl http://localhost:8008/api/ai/knowledge/chunk/chunk_xxx
    ```
    """
    manager = get_knowledge_manager()
    results = manager.search(query="", top_k=1)
    # 注：ChromaDB 不支持按 ID 查询，此接口暂不支持
    raise HTTPException(
        status_code=501,
        detail="ChromaDB 不支持按 ID 查询，请使用 /search 接口搜索"
    )


@router.delete("/chunk/{chunk_id}")
async def delete_chunk(chunk_id: str):
    """
    删除知识块

    用法：
    ```bash
    curl -X DELETE http://localhost:8008/api/ai/knowledge/chunk/chunk_xxx
    ```
    """
    manager = get_knowledge_manager()
    success = manager.delete(chunk_id)
    return {"success": success, "chunk_id": chunk_id}


@router.delete("/clear")
async def clear_knowledge(category: str = None, tags: str = None):
    """
    清空知识库（慎用）

    用法：
    ```bash
    # 清空所有
    curl -X DELETE http://localhost:8008/api/ai/knowledge/clear

    # 按分类删除
    curl -X DELETE "http://localhost:8008/api/ai/knowledge/clear?category=投资理财"
    ```
    """
    manager = get_knowledge_manager()

    if category or tags:
        # 条件删除
        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        count = manager.delete_by_filter(category=category, tags=tag_list)
        return {"success": True, "deleted": count, "mode": "filtered"}
    else:
        # 清空全部
        manager.rebuild_index()
        return {"success": True, "mode": "full_clear"}


# ============ 记忆接口（对话中触发） ============


class RememberRequest(BaseModel):
    """记住指令请求（供 Agent 内部调用）"""
    content: str
    category: str = "memory"
    tags: List[str] = ["用户主动记忆"]


@router.post("/remember")
async def remember(req: RememberRequest):
    """
    记住内容（Agent 对话中触发）

    此接口供 Agent 内部使用，当检测到用户说"记住xxx"时调用

    用法：
    ```bash
    curl -X POST http://localhost:8008/api/ai/knowledge/remember \\
      -H "Content-Type: application/json" \\
      -d '{"content": "用户偏好晚上9点后下单"}'
    ```
    """
    importer = get_text_importer()
    result = importer.import_text(
        text=req.content,
        title="用户记忆",
        category=req.category,
        tags=req.tags
    )
    return {
        "success": result.get("success", False),
        "content": req.content,
        "result": result
    }


@router.post("/remember/detect")
async def detect_remember(user_message: str):
    """
    检测并处理记住指令

    此接口会自动检测用户消息是否包含"记住"指令，
    如果是则自动导入，不是则返回不匹配

    用法：
    ```bash
    curl -X POST http://localhost:8008/api/ai/knowledge/remember/detect \\
      -H "Content-Type: application/json" \\
      -d '{"user_message": "记住我喜欢低风险的投资产品"}'
    ```
    """
    handler = get_remember_handler()
    result = handler.handle(user_message)

    if not result["matched"]:
        return {
            "matched": False,
            "message": "未检测到记住指令"
        }

    if result["result"] and result["result"].get("success"):
        return {
            "matched": True,
            "remembered": True,
            "content": result["content"][:100] + ("..." if len(result["content"]) > 100 else ""),
            "chunks_created": result["result"].get("total_chunks", 0)
        }
    else:
        return {
            "matched": True,
            "remembered": False,
            "error": result["result"].get("error", "导入失败")
        }