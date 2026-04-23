"""
提示词模板统一配置
所有 Agent 相关的 System Prompt 和格式化 Prompt 都在这里集中管理

主要模块：
1. 意图分类 - intent_classifier
2. 意图确认 - intent_confirm
3. 业务处理 - business_handler
4. 上下文压缩 - compression

用法：
    from config.prompts import INTENT_CLASSIFIER_SYSTEM, build_xxx_prompt
"""

# =============================================================================
# 一、意图分类系统提示词 (Intent Classification)
# =============================================================================

# 用途：LLM 判断用户消息的意图类型
# 调用位置：tools/intent_classifier.py 的 _run_impl()
INTENT_CLASSIFIER_SYSTEM = """你是一个意图分类专家。
用户会发送一条消息，你需要判断这条消息的意图类型。
请结合对话历史以及知识库来理解用户意图，避免孤立地回答单个问题。

请判断这条消息的意图类型：
BUSINESS - 业务相关，用户的问题与对话历史以及知识库相关，或需要通过调用工具/Skills访问后端API获取业务数据
GENERAL - 一般对话，用户的请求属于闲聊、问候、或与业务无关的普通对话
CONFIRM - 需要确认，消息模糊或需要用户进一步澄清或选择，通常是回应系统的追问
REMEMBER - 记住指令，用户明确要求记住某些内容（如"记住xxx"、"记下来xxx"、"请记住xxx"、"帮我记住xxx"、"记一下xxx"），此时必须将内容写入知识库

同时给出你的置信度（0到1之间）和简短理由。
按照以下格式返回（只返回 JSON，不要其他内容）：
{{"intent": "BUSINESS | GENERAL | CONFIRM | REMEMBER", "confidence": 0.0, "reason": "简短理由"}}"""

# =============================================================================
# 二、意图确认系统提示词 (Intent Confirmation)
# =============================================================================

# 用途：当意图不够明确时，追问用户或提供选项
# 调用位置：tools/intent_confirm.py 的 _run_impl()
INTENT_CONFIRM_SYSTEM = """你是一个意图确认专家。
当用户的意图不够明确时，你需要帮助用户明确他们的需求。
请结合对话历史以及知识库来理解上下文，避免孤立地回答单个问题。

【重要】如果用户的问题是关于对话本身的元问题，必须直接基于历史回答：
- "我刚才问了什么" → 直接说出用户上一条消息的内容
- "你还记得吗" → 基于历史如实回答
- 任何要求回顾历史的问题 → 直接回答，不要再追问

其他情况你可以：
1、如果能根据上下文合理推断用户意图，直接确认
2. 追问 - 通过提问来明确用户意图
3. 提供选择 - 给用户提供明确的选项让用户选择，提供选项时列出选项并标号
4. 引导 - 将用户引导至业务相关的话题

请用自然语言回复，用简洁、友好的语言与用户交流。"""

# =============================================================================
# 三、业务处理系统提示词 (Business Handler)
# =============================================================================

# 用途：分析后端 API 返回数据，生成用户友好的回复
# 调用位置：tools/business_handler.py 的 _analyze_and_respond()
BUSINESS_HANDLER_SYSTEM = """你是一个业务处理专家。
用户的问题已经被识别为业务相关，你需要：
1. 理解用户的具体需求
2. 选择合适的工具/Skills 来获取数据
3. 分析返回的业务数据
4. 生成清晰、易懂的回复

请结合对话历史以及知识库来理解上下文，避免孤立地回答单个问题。请始终保持专业、友好的服务态度。"""

# 用法：BusinessHandlerNode 处理 API 返回时注入为 system message
# temperature 建议 0.7（需要创造性来组织回复）

# =============================================================================
# 四、业务计划制定提示词 (Business Planning)
# =============================================================================

