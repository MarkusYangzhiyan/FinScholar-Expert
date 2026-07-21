"""
Yahoo finance 历史行情数据输入输出的数据契约协议
解决的是“输入输出应该长什么样”
"""

from typing import Literal, TypeAlias, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator, Field
from finscholar.schemas.yahoo_evidence import Evidence
from finscholar.schemas.financial_data import FinancialDataPoint

# 类型别名
# 查询数据的范围
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
    "ytd",  # year to date : 年初至今
    "max",  # yahoo finance 当前可以提供的最大历史范围
]


# 类型别名
# 每一条行情记录的时间粒度，也就是一条K线代表多长时间
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
    """
    规定了如果 Finscholar 想查询 yahoo finance 的历史行情数据，调用方必须按照什么格式提供查询参数

    Args:
        1. 不能传入没有规定的参数
        2. symbol : str  金融标的的代码/符号(Tsla,Apple,NVIDA....)
        3. period : 查询数据的范围
        4. interval : 每一条行情记录的时间粒度，也就是一条K线代表多长时间
        5. auto_adjust : 是否让 yfinance 自动对历史价格进行复权处理。

    """

    model_config = ConfigDict(extra="forbid")

    symbol: str
    period: YahooHistoryPeriod = "1mo"
    interval: YahooHistoryInterval = "1d"
    auto_adjust: bool = Field(
        default=False,
        description=(
            "是否自动复权；只有用户明确要求复权价格时,才设为 true，用户未说明时必须为 false"
        ),
    )

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """清理空格并统一证券代码为大写"""

        symbol = value.strip().upper()

        if not symbol:
            raise ValueError("symbol 不得为空")

        return symbol


class YahooFinanceHistoryOutput(BaseModel):
    """
    规定了 Yahoo finance 历史行情经过客户端处理后，必须以什么结构返回给 Tool、LangGraph 或其他调用方。

    Args:
        1. query : 查询的输入 -- 结构化后的 YahooFinanceHistoryInput
        2. evidence : 数据来源信息
        3. data_points : query 请求结果中，经过客户端提取和标准化后的金融数值

    evidence 和 data_points 中的数据应该是对应的，即evidence.evidence_id == data_point.evidence_id
    !Notice
        evidence 和 data_points 是一对多的
            一条evidence
                ├── close_price 数据点
                ├── volume 数据点
                ├── open_price 数据点
                └── 更多日期的数据点
    """

    model_config = ConfigDict(extra="forbid")

    query: YahooFinanceHistoryInput
    evidence: Evidence
    data_points: list[FinancialDataPoint]

    @model_validator(mode="after")
    def validate_evidence_links(self) -> Self:
        """确保所有金融数据点都关联到本次请求的证据。"""

        if any(
            data_point.evidence_id != self.evidence.evidence_id for data_point in self.data_points
        ):
            raise ValueError("data_points.evidence_id 必须与 evidence.evidence_id 一致")

        return self


__all__ = [
    "YahooFinanceHistoryInput",
    "YahooFinanceHistoryOutput",
    "YahooHistoryInterval",
    "YahooHistoryPeriod",
]
