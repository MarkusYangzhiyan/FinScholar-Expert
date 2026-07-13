"""
采用明确的分类输入，不创建充满可选字段的万能对象：
YahooFinanceHistoryInput
YahooFinanceQuoteInput
YahooFinanceStatementInput
YahooFinanceCorporateActionsInput
"""


from typing import Literal, TypeAlias, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from finscholar.schemas.yahoo_evidence import Evidence
from finscholar.schemas.financial_data import FinancialDataPoint

YahooHistoryPeriod: TypeAlias = Literal[
    "1d",
    "5d",
    "1mo",
    "3mo",
    "6mo",
    "1y",
    "2y",
    "5y",
    "10y",
    "ytd",
    "max",
]

YahooHistoryInterval: TypeAlias = Literal[
    "1m",
    "2m",
    "5m",
    "15m",
    "30m",
    "60m",
    "90m",
    "1h",
    "1d",
    "5d",
    "1wk",
    "1mo",
    "3mo",
]


class YahooFinanceHistoryInput(BaseModel):
    """定义 Yahoo Finance 历史行情查询参数。"""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    period: YahooHistoryPeriod = "1mo"
    interval: YahooHistoryInterval = "1d"
    auto_adjust: bool = False

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """清理并统一证券代码。"""

        symbol = value.strip().upper()

        if not symbol:
            raise ValueError("symbol 不得为空")

        return symbol


class YahooFinanceHistoryOutput(BaseModel):
    """定义 Yahoo Finance 历史行情的结构化输出。"""

    model_config = ConfigDict(extra="forbid")

    query: YahooFinanceHistoryInput
    evidence: Evidence
    data_points: list[FinancialDataPoint]

    @model_validator(mode="after")
    def validate_evidence_links(self) -> Self:
        """确保所有金融数据点都关联到本次请求的证据。"""

        if any(
            data_point.evidence_id != self.evidence.evidence_id
            for data_point in self.data_points
        ):
            raise ValueError(
                "data_points.evidence_id 必须与 evidence.evidence_id 一致"
            )

        return self

__all__ = [
    "YahooFinanceHistoryInput",
    "YahooFinanceHistoryOutput",
    "YahooHistoryInterval",
    "YahooHistoryPeriod",
]