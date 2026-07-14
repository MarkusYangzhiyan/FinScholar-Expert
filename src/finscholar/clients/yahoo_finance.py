"""访问并规范化 Yahoo Finance 历史行情。"""

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Protocol
from urllib.parse import quote
from uuid import UUID, uuid4

import pandas as pd

from finscholar.schemas.financial_data import FinancialDataPoint
from finscholar.schemas.yahoo_evidence import Evidence
from finscholar.schemas.yahoo_finance import (
    YahooFinanceHistoryInput,
    YahooFinanceHistoryOutput,
)


# frozen = True: 对象创建后不能重新修改参数值
# slots = True: 改对象有且仅有定义的参数，不能增加，避免typo错误而给对象增加新的参数
@dataclass(frozen=True, slots=True)
class YahooHistoryRawResult:
    """它只是 Gateway 与 Client 之间的内部数据容器,不是最终输出契约"""

    frame: pd.DataFrame
    currency: str | None


class YahooHistoryGateway(Protocol):
    """传给 Client 的 Gateway 必须有 fetch_history() 方法。"""

    def fetch_history(
        self,
        query: YahooFinanceHistoryInput,
    ) -> YahooHistoryRawResult:
        """获取未经 FinScholar 标准化的 Yahoo 行情。"""


class YahooFinanceClient:
    """
    将 Yahoo 原始行情转换为 FinScholar 数据契约。
    执行三步
        1. 调用 Gateway 获得 YahooHistoryRawResult
        2. 生成 Evidence 和 FinancialDataPoint
        3. 返回 YahooFinanceHistoryOutput
    """

    def __init__(self, gateway: YahooHistoryGateway) -> None:
        self._gateway = gateway

    async def get_history(
        self,
        query: YahooFinanceHistoryInput,
    ) -> YahooFinanceHistoryOutput:
        """获取历史行情并返回带证据的标准化结果。"""

        raw_result = await asyncio.to_thread(
            self._gateway.fetch_history,
            query,
        )

        evidence_id = uuid4()
        content = self._serialize_history(raw_result)

        evidence = Evidence(
            evidence_id=evidence_id,
            source_type="market_data",
            source_name="Yahoo Finance",
            source_uri=(
                f"https://query2.finance.yahoo.com/v8/finance/chart/{quote(query.symbol, safe='')}"
            ),
            retrieved_at=datetime.now(UTC),
            content=content,
            content_hash=sha256(content.encode("utf-8")).hexdigest(),
        )

        data_points = self._build_close_prices(
            query=query,
            raw_result=raw_result,
            evidence_id=evidence_id,
        )

        return YahooFinanceHistoryOutput(
            query=query,
            evidence=evidence,
            data_points=data_points,
        )

    @staticmethod
    def _serialize_history(
        raw_result: YahooHistoryRawResult,
    ) -> str:
        """把原始 DataFrame 转换为可审计的 JSON。"""

        raw_json = raw_result.frame.reset_index().to_json(
            orient="records",
            date_format="iso",
        )

        if raw_json is None:
            raise RuntimeError("Yahoo 历史行情序列化失败")

        return json.dumps(
            {
                "currency": raw_result.currency,
                "rows": json.loads(raw_json),
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    @staticmethod
    def _build_close_prices(
        *,
        query: YahooFinanceHistoryInput,
        raw_result: YahooHistoryRawResult,
        evidence_id: UUID,
    ) -> list[FinancialDataPoint]:
        """将 Yahoo Close 列转换为标准收盘价数据点。"""

        return [
            FinancialDataPoint(
                symbol=query.symbol,
                metric_name="close_price",
                value=Decimal(str(value)),
                currency=raw_result.currency,
                unit="per_share",
                as_of_date=pd.Timestamp(index).date(),
                provider="Yahoo Finance",
                evidence_id=evidence_id,
            )
            for index, value in raw_result.frame["Close"].items()
        ]


__all__ = [
    "YahooFinanceClient",
    "YahooHistoryGateway",
    "YahooHistoryRawResult",
]