# 用途：LLM 分析用户需求，决定调用哪个工具/API
# 调用位置：tools/business_handler.py 的 _plan_api_call()
# 注意：此 prompt 是动态格式化的，包含已启用工具列表
BUSINESS_HANDLER_PLAN_TEMPLATE = """你是一个业务助手，擅长分解用户需求并制定行动计划。
请结合对话历史理解用户意图，避免孤立地回答单个问题。

请分析用户需求，从上述已启用的工具中选择最合适的一个来完成任务：

1. 如果对话历史或者当前上下文或者知识库已有相关信息能回答用户问题：
   - action: "answer"
   - reason: 简短说明为什么可以直接回答

2. 如果需要调用后端 API 或 Skills 获取数据：
   - action: "api_call"
   - skill_name: 技能名称（必须来自上述已启用列表中）
   - endpoint: API 端点
   - method: GET 或 POST
   - params: 参数

3. 如果意图仍然不明确需要用户确认：
   - action: "confirm"
   - confirm_message: 追问内容

请以以下 JSON 格式返回（只返回 JSON，不要其他内容）：
{{
  "action": "answer | api_call | confirm",
  "reason": "简短说明",
  "skill_name": "技能名称（仅 api_call 时需要，必须来自已启用列表）",
  "endpoint": "/api/xxx（仅 api_call 时需要）",
  "method": "GET 或 POST（仅 api_call 时需要）",
  "params": {{}}（仅 api_call 时需要）,
  "confirm_message": "追问内容（仅 confirm 时需要）"
}}"""

# 用法：动态注入已启用工具列表，让 LLM 决策
# temperature 建议 0.3（计划需要确定性，避免幻觉）

# =============================================================================
# 五、知识库回答提示词 (Knowledge Answering)
# =============================================================================

# 用途：基于知识库检索结果生成回答
# 调用位置：tools/business_handler.py 的 _answer_from_knowledge()

# 用法：注入知识库检索内容，让 LLM 组织回复
# temperature 建议 0.7（需要创造性来整合内容）
# 注意：实际返回时会自动添加来源标记 📚

# =============================================================================
# 六、API 分析回复提示词 (API Result Analysis)
# =============================================================================

# 用途：分析后端 API 返回，生成用户友好的回复
# 调用位置：tools/business_handler.py 的 _analyze_and_respond()

# =============================================================================
# 七、上下文压缩摘要提示词 (Context Compression)
# =============================================================================

# 用途：将过长的对话历史压缩为摘要
# 调用位置：memory/compression.py 的 compress()
COMPRESSION_SUMMARY_PROMPT = """请总结以下对话的要点，保持关键信息完整：

{dialog_text}

要求：
1. 概括用户的主要需求/问题
2. 概括助手的主要回复和行动
3. 保留关键细节（如数字、名称、结论等）
4. 用简洁的段落表述，中文回复
5. 控制在 500 字以内"""

COMPRESSION_SYSTEM = """你是一个专业的对话摘要助手，擅长提炼对话核心内容。"""

# 用法：当 token 超过阈值时，用此 prompt 调用 LLM 生成摘要
# 摘要结果会替代原始消息，大幅减少 token 占用

# =============================================================================
# 八、统一 Prompt 头部模板
# =============================================================================

# 用途：所有 LLM 思考类 prompt 的统一头部结构
# 包含 user_message / history / context / knowledge / tools 五个标准字段
# 各具体模板在 {standard_header} 占位符处插入此头部，后接各自的特有指令
STANDARD_PROMPT_HEADER = """用户请求：{user_message}

对话历史（共 {history_count} 条消息）：
{history_text}

当前上下文：
{context}

知识库参考：
{knowledge_text}

已启用的工具：
{available_tools_text}"""

# =============================================================================
# 九、默认回复模板 (Default Reply)
# =============================================================================

# 用途：无法识别意图时的兜底回复
DEFAULT_REPLY = """您好！我是您的智能助手。请问有什么可以帮您的？"""

# =============================================================================
# 十、一般回复系统提示词 (General Handler)
# =============================================================================

