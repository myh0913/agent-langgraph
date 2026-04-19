"""
工具基类
所有自定义 Tools 应继承 BaseToolNode，统一 LLM 调用方式
"""
from typing import Optional, Any
from langchain_core.tools import BaseTool
from langchain_core.messages import SystemMessage, HumanMessage
from config.llm import get_llm_client, LLMClient


class BaseToolNode(BaseTool):
    """
    工具基类，继承自 langchain BaseTool
    封装 LLM 调用，子类只需实现 _run_impl
    """

    def __init__(self, llm_client: Optional[LLMClient] = None, **kwargs):
        """
        初始化工具节点

        Args:
            llm_client: 可选，指定 LLM 客户端，默认使用全局单例
            **kwargs: 透传给 BaseTool
        """
        super().__init__(**kwargs)
        self._llm_client = llm_client

    @property
    def llm(self) -> LLMClient:
        """获取 LLM 客户端"""
        if self._llm_client is None:
            return get_llm_client()
        return self._llm_client

    def _build_messages(self, prompt: str, system: Optional[str] = None) -> list:
        """
        构建消息列表

        Args:
            prompt: 用户 prompt
            system: 系统提示词（可选）

        Returns:
            list: 消息列表
        """
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))
        return messages

    def _call_llm(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        调用 LLM（同步）

        Args:
            prompt: 用户 prompt
            system: 系统提示词
            **kwargs: 透传给 LLM

        Returns:
            str: LLM 回复
        """
        messages = self._build_messages(prompt, system)
        result = self.llm.invoke(messages, **kwargs)
        return self._extract_content(result)

    async def _acall_llm(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        调用 LLM（异步）

        Args:
            prompt: 用户 prompt
            system: 系统提示词
            **kwargs: 透传给 LLM

        Returns:
            str: LLM 回复
        """
        messages = self._build_messages(prompt, system)
        result = await self.llm.ainvoke(messages, **kwargs)
        return self._extract_content(result)

    def _extract_content(self, result: Any) -> str:
        """
        从 LLM 返回结果中提取文本内容

        Args:
            result: LLM 返回结果

        Returns:
            str: 文本内容
        """
        if hasattr(result, "content"):
            return result.content
        if isinstance(result, str):
            return result
        return str(result)

    def _run_impl(self, *args, **kwargs) -> Any:
        """
        实际业务逻辑（子类必须实现）
        用 self._call_llm() 或 self._acall_llm() 调用 LLM
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _run_impl"
        )

    def _run(self, *args, **kwargs) -> Any:
        """同步执行入口"""
        return self._run_impl(*args, **kwargs)

    async def _arun(self, *args, **kwargs) -> Any:
        """异步执行入口"""
        return await self._run_impl(*args, **kwargs)
