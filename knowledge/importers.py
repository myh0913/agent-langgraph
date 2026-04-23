"""
知识导入器
支持：文件、文本、URL、API 回调
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import httpx

from .config import knowledge_settings
from .manager import get_knowledge_manager

logger = logging.getLogger(__name__)


class FileImporter:
    """文件导入器（支持 md/txt/json）"""

    def __init__(self):
        self.manager = get_knowledge_manager()
        self.supported_exts = {".md", ".txt", ".json"}

    def import_file(
        self,
        file_path: str,
        category: str = "",
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        导入单个文件

        Args:
            file_path: 文件路径
            category: 分类
            tags: 标签列表

        Returns:
            Dict: 导入结果
        """
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": "文件不存在"}

        ext = path.suffix.lower()
        if ext not in self.supported_exts:
            return {"success": False, "error": f"不支持的文件类型: {ext}"}

        return self.manager.import_file(
            file_path=str(path),
            category=category,
            tags=tags or []
        )

    def import_batch(
        self,
        dir_path: str,
        category: str = "",
        tags: List[str] = None,
        recursive: bool = True
    ) -> Dict[str, Any]:
        """
        批量导入目录

        Args:
            dir_path: 目录路径
            category: 默认分类
            tags: 默认标签
            recursive: 是否递归子目录

        Returns:
            Dict: 导入结果统计
        """
        return self.manager.import_directory(
            dir_path=dir_path,
            category=category,
            tags=tags or [],
            recursive=recursive
        )


class TextImporter:
    """文本导入器（直接传入文本内容）"""

    def __init__(self):
        self.manager = get_knowledge_manager()

    def import_text(
        self,
        text: str,
        title: str = "",
        category: str = "",
        tags: List[str] = None,
        source: str = "manual"
    ) -> Dict[str, Any]:
        """
        导入纯文本

        Args:
            text: 文本内容
            title: 标题
            category: 分类
            tags: 标签列表
            source: 来源标识

        Returns:
            Dict: 导入结果
        """
        if not text or not text.strip():
            return {"success": False, "error": "文本内容为空"}

        return self.manager.import_text(
            text=text,
            title=title or "手动导入",
            category=category,
            tags=tags or [],
            source=source
        )


class ApiImporter:
    """API 导入器（请求接口获取内容并导入）"""

    def __init__(self):
        self.manager = get_knowledge_manager()
        self.http_client = httpx.Client(timeout=30.0)

    def fetch_and_import(
        self,
        url: str,
        method: str = "GET",
        params: Dict = None,
        headers: Dict = None,
        category: str = "",
        tags: List[str] = None,
        title: str = "",
        json_key: str = None
    ) -> Dict[str, Any]:
        """
        请求接口并导入内容

        Args:
            url: 接口地址
            method: GET/POST
            params: URL 参数(GET) 或 body(POST)
            headers: 请求头
            category: 知识分类
            tags: 知识标签
            title: 知识标题（可从返回中提取）
            json_key: 从响应 JSON 中提取 content 的 key，如 "data.content"

        Returns:
            Dict: 导入结果
        """
        try:
            # 请求接口
            if method.upper() == "GET":
                resp = self.http_client.get(url, params=params or {}, headers=headers or {})
            else:
                resp = self.http_client.post(url, json=params or {}, headers=headers or {})

            resp.raise_for_status()
            result = resp.json()

            # 提取文本内容
            text = self._extract_content(result, json_key)
            if not text:
                return {"success": False, "error": "接口返回内容为空或无法解析"}

            # 如果没指定 title，尝试从返回中提取
            if not title:
                title = self._extract_title(result)

            # 导入知识库
            import_result = self.manager.import_text(
                text=text,
                title=title or "API导入",
                category=category,
                tags=tags or [],
                source=f"api:{url}"
            )

            import_result["api_url"] = url
            return import_result

        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP 错误: {e.response.status_code}"}
        except Exception as e:
            return {"success": False, "error": f"请求失败: {str(e)}"}

    def _extract_content(self, result: dict, json_key: str = None) -> str:
        """从响应中提取文本内容"""
        if json_key:
            keys = json_key.split(".")
            current = result
            for k in keys:
                if isinstance(current, dict):
                    current = current.get(k)
                else:
                    return ""
            return str(current) if current else ""

        # 默认：尝试常见字段
        for key in ["content", "text", "description", "data"]:
            if isinstance(result, dict) and key in result:
                value = result[key]
                if isinstance(value, str):
                    return value
                if isinstance(value, dict):
                    return str(value)

        return str(result)

    def _extract_title(self, result: dict) -> str:
        """从响应中提取标题"""
        for key in ["title", "name", "subject"]:
            if key in result:
                return str(result[key])
        return ""

    def close(self):
        """关闭 HTTP 客户端"""
        self.http_client.close()


# ============ "记住"指令处理器 ============

class RememberHandler:
    """记住指令处理器 - 处理用户说"记住xxx"的场景"""

    def __init__(self):
        self.manager = get_knowledge_manager()
        # 按优先级排列：冒号分隔优先，然后空格分隔，最后无分隔
        self._patterns = [
            # 记住：xxx / 记住xxx
            r"记住[：:]?\s*(.+)",
            r"记住(.+)",
            # 请记住：xxx / 请记住xxx
            r"请记住[：:]?\s*(.+)",
            r"请记住(.+)",
            # 帮我记住：xxx / 帮我记住xxx
            r"帮我记住[：:]?\s*(.+)",
            r"帮我记住(.+)",
            # 记一下xxx / 记一下：xxx
            r"记一下[：:]?\s*(.+)",
            r"记一下(.+)",
            # 记下来xxx / 记下来：xxx / 把这个记下来xxx
            r"记下来[：:]?\s*(.+)",
            r"记下来(.+)",
            r"把这个记下来[：:]?\s*(.+)",
            r"把这个记下来(.+)",
        ]

    def handle(self, user_message: str) -> Optional[Dict[str, Any]]:
        """
        处理"记住"指令

        Args:
            user_message: 用户消息

        Returns:
            Dict: {"matched": bool, "content": str, "result": dict}
            matched=True 表示触发了记住逻辑
        """
        content = self._extract_remember_content(user_message)
        if not content:
            return {"matched": False, "content": None, "result": None}

        result = self.manager.import_text(
            text=content,
            title="用户记忆",
            category="memory",
            tags=["用户主动记忆"]
        )

        return {
            "matched": True,
            "content": content,
            "result": result
        }

    def _extract_remember_content(self, message: str) -> Optional[str]:
        """从消息中提取要记住的内容"""
        import re

        for pattern in self._patterns:
            match = re.search(pattern, message)
            if match:
                content = match.group(1).strip()
                if content:
                    return content
        return None

    def is_remember_command(self, message: str) -> bool:
        """检查是否是记住指令"""
        return self._extract_remember_content(message) is not None


# ============ 全局实例 ============

_file_importer = None
_text_importer = None
_api_importer = None
_remember_handler = None


def get_file_importer() -> FileImporter:
    global _file_importer
    if _file_importer is None:
        _file_importer = FileImporter()
    return _file_importer


def get_text_importer() -> TextImporter:
    global _text_importer
    if _text_importer is None:
        _text_importer = TextImporter()
    return _text_importer


def get_api_importer() -> ApiImporter:
    global _api_importer
    if _api_importer is None:
        _api_importer = ApiImporter()
    return _api_importer


def get_remember_handler() -> RememberHandler:
    global _remember_handler
    if _remember_handler is None:
        _remember_handler = RememberHandler()
    return _remember_handler