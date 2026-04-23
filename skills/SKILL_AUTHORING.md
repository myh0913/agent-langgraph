# Skill 编写规范

本文档定义了在 FI-Agent 项目中创建新 Skill 的标准方式，供人类开发者和其他 AI 阅读遵循。

---

## 一、文件结构

每个 Skill 独占一个 Python 文件，放置于 `skills/` 目录下：

```
skills/
├── __pycache__/
├── __init__.py           # 可选，放共享导入
├── currency_converter.py # 示例 Skill
└── SKILL_AUTHORING.md    # 本规范
```

---

## 二、必选组件

每个 Skill 必须包含以下四个部分：

### 1. Input 模型（Pydantic）

定义 Skill 接受的参数，供 LLM 和调用方校验输入。

```python
from pydantic import BaseModel, Field

class MySkillInput(BaseModel):
    query: str = Field(description="用户查询内容")
    limit: int = Field(description="返回结果数量上限", default=10)
```

**规则：**
- 必须继承 `BaseModel`
- 每个字段必须写 `description`，LLM 依靠它理解参数用途
- 带默认值的字段放在无默认值字段后面
- 使用标准 Python 类型（str / int / float / bool / list / dict）

---

### 2. Output 模型（Pydantic）

定义 Skill 的返回结构。建议始终包含 `success` 字段。

```python
class MySkillOutput(BaseModel):
    success: bool
    result: Optional[str] = None
    message: str = ""  # 返回给用户的友好描述
    data: Optional[dict] = None  # 原始数据，可选
```

**建议：**
- `success=True` 时填 `result` / `data`
- `success=False` 时填 `message` 说明错误原因
- 包含一个 `message` 字段用于直接展示给用户

---

### 3. Skill 类（继承 BaseToolNode）

核心逻辑类。

```python
from tools.base import BaseToolNode

class MySkill(BaseToolNode):
    def __init__(self, **kwargs):
        super().__init__(
            name="my_skill",           # 唯一标识，全局不可重复
            description=(              # 描述供 LLM 决策是否调用
                "处理 xxx 场景的 Skill。当用户需要 ... 时使用。\n"
                "用法示例：\n"
                "  - 'xxx'\n"
                "  - 'xxx'"
            ),
            args_schema=MySkillInput,  # 绑定输入模型
            **kwargs
        )

    def _run_impl(self, query: str, limit: int = 10) -> MySkillOutput:
        # 业务逻辑
        return MySkillOutput(success=True, result="...", message="完成")
```

**关键规则：**

| 项目 | 要求 |
|------|------|
| `name` | 字符串，唯一标识，推荐 snake_case |
| `description` | 供 LLM 理解何时调用，必须写清楚使用场景和示例 |
| `args_schema` | 绑定 Input 模型类（不是实例） |
| `_run_impl` | 必须实现，返回 Output 模型实例 |

---

### 4. 注册（`tools/__init__.py`）

创建完 Skill 后，必须在 `tools/__init__.py` 中注册，否则系统无法发现它。

```python
from config.tool_registry import get_registry

registry = get_registry()
registry.register_class(
    "my_skill",           # 必须与类中 name 一致
    MySkill,
    enabled=True           # 默认启用，可改为 False 禁用
)
```

**注册时机：** 应用启动时（`tools/__init__.py` 在 `main.py` 之前被导入），registry 会自动初始化。

---

## 三、完整示例

以下是一个"计算器 Skill"的最小完整实现：

```python
"""
计算器 Skill
支持基本数学运算
"""
from typing import Optional
from pydantic import BaseModel, Field
from tools.base import BaseToolNode
import math


class CalculatorInput(BaseModel):
    """计算器输入"""
    expression: str = Field(description="数学表达式，如 '2+3*4' 或 'sqrt(16)'")
    precision: int = Field(description="小数点精度", default=4)


class CalculatorOutput(BaseModel):
    """计算器输出"""
    success: bool
    expression: str = ""
    result: Optional[float] = None
    message: str = ""


class CalculatorSkill(BaseToolNode):
    """计算器 Skill"""

    # 支持的运算
    SUPPORTED_OPS = ["+", "-", "*", "/", "sqrt", "pow", "abs"]

    def __init__(self, **kwargs):
        super().__init__(
            name="calculator",
            description=(
                "数学计算工具。当用户需要进行数学运算时使用。\n"
                "支持：加(+)、减(-)、乘(*)、除(/)、平方根(sqrt)、幂(pow)、绝对值(abs)\n"
                "用法示例：\n"
                "  - '计算 2+3*4'\n"
                "  - '100除以7是多少'\n"
                "  - 'sqrt(144) 等于多少'"
            ),
            args_schema=CalculatorInput,
            **kwargs
        )

    def _run_impl(self, expression: str, precision: int = 4) -> CalculatorOutput:
        try:
            # 安全评估：只允许数字和运算符
            allowed = set("0123456789.+-*/() sqrtpowabs ")
            if not all(c in allowed for c in expression):
                return CalculatorOutput(
                    success=False,
                    expression=expression,
                    message="表达式包含非法字符"
                )

            result = eval(expression)  # 简化示例，实际请用安全方案
            result = round(result, precision)

            return CalculatorOutput(
                success=True,
                expression=expression,
                result=result,
                message=f"{expression} = {result}"
            )
        except Exception as e:
            return CalculatorOutput(
                success=False,
                expression=expression,
                message=f"计算错误: {str(e)}"
            )
```

