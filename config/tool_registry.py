"""
工具注册表
所有 Tools/Skills 统一注册管理，支持按名称查找和批量绑定
支持 enabled 字段统一控制开关
"""
from typing import Dict, List, Type, Optional
from dataclasses import dataclass, field
from langchain_core.tools import BaseTool


@dataclass
class ToolConfig:
    """工具配置，包含启用/禁用开关"""
    enabled: bool = True           # 是否启用
    description: str = ""          # 工具描述（用于 LLM 决策）
    params: dict = field(default_factory=dict)  # 额外参数


class ToolRegistry:
    """
    工具注册表
    负责工具的注册、查找、批量绑定
    支持 enabled 字段统一管理工具开关
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_classes: Dict[str, Type[BaseTool]] = {}
        self._configs: Dict[str, ToolConfig] = {}  # 每个工具的配置

    def register(
        self,
        tool: BaseTool,
        enabled: bool = True,
        description: str = None
    ) -> None:
        """
        注册一个工具实例

        Args:
            tool: BaseTool 实例
            enabled: 是否启用（默认 True）
            description: 工具描述，用于 LLM 决策
        """
        self._tools[tool.name] = tool
        self._configs[tool.name] = ToolConfig(
            enabled=enabled,
            description=description or tool.description
        )

    def register_class(
        self,
        name: str,
        cls: Type[BaseTool],
        enabled: bool = True,
        description: str = None
    ) -> None:
        """
        注册一个工具类（延迟实例化）

        Args:
            name: 工具名称
            cls: BaseTool 子类
            enabled: 是否启用（默认 True）
            description: 工具描述，用于 LLM 决策
        """
        self._tool_classes[name] = cls
        # 注册时还没实例，所以先存配置
        self._configs[name] = ToolConfig(
            enabled=enabled,
            description=description or ""
        )

    def is_enabled(self, name: str) -> bool:
        """检查工具是否启用"""
        return self._configs.get(name, ToolConfig()).enabled

    def set_enabled(self, name: str, enabled: bool) -> bool:
        """
        设置工具启用/禁用状态

        Args:
            name: 工具名称
            enabled: 是否启用

        Returns:
            bool: 是否设置成功
        """
        if name not in self._configs:
            return False
        self._configs[name].enabled = enabled
        return True

    def get_config(self, name: str) -> Optional[ToolConfig]:
        """获取工具配置"""
        return self._configs.get(name)

    def get_enabled_tools(self) -> List[BaseTool]:
        """
        获取所有已启用工具的实例列表

        Returns:
            List[BaseTool]: 已启用工具实例列表
        """
        result = []
        for name, tool in self._tools.items():
            if self.is_enabled(name):
                result.append(tool)
        # 处理延迟实例化的类
        for name, cls in self._tool_classes.items():
            if name not in self._tools and self.is_enabled(name):
                instance = cls()
                self._tools[name] = instance
                result.append(instance)
        return result

    def get_enabled_descriptions(self) -> List[dict]:
        """
        获取所有已启用工具的描述列表（用于 LLM 决策）

        Returns:
            List[dict]: [{name, description, enabled}, ...]
        """
        result = []
        for name in list(self._tools.keys()) + list(self._tool_classes.keys()):
            cfg = self._configs.get(name, ToolConfig())
            result.append({
                "name": name,
                "description": cfg.description,
                "enabled": cfg.enabled
            })
        return result

    def get(self, name: str) -> BaseTool:
        """
        获取工具实例（如果注册的是类则延迟实例化）
        注意：即使工具被禁用也能获取到实例，具体是否可用由调用方判断

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
        列出所有已注册的工具名称（含 enabled 状态）

        Returns:
            List[str]: 工具名称列表
        """
        return list(set(list(self._tools.keys()) + list(self._tool_classes.keys())))

    def list_tools_with_status(self) -> List[dict]:
        """列出所有工具及状态"""
        result = []
        for name in self.list_tools():
            cfg = self._configs.get(name, ToolConfig())
            result.append({
                "name": name,
                "enabled": cfg.enabled,
                "description": cfg.description
            })
        return result

    def bind_all(self) -> List[BaseTool]:
        """
        将所有工具实例化并返回列表（只包含 enabled 的）
        用于 LangGraph 的 tool_node 或 bind_tools()

        Returns:
            List[BaseTool]: 已启用工具实例列表
        """
        return self.get_enabled_tools()


# 全局工具注册表
_global_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """获取全局工具注册表"""
    return _global_registry


def register_tool(tool: BaseTool, enabled: bool = True, description: str = None):
    """快捷注册工具"""
    _global_registry.register(tool, enabled=enabled, description=description)


def get_tool(name: str) -> BaseTool:
    """快捷获取工具"""
    return _global_registry.get(name)


def set_tool_enabled(name: str, enabled: bool) -> bool:
    """快捷设置工具启用状态"""
    return _global_registry.set_enabled(name, enabled)


def get_enabled_tools() -> List[BaseTool]:
    """快捷获取所有已启用工具"""
    return _global_registry.get_enabled_tools()