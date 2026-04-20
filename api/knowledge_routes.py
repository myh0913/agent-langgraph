"""
知识库 API 接口
提供 HTTP 接口用于导入和搜索知识
统一使用 ApiResponse 封装
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
from api.response import ApiResponse
import logging

logger = logging.getLogger(__name__)

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
    json_key: Optional[str] = None


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
    return ApiResponse.success(data=result)


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
    logger.info(f"接收到文件上传: {file.filename}, 大小: {getattr(file, 'size', 'unknown')}")
    
    # 验证文件类型
    allowed_exts = {".md", ".txt", ".json"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_exts:
        return ApiResponse.error(
            message=f"不支持的文件类型: {ext}，支持的类型: {allowed_exts}",
            code=400
        )

    # 保存临时文件
    temp_dir = Path("knowledge/sources")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / file.filename

    try:
        # 读取文件内容
        content = await file.read()
        logger.info(f"文件大小: {len(content)} bytes")
        
        if not content:
            return ApiResponse.error(message="文件内容为空", code=400)
        
        # 写入临时文件
        with temp_path.open("wb") as f:
            f.write(content)
        
        logger.info(f"文件已保存到: {temp_path}")

        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        importer = get_file_importer()
        result = importer.import_file(
            file_path=str(temp_path),
            category=category,
            tags=tag_list
        )
        return ApiResponse.success(data=result)

    except Exception as e:
        return ApiResponse.error(message=f"导入失败: {str(e)}", code=500)

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
    try:
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
        return ApiResponse.success(data=result)
    except Exception as e:
        return ApiResponse.error(message=f"抓取导入失败: {str(e)}", code=500)


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
    try:
        importer = get_file_importer()
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        result = importer.import_batch(
            dir_path=dir_path,
            category=category,
            tags=tag_list,
            recursive=recursive
        )
        return ApiResponse.success(data=result)
    except Exception as e:
        return ApiResponse.error(message=f"批量导入失败: {str(e)}", code=500)


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
    try:
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

        return ApiResponse.success(data={
            "total": len(results),
            "query": query,
            "results": results
        })
    except Exception as e:
        return ApiResponse.error(message=f"搜索失败: {str(e)}", code=500)


@router.get("/stats")
async def stats():
    """
    获取知识库统计信息

    用法：
    ```bash
    curl http://localhost:8008/api/ai/knowledge/stats
    ```
    """
    try:
        manager = get_knowledge_manager()
        stats_data = manager.get_stats()
        return ApiResponse.success(data=stats_data)
    except Exception as e:
        return ApiResponse.error(message=f"获取统计失败: {str(e)}", code=500)


@router.get("/chunk/{chunk_id}")
async def get_chunk(chunk_id: str):
    """
    获取单条知识详情

    用法：
    ```bash
    curl http://localhost:8008/api/ai/knowledge/chunk/chunk_xxx
    ```
    """
    # 注：ChromaDB 不支持按 ID 查询，此接口暂不支持
    return ApiResponse.error(
        message="ChromaDB 不支持按 ID 查询，请使用 /search 接口搜索",
        code=501
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
    try:
        manager = get_knowledge_manager()
        success = manager.delete(chunk_id)
        return ApiResponse.success(data={
            "success": success,
            "chunk_id": chunk_id
        })
    except Exception as e:
        return ApiResponse.error(message=f"删除失败: {str(e)}", code=500)


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
    try:
        manager = get_knowledge_manager()

        if category or tags:
            # 条件删除
            tag_list = [t.strip() for t in tags.split(",")] if tags else None
            count = manager.delete_by_filter(category=category, tags=tag_list)
            return ApiResponse.success(data={
                "success": True,
                "deleted": count,
                "mode": "filtered"
            })
        else:
            # 清空全部
            manager.rebuild_index()
            return ApiResponse.success(data={
                "success": True,
                "mode": "full_clear"
            })
    except Exception as e:
        return ApiResponse.error(message=f"清空失败: {str(e)}", code=500)


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
    try:
        importer = get_text_importer()
        result = importer.import_text(
            text=req.content,
            title="用户记忆",
            category=req.category,
            tags=req.tags
        )
        return ApiResponse.success(data={
            "success": result.get("success", False),
            "content": req.content,
            "result": result
        })
    except Exception as e:
        return ApiResponse.error(message=f"记忆失败: {str(e)}", code=500)


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
    try:
        handler = get_remember_handler()
        result = handler.handle(user_message)

        if not result["matched"]:
            return ApiResponse.success(data={
                "matched": False,
                "message": "未检测到记住指令"
            })

        if result["result"] and result["result"].get("success"):
            return ApiResponse.success(data={
                "matched": True,
                "remembered": True,
                "content": result["content"][:100] + ("..." if len(result["content"]) > 100 else ""),
                "chunks_created": result["result"].get("total_chunks", 0)
            })
        else:
            return ApiResponse.success(data={
                "matched": True,
                "remembered": False,
                "error": result["result"].get("error", "导入失败")
            })
    except Exception as e:
        return ApiResponse.error(message=f"检测失败: {str(e)}", code=500)