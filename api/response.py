"""
统一 API 响应封装
"""
from pydantic import BaseModel, Field
from typing import Any, Optional


class ApiResponse(BaseModel):
    """统一 API 响应格式"""

    code: int = Field(default=200, description="状态码：200成功，500失败")
    state: str = Field(default="success", description="状态：success 成功，error 失败")
    message: str = Field(default="ok", description="状态描述")
    data: Any = Field(default=None, description="业务数据，无数据返回 null")
    request_id: Optional[str] = Field(default=None, description="请求ID（预留）")

    @classmethod
    def success(cls, data: Any = None, message: str = "ok") -> "ApiResponse":
        """成功响应"""
        return cls(code=200, state="success", message=message, data=data)

    @classmethod
    def error(cls, message: str = "Internal server error", code: int = 500) -> "ApiResponse":
        """失败响应"""
        return cls(code=code, state="error", message=message, data=None)
