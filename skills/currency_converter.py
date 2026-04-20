"""
货币转换 Skill
使用免费汇率 API，支持多币种之间的转换
"""
import json
import time
from typing import Optional, Dict, Any, ClassVar
from pydantic import BaseModel, Field
from tools.base import BaseToolNode
import httpx


class CurrencyConverterInput(BaseModel):
    """货币转换输入"""
    amount: float = Field(description="要转换的金额", default=1.0)
    from_currency: str = Field(description="源货币代码，如 USD/CNY/EUR/JPY")
    to_currency: str = Field(description="目标货币代码，如 USD/CNY/EUR/JPY")


class CurrencyConverterOutput(BaseModel):
    """货币转换输出"""
    success: bool
    original: Dict[str, Any] = Field(default_factory=dict)
    converted: float = 0.0
    rate: float = 0.0
    message: str = ""


class CurrencyConverterSkill(BaseToolNode):
    """货币转换技能"""

    SUPPORTED_CURRENCIES: ClassVar[list] = [
        "USD", "CNY", "EUR", "JPY", "GBP", "HKD", "AUD", "CAD", "SGD", "KRW",
        "THB", "MYR", "IDR", "PHP", "VND", "TWD", "INR", "CHF", "NZD", "SEK"
    ]

    def __init__(self, **kwargs):
        super().__init__(
            name="currency_converter",
            description=(
                "货币转换工具。当用户需要汇率查询或货币换算时使用。\n"
                "支持：USD, CNY, EUR, JPY, GBP, HKD, AUD, CAD, SGD, KRW 等20+种货币。\n"
                "用法示例：\n"
                "  - '100美元等于多少人民币'\n"
                "  - '美元兑日元汇率'\n"
                "  - '5000日元换成美元是多少'\n"
                "  - 'EUR to CNY rate'"
            ),
            args_schema=CurrencyConverterInput,
            **kwargs
        )
        # 缓存汇率，避免频繁请求（有效期1小时）
        self._rate_cache: Dict[str, Any] = {}
        self._cache_time: float = 0
        self._cache_ttl: int = 3600

    def _run_impl(
        self,
        amount: float = 1.0,
        from_currency: str = "USD",
        to_currency: str = "CNY"
    ) -> CurrencyConverterOutput:
        """
        执行货币转换

        Args:
            amount: 要转换的金额
            from_currency: 源货币代码
            to_currency: 目标货币代码

        Returns:
            CurrencyConverterOutput: 转换结果
        """
        # 标准化货币代码（大写）
        from_curr = from_currency.upper().strip()
        to_curr = to_currency.upper().strip()

        # 验证货币代码
        if from_curr not in self.SUPPORTED_CURRENCIES:
            return CurrencyConverterOutput(
                success=False,
                message=f"不支持的货币代码: {from_currency}，支持的货币: {', '.join(self.SUPPORTED_CURRENCIES)}"
            )
        if to_curr not in self.SUPPORTED_CURRENCIES:
            return CurrencyConverterOutput(
                success=False,
                message=f"不支持的货币代码: {to_currency}，支持的货币: {', '.join(self.SUPPORTED_CURRENCIES)}"
            )

        # 如果相同货币，直接返回
        if from_curr == to_curr:
            return CurrencyConverterOutput(
                success=True,
                original={"amount": amount, "currency": from_curr},
                converted=amount,
                rate=1.0,
                message=f"{amount} {from_curr} = {amount} {to_curr}"
            )

        # 获取汇率
        rate = self._get_exchange_rate(from_curr, to_curr)
        if rate is None:
            return CurrencyConverterOutput(
                success=False,
                message="获取汇率失败，请稍后重试"
            )

        # 计算转换结果
        converted = round(amount * rate, 2)

        return CurrencyConverterOutput(
            success=True,
            original={"amount": amount, "currency": from_curr},
            converted=converted,
            rate=rate,
            message=f"{amount} {from_curr} = {converted} {to_curr}（汇率: 1 {from_curr} = {rate:.4f} {to_curr}）"
        )

    def _get_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """
        获取汇率（带缓存）

        Args:
            from_currency: 源货币
            to_currency: 目标货币

        Returns:
            float: 汇率，或 None 获取失败
        """
        cache_key = f"{from_currency}_{to_currency}"

        # 检查缓存
        if cache_key in self._rate_cache:
            if time.time() - self._cache_time < self._cache_ttl:
                return self._rate_cache[cache_key]

        # 获取基准汇率（USD 为基准）
        usd_rate_from = self._get_usd_rate(from_currency)
        usd_rate_to = self._get_usd_rate(to_currency)

        if usd_rate_from is None or usd_rate_to is None:
            return None

        # 计算交叉汇率
        rate = usd_rate_to / usd_rate_from

        # 更新缓存
        self._rate_cache[cache_key] = rate
        self._cache_time = time.time()

        return rate

    def _get_usd_rate(self, currency: str) -> Optional[float]:
        """
        获取货币对 USD 的汇率

        Args:
            currency: 货币代码

        Returns:
            float: 1 USD 等于多少该货币，或 None 获取失败
        """
        if currency == "USD":
            return 1.0

        cache_key = f"USD_{currency}"

        # 检查缓存
        if cache_key in self._rate_cache:
            if time.time() - self._cache_time < self._cache_ttl:
                return self._rate_cache[cache_key]

        # 使用免费 API 获取汇率
        try:
            # 方案1：使用 frankfurter.app（免费，无需 API key）
            url = f"https://api.frankfurter.app/latest?from=USD&to={currency}"
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    if "rates" in data and currency in data["rates"]:
                        rate = float(data["rates"][currency])
                        self._rate_cache[cache_key] = rate
                        return rate

        except Exception as e:
            print(f"获取汇率失败: {e}")

        return None

    def get_supported_currencies(self) -> list:
        """获取支持的货币列表"""
        return self.SUPPORTED_CURRENCIES.copy()