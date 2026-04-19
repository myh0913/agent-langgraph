"""
上下文压缩模块
基于 LLM 的消息摘要实现，类似 MessagesSummaryMemory
当会话历史 token 超过阈值时，自动压缩为摘要
"""
import tiktoken
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings


# 默认保留的最新消息条数（压缩时）
DEFAULT_KEEP_RECENT = 20


class ContextCompressor:
    """
    上下文压缩器
    - 使用 tiktoken 精确计算 token 数
    - 当总 token 超过阈值时，调用 LLM 将早期消息压缩为摘要
    - 保留最近 N 条消息不做压缩（确保对话连贯）
    """

    def __init__(
        self,
        token_limit: Optional[int] = None,
        keep_recent: int = DEFAULT_KEEP_RECENT,
    ):
        """
        Args:
            token_limit: token 阈值，超过此值触发压缩
            keep_recent: 压缩时保留的最近消息条数
        """
        self.token_limit = token_limit or settings.CONTEXT_TOKEN_LIMIT
        self.keep_recent = keep_recent
        self._encoder = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """
        计算消息列表的 token 总数

        Args:
            messages: 消息列表

        Returns:
            int: 估算的 token 总数
        """
        total = 0
        for msg in messages:
            # role 标签也占 token
            total += 5  # role + content 格式 overhead
            tokens = self._encoder.encode(str(msg.get("content", "")), disallowed_special=())
            total += len(tokens)
        # 每个消息的 overhead
        total += 3 * len(messages)
        return total

    def should_compress(self, messages: List[Dict[str, Any]]) -> bool:
        """判断是否需要压缩"""
        return self.count_tokens(messages) > self.token_limit

    def compress(
        self,
        messages: List[Dict[str, Any]],
        llm_client=None
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        执行压缩（LLM 摘要方式）

        Args:
            messages: 原始消息列表
            llm_client: LLM 客户端（必须提供）

        Returns:
            Tuple[压缩后的消息列表, 是否执行了压缩]
        """
        if not llm_client:
            # 没有 LLM 客户端，降级为简单截断
            return self._compress_simple(messages), False

        total_tokens = self.count_tokens(messages)
        if total_tokens <= self.token_limit:
            return messages, False

        # 分离系统消息和对话消息
        system_messages = [m for m in messages if m.get("role") == "system"]
        dialog_messages = [m for m in messages if m.get("role") != "system"]

        # 保留最近的 keep_recent 条对话消息不做压缩
        if len(dialog_messages) <= self.keep_recent:
            # 消息条数少但 token 多，说明每条很长，不再压缩
            return messages, False

        recent_messages = dialog_messages[-self.keep_recent:]
        older_messages = dialog_messages[:-self.keep_recent]

        # 用 LLM 生成摘要
        summary = self._generate_summary(older_messages, llm_client)

        # 构建压缩后的消息列表
        compressed = system_messages.copy()
        if summary:
            compressed.append({
                "role": "system",
                "content": f"[早期对话摘要] {summary}",
                "is_summary": True
            })
        compressed.extend(recent_messages)

        return compressed, True

    def _generate_summary(
        self,
        messages: List[Dict[str, Any]],
        llm_client
    ) -> str:
        """
        调用 LLM 生成对话摘要

        Args:
            messages: 待摘要的消息列表
            llm_client: LLM 客户端

        Returns:
            str: LLM 生成的摘要
        """
        # 将消息格式化为文本
        dialog_text = ""
        for m in messages:
            role = "用户" if m.get("role") == "user" else "助手"
            content = m.get("content", "")
            dialog_text += f"{role}：{content}\n\n"

        prompt = f"""请总结以下对话的要点，保持关键信息完整：

{dialog_text}

要求：
1. 概括用户的主要需求/问题
2. 概括助手的主要回复和行动
3. 保留关键细节（如数字、名称、结论等）
4. 用简洁的段落表述，中文回复
5. 控制在 500 字以内"""

        try:
            summary = llm_client.chat(
                prompt=prompt,
                system="你是一个专业的对话摘要助手，擅长提炼对话核心内容。"
            )
            return summary.strip()
        except Exception as e:
            # LLM 调用失败，降级为简单摘要
            return self._fallback_summary(messages)

    def _fallback_summary(self, messages: List[Dict[str, Any]]) -> str:
        """LLM 不可用时的简单摘要"""
        user_msgs = [m for m in messages if m.get("role") == "user"]
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]

        parts = []
        if user_msgs:
            parts.append(f"用户共发了 {len(user_msgs)} 条消息")
        if assistant_msgs:
            parts.append(f"助手共回复了 {len(assistant_msgs)} 条消息")
        if user_msgs:
            first = user_msgs[0]["content"][:80]
            last = user_msgs[-1]["content"][:80]
            parts.append(f"对话从「{first}...」到「{last}...」")
        return "；".join(parts)

    def _compress_simple(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        简单截断压缩（无 LLM 时降级使用）
        保留系统消息 + 最近 keep_recent 条
        """
        system_messages = [m for m in messages if m.get("role") == "system"]
        dialog_messages = [m for m in messages if m.get("role") != "system"]
        recent = dialog_messages[-self.keep_recent:]

        summary_text = f"[已压缩早期对话，保留最近 {len(recent)} 条消息，共跳过 {len(dialog_messages) - self.keep_recent} 条]"

        compressed = system_messages.copy()
        compressed.append({
            "role": "system",
            "content": summary_text,
            "is_summary": True
        })
        compressed.extend(recent)
        return compressed
