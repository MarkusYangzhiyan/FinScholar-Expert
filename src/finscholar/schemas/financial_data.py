"""
描述一条标准化金融数据（yf返回的数据）
哪个金融标的、哪个指标、数值是多少、币种和单位是什么、属于哪个时间点，并由哪条 Evidence 支持？
"""

from typing import Self
from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator


class FinancialDataPoint(BaseModel):
    """记录一个具有明确口径、时间和来源的金融数值。"""
    
    model_config = ConfigDict(extra = "forbid")
    
    symbol: str

    # 标准化指标名称，例如 close_price、volume。
    metric_name: str

    # 金融数值使用 Decimal，避免二进制浮点误差。
    value: Decimal = Field(
        strict = True,
        description="禁止直接传入二进制 float 的精确金融数值"
    )

    # 币种；成交量等非金额指标可以为空。
    currency: str | None = None

    # 数值单位，例如 per_share、shares、percent。
    unit: str

    # 期间型数据使用，例如季度营收。
    period_start: date | None = None
    period_end: date | None = None

    # 时点型数据使用，例如某日收盘价。
    as_of_date: date | None = None

    # 数据提供方。
    provider: str

    # 关联到支持该数值的 Evidence。
    evidence_id: UUID

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(
        cls,
        value: str,
    ) -> str:
        """清理并统一 Yahoo Finance 股票代码。"""

        symbol = value.strip().upper()

        if not symbol:
            raise ValueError("symbol 不得为空")

        return symbol

    @field_validator("metric_name", "unit")
    @classmethod
    def normalize_lowercase_fields(
        cls,
        value: str,
    ) -> str:
        """清理并统一指标名称和单位。"""

        normalized_value = value.strip().lower()

        if not normalized_value:
            raise ValueError("metric_name 和 unit 不得为空")

        return normalized_value

    @field_validator("provider")
    @classmethod
    def normalize_provider(
        cls,
        value: str,
    ) -> str:
        """清理数据提供方名称，同时保留原始大小写。"""

        provider = value.strip()

        if not provider:
            raise ValueError("provider 不得为空")

        return provider



    @field_validator("currency")
    @classmethod
    def normalize_currency(
        cls,
        value: str | None,
    ) -> str | None:
        """清理币种代码并统一转换为大写。"""

        if value is None:
            return None

        currency = value.strip().upper()

        if not currency:
            raise ValueError("currency 不得为空；不适用时应传入 None")

        return currency
    


    @model_validator(mode="after")
    def validate_time_context(self) -> Self:
        """校验金融数据的时点日期和报告期间。"""

        has_as_of_date = self.as_of_date is not None
        has_period_start = self.period_start is not None
        has_period_end = self.period_end is not None

        # 此时has_period_start 和 has_period_end 是 bool 值
        if has_period_start != has_period_end:
            raise ValueError(
                "period_start 和 period_end 必须同时提供或同时为空"
            )

        has_complete_period = has_period_start and has_period_end

        if not has_as_of_date and not has_complete_period:
            raise ValueError(
                "必须提供 as_of_date 或完整的 period_start/period_end"
            )

        if (
            self.period_start is not None
            and self.period_end is not None
            and self.period_start > self.period_end
        ):
            raise ValueError(
                "period_start 不得晚于 period_end"
            )

        return self


__all__ = ["FinancialDataPoint"]