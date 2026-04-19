"""
LLM 客户端封装
统一管理 ChatOpenAI / ChatMinimax 等模型的初始化和调用
"""
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.outputs import ChatResult
from config.settings import settings


class LLMClient:
    """
    LLM 客户端封装类（单例）
    支持 OpenAI 兼容格式的 API（OpenAI / MiniMax 等）
    """

    _instance: Optional["LLMClient"] = None
    _client: ChatOpenAI = None

    def __new__(cls, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 60,
        **kwargs
    ):
        """
        初始化 LLM 客户端

        Args:
            model: 模型名称，默认读 settings.MODEL_NAME
            api_key: API Key，默认读 settings.MODEL_API_KEY
            base_url: API 地址，默认读 settings.MODEL_BASE_URL
            temperature: 温度参数
            max_tokens: 最大 token 数
            timeout: 超时时间（秒）
        """
        # 避免重复初始化
        if getattr(self, "_initialized", False):
            return

        self.model = model or settings.MODEL_NAME
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.api_key = api_key or settings.MODEL_API_KEY
        self.base_url = base_url or settings.MODEL_BASE_URL

        self._init_client()
        self._initialized = True

    def _init_client(self):
        """初始化底层的 ChatOpenAI 实例（OpenAI 兼容 API 均可使用）"""
        self._client = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
        )

    @property
    def client(self) -> ChatOpenAI:
        """获取底层客户端"""
        return self._client

    def invoke(
        self,
        messages: list[BaseMessage],
        **kwargs
    ) -> ChatResult:
        """
        同步调用 LLM

        Args:
            messages: 消息列表 (SystemMessage / HumanMessage / AIMessage)
            **kwargs: 透传参数 (temperature / max_tokens 等)

        Returns:
            ChatResult: LLM 返回结果
        """
        return self._client.invoke(messages, **kwargs)

    async def ainvoke(
        self,
        messages: list[BaseMessage],
        **kwargs
    ) -> ChatResult:
        """
        异步调用 LLM

        Args:
            messages: 消息列表
            **kwargs: 透传参数

        Returns:
            ChatResult: LLM 返回结果
        """
        return await self._client.ainvoke(messages, **kwargs)

    def chat(
        self,
        prompt: str,
        system: str = None,
        **kwargs
    ) -> str:
        """
        简易对话接口（同步）

        Args:
            prompt: 用户输入
            system: 系统提示词（可选）
            **kwargs: 透传参数

        Returns:
            str: LLM 回复文本
        """
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        result = self.invoke(messages, **kwargs)
        return self._extract_content(result)

    async def achat(
        self,
        prompt: str,
        system: str = None,
        **kwargs
    ) -> str:
        """
        简易对话接口（异步）

        Args:
            prompt: 用户输入
            system: 系统提示词（可选）
            **kwargs: 透传参数

        Returns:
            str: LLM 回复文本
        """
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        result = await self.ainvoke(messages, **kwargs)
        return self._extract_content(result)

    def _extract_content(self, result) -> str:
        """从 LLM 返回结果中提取文本内容"""
        if hasattr(result, "content"):
            return result.content
        if isinstance(result, str):
            return result
        return str(result)

    def __repr__(self):
        return (
            f"LLMClient(model={self.model}, "
            f"base_url={self.base_url})"
        )


# 全局单例（延迟初始化）
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    获取全局 LLM 客户端单例

    Returns:
        LLMClient: 全局客户端实例
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def rebuild_llm_client(**kwargs) -> LLMClient:
    """
    重建 LLM 客户端（用于动态切换模型/配置）

    Returns:
        LLMClient: 新的客户端实例
    """
    global _llm_client
    _llm_client = LLMClient(**kwargs)
    return _llm_client