---

## 四、LLM 是如何调用 Skill 的

`business_handler._plan_api_call()` 阶段：

1. 把所有已启用 Skills 的 `description` 组成列表，发给 LLM
2. LLM 分析用户意图，决定调用哪个 Skill、传什么参数
3. LLM 返回结构化 JSON：`{"skill_name": "xxx", "params": {...}}`
4. `business_handler._call_skill()` 从 registry 取出 Skill 实例，调用 `_run(**params)`

**因此，`description` 的编写质量直接影响 LLM 能否正确调用你的 Skill。**

---

## 五、description 写作指南

LLM 会根据 description 决定"这个 Skill 适不适合当前用户请求"。好的 description 应包含：

### 1. 清晰的使用场景

```
❌ 不好："处理数据的 Skill"
✅ 好："处理基金产品查询。当用户询问基金净值、费率、持仓时使用。"
```

### 2. 具体的能力边界

```
❌ 不好："支持多种货币"
✅ 好："支持 USD, CNY, EUR, JPY, GBP, HKD, AUD, CAD, SGD, KRW 等20+种货币"
```

### 3. 用法示例（可选但推荐）

```
用法示例：
  - '100美元等于多少人民币'
  - '美元兑日元汇率'
  - 'EUR to CNY rate'
```

### 4. 避免歧义

如果 Skill 有特殊限制或前置条件，必须说明：

```
"天气查询工具。仅支持中国大陆城市查询，国际城市请用其他方式。"
```

---

## 六、测试 Skill

启动服务后，用 API 触发匹配请求即可验证：

```bash
# 确认 Skill 已注册
curl http://localhost:8008/api/skills

# 发送匹配的消息（触发 LLM 决策调用）
curl -X POST http://localhost:8008/api/ai/message \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "100美元等于多少人民币"}'
```

也可以直接调用：

```python
from config.tool_registry import get_registry

registry = get_registry()
skill = registry.get("currency_converter")
result = skill._run(amount=100, from_currency="USD", to_currency="CNY")
print(result)
```

---

## 七、常见问题

**Q: Skill 报 `Tool Input should be a dict` 错误？**
A: `_run_impl` 的参数名必须与 Input 模型字段名一致，且 `_run` 调用时必须用关键字参数。

**Q: Skill 一直不被调用？**
A: 检查 description 是否覆盖了用户可能的表达方式，LLM 是根据 description 做决策的。

**Q: 如何调试 Skill？**
A: 在 `_run_impl` 内部加 `print`，输出会直接在启动服务的终端看到。

**Q: Skill 需要调用外部 API 吗？**
A: 可以，参考 `currency_converter.py` 中的 `httpx` 用法。注意添加超时和错误处理。

---

## 八、Token 获取机制

### Token 传递链路

```
请求 Header: Authorization: <token>
  → api/routes.py: http_request.headers.get("Authorization")
  → agent_input["token"]
  → business_handler._run_impl(token=token)
  → _call_skill(skill_name, params, token=token)
    → params["token"] = token  （注入）
    → skill._run(**params)        （传给 Skill）
```

### Skill 如何接收 Token

在 `_run_impl` 的参数列表中声明 `token: Optional[str] = None` 即可自动接收：

```python
def _run_impl(
    self,
    amount: float = 1.0,
    from_currency: str = "USD",
    to_currency: str = "CNY",
    token: Optional[str] = None,   # ← 自动收到
) -> CurrencyConverterOutput:
    print("收到token:", token)    # 可用于调试
    # 业务逻辑...
```

### 注意事项

- `token` 是**用户认证 token**，不是 LLM API Key
- Skill 收到 token 后可用于调用需要认证的外部 API
- 如果 Skill 不需要 token，可以不声明（params 中不会有这个字段）
- Token 也可以从项目全局配置 `config/settings.py` 读取（如 `SOME_API_TOKEN`），适合 Skill 自带的专用 API Key