# 用途：处理 GENERAL 类型的一般对话（闲聊、问候、元问题等）
# 调用位置：graph/nodes.py 的 response_node
GENERAL_HANDLER_SYSTEM = """你是一个友好、智能的助手。
用户发送的是一般性问题、闲聊或关于对话本身的元问题。

请结合对话历史理解上下文，自然地回答用户。
如果用户问的是"我刚刚问了什么"或类似问题，请直接根据历史回答。

请用简洁、亲切的语言回复。"""

# =============================================================================
# 兼容性别名（旧的引用方式）
# =============================================================================

# 业务计划制定系统提示词
BUSINESS_PLAN_SYSTEM = """你是一个业务助手，擅长分解用户需求并制定行动计划。"""
# 知识库回答系统提示词
KNOWLEDGE_ANSWER_SYSTEM = """你是一个知识库助手，擅长基于参考内容回答用户问题。"""

# =============================================================================
# 辅助函数：构建动态 Prompt
# =============================================================================

def build_business_plan_prompt(
    user_message: str,
    history: list,
    context: dict = None,
    knowledge_text: str = "",
    available_tools_text: str = ""
) -> str:
    """
    构建业务计划制定 prompt

    Args:
        user_message: 用户消息
        history: 对话历史列表
        context: 上下文 dict
        knowledge_text: 格式化后的知识库内容
        available_tools_text: 已启用工具的描述文本

    Returns:
        str: 格式化后的完整 prompt = 标准头部 + 特有指令
    """
    history_count = len(history) if history else 0
    history_text = _format_history_for_prompt(history) if history else "（无历史消息）"
    context_str = str(context) if context else "（无）"

    # 渲染标准头部
    header = STANDARD_PROMPT_HEADER.format(
        user_message=user_message,
        history_count=history_count,
        history_text=history_text,
        context=context_str,
        knowledge_text=knowledge_text or "（无）",
        available_tools_text=available_tools_text or "（无）"
    )
    return header + "\n\n" + BUSINESS_HANDLER_PLAN_TEMPLATE


def build_knowledge_answer_prompt(
    user_message: str,
    history: list,
    context: dict = None,
    knowledge_text: str = "",
    available_tools_text: str = ""
) -> str:
    """
    构建知识库回答 prompt

    Args:
        user_message: 用户问题
        history: 对话历史
        context: 上下文 dict
        knowledge_text: 格式化后的知识库内容
        available_tools_text: 已启用工具描述文本

    Returns:
        str: 格式化后的完整 prompt
    """
    history_count = len(history) if history else 0
    history_text = _format_history_for_prompt(history) if history else "（无）"
    context_str = str(context) if context else "（无）"

    header = STANDARD_PROMPT_HEADER.format(
        user_message=user_message,
        history_count=history_count,
        history_text=history_text,
        context=context_str,
        knowledge_text=knowledge_text or "（无）",
        available_tools_text=available_tools_text or "（无）"
    )
    instructions = """请基于上述知识库内容，用清晰、友好的语言回答用户问题。
如果知识库内容不足以完全回答，请说明并建议用户补充提问。

回答："""
    return header + "\n\n" + instructions


def build_analyze_response_prompt(
    user_message: str,
    history: list,
    context: dict = None,
    knowledge_text: str = "",
    api_result: dict = None,
    available_tools_text: str = ""
) -> str:
    """
    构建 API 结果分析回复 prompt

    Args:
        user_message: 用户原始消息
        history: 对话历史
        context: 上下文 dict
        knowledge_text: 知识库内容（可选）
        api_result: API 返回数据
        available_tools_text: 已启用工具描述文本

    Returns:
        str: 格式化后的完整 prompt
    """
    history_count = len(history) if history else 0
    history_text = _format_history_for_prompt(history) if history else "（无）"
    context_str = str(context) if context else "（无）"

    header = STANDARD_PROMPT_HEADER.format(
        user_message=user_message,
        history_count=history_count,
        history_text=history_text,
        context=context_str,
        knowledge_text=knowledge_text or "（无）",
        available_tools_text=available_tools_text or "（无）"
    )
    instructions = f"""请根据返回数据，生成一段简洁、准确的用户回复。如果数据为空或异常，需要说明情况。

后端返回数据：
{str(api_result) if api_result else '（无）'}

回答："""
    return header + "\n\n" + instructions


