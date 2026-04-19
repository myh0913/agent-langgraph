"""
工具注册表
所有 Tools/Skills 统一注册管理，支持按名称查找和批量绑定
"""
from typing import Dict, List, Type
from langchain_core.tools import BaseTool


class ToolRegistry:
    """
    工具注册表
    负责工具的注册、查找、批量绑定
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_classes: Dict[str, Type[BaseTool]] = {}

    def register(self, tool: BaseTool) -> None:
        """
        注册一个工具实例

        Args:
            tool: BaseTool 实例
        """
        self._tools[tool.name] = tool

    def register_class(self, name: str, cls: Type[BaseTool]) -> None:
        """
        注册一个工具类（延迟实例化）

        Args:
            name: 工具名称
            cls: BaseTool 子类
        """
        self._tool_classes[name] = cls

    def get(self, name: str) -> BaseTool:
        """
        获取工具实例（如果注册的是类则延迟实例化）

        Args:
            name: 工具名称

        Returns:
            BaseTool: 工具实例
        """
        if name in self._tools:
            return self._tools[name]

        if name in self._tool_classes:
            instance = self._tool_classes[name]()
            self._tools[name] = instance
            return instance

        raise KeyError(f"Tool '{name}' not found in registry")

    def list_tools(self) -> List[str]:
        """
        列出所有已注册的工具名称

        Returns:
            List[str]: 工具名称列表
        """
        return list(self._tools.keys()) + list(self._tool_classes.keys())

    def bind_all(self) -> List[BaseTool]:
        """
        将所有工具实例化并返回列表
        用于 LangGraph 的 tool_node 或 bind_tools()

        Returns:
            List[BaseTool]: 工具实例列表
        """
        for name in self._tool_classes:
            if name not in self._tools:
                self._tools[name] = self._tool_classes[name]()

        return list(self._tools.values())


# 全局工具注册表
_global_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """获取全局工具注册表"""
    return _global_registry


def register_tool(tool: BaseTool):
    """快捷注册工具"""
    _global_registry.register(tool)


def get_tool(name: str) -> BaseTool:
    """快捷获取工具"""
    return _global_registry.get(name)