def build_intent_classifier_prompt(
    user_message: str,
    history: list,
    context: dict = None,
    knowledge_text: str = "",
    available_tools_text: str = ""
) -> str:
    """
    构建意图分类 prompt

    Args:
        user_message: 用户消息
        history: 对话历史
        context: 上下文 dict
        knowledge_text: 知识库参考文本
        available_tools_text: 已启用工具描述文本

    Returns:
        str: 完整 prompt = 标准头部 + 特有指令
    """
    history_count = len(history) if history else 0
    history_text = _format_history_for_prompt(history) if history else "（无）"
    context_str = str(context) if context else "（无）"

    header = STANDARD_PROMPT_HEADER.format(
        user_message=user_message,
        history_count=history_count,
        history_text=history_text,
        context=context_str,
        knowledge_text=knowledge_text or "（无）",
        available_tools_text=available_tools_text or "（无）"
    )
    return header


def build_intent_confirm_prompt(
    user_message: str,
    history: list,
    context: dict = None,
    knowledge_text: str = "",
    available_tools_text: str = ""
) -> str:
    """
    构建意图确认 prompt

    Args:
        user_message: 用户消息
        history: 对话历史
        context: 上下文 dict
        knowledge_text: 知识库参考文本
        available_tools_text: 已启用工具描述文本

    Returns:
        str: 完整 prompt = 标准头部 + 特有指令
    """
    history_count = len(history) if history else 0
    history_text = _format_history_for_prompt(history) if history else "（无）"
    context_str = str(context) if context else "（无）"

    header = STANDARD_PROMPT_HEADER.format(
        user_message=user_message,
        history_count=history_count,
        history_text=history_text,
        context=context_str,
        knowledge_text=knowledge_text or "（无）",
        available_tools_text=available_tools_text or "（无）"
    )
    return header


def build_compression_summary_prompt(dialog_text: str) -> str:
    """
    构建上下文压缩摘要 prompt

    Args:
        dialog_text: 格式化的对话文本

    Returns:
        str: 完整 prompt
    """
    return COMPRESSION_SUMMARY_PROMPT.format(dialog_text=dialog_text)


def build_general_response_prompt(
    user_message: str,
    history: list,
    context: dict = None,
    knowledge_text: str = "",
    available_tools_text: str = ""
) -> str:
    """
    构建一般对话回复 prompt

    Args:
        user_message: 用户消息
        history: 对话历史
        context: 上下文 dict
        knowledge_text: 知识库参考文本
        available_tools_text: 已启用工具描述文本

    Returns:
        str: 完整 prompt
    """
    history_count = len(history) if history else 0
    history_text = _format_history_for_prompt(history) if history else "（无）"
    context_str = str(context) if context else "（无）"

    header = STANDARD_PROMPT_HEADER.format(
        user_message=user_message,
        history_count=history_count,
        history_text=history_text,
        context=context_str,
        knowledge_text=knowledge_text or "（无）",
        available_tools_text=available_tools_text or "（无）"
    )
    instructions = "请直接、自然地回答用户的问题。如果用户问的是回顾性问题，请基于上面的对话历史回答。"
    return header + "\n\n" + instructions


def _format_history_for_prompt(history: list, max_messages: int = 6) -> str:
    """
    格式化对话历史为 prompt 文本

    Args:
        history: 消息列表
        max_messages: 最多显示的消息条数

    Returns:
        str: 格式化的历史文本
    """
    if not history:
        return "（无）"

    lines = []
    # 只显示最近 max_messages 条
    for m in history[-max_messages:]:
        role = "用户" if m.get("role") == "user" else "助手"
        content = m.get("content", "")[:200]  # 截断超长内容
        lines.append(f"{role}：{content}")

    return "\n".join(lines) or "（无）"