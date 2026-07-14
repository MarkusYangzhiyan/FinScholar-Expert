"""测试 Yahoo Finance LangGraph Node。"""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from finscholar.nodes.yahoo_finance_node import (
    run_yahoo_finance_node,
)
from finscholar.schemas.yahoo_evidence import Evidence
from finscholar.schemas.yahoo_finance import (
    YahooFinanceHistoryInput,
    YahooFinanceHistoryOutput,
)
from finscholar.state.agent_state import AgentState
from finscholar.tools.yahoo_finance import YahooFinanceTool


def _make_output() -> YahooFinanceHistoryOutput:
    """创建 Node 测试使用的结构化结果。"""

    query = YahooFinanceHistoryInput(
        symbol="TSLA",
        period="1mo",
        interval="1d",
    )

    evidence = Evidence(
        evidence_id=UUID(
            "a60ee325-aea0-49b3-b23d-cc06d8ae54a2"
        ),
        source_type="market_data",
        source_name="Yahoo Finance",
        source_uri=(
            "https://query2.finance.yahoo.com/v8/"
            "finance/chart/TSLA"
        ),
        retrieved_at=datetime(2026, 7, 14, tzinfo=UTC),
        content='{"currency":"USD","rows":[]}',
        content_hash="a" * 64,
    )

    return YahooFinanceHistoryOutput(
        query=query,
        evidence=evidence,
        data_points=[],
    )


class FakeYahooHistoryClient:
    """记录 Node 最终传给 Client 的查询。"""

    def __init__(
        self,
        output: YahooFinanceHistoryOutput | None,
    ) -> None:
        self.output = output
        self.received_query: YahooFinanceHistoryInput | None = None

    async def get_history(
        self,
        query: YahooFinanceHistoryInput,
    ) -> YahooFinanceHistoryOutput:
        self.received_query = query

        if self.output is None:
            raise AssertionError("本次测试不应调用 Client")

        return self.output


class FailingYahooHistoryClient:
    """模拟 Yahoo 上游调用失败。"""

    async def get_history(
        self,
        query: YahooFinanceHistoryInput,
    ) -> YahooFinanceHistoryOutput:
        raise TimeoutError("Yahoo Finance 请求超时")


async def test_node_returns_yahoo_finance_output() -> None:
    """合法输入应调用 Tool 并返回结构化结果。"""

    expected_output = _make_output()
    client = FakeYahooHistoryClient(expected_output)
    tool = YahooFinanceTool(client=client)

    state: AgentState = {
        "yahoo_finance_input": {
            "symbol": " tsla ",
            "period": "1mo",
            "interval": "1d",
        }
    }

    update = await run_yahoo_finance_node(state, tool)

    assert client.received_query == expected_output.query
    assert update["yahoo_finance_output"] == expected_output
    assert update["yahoo_finance_error_type"] is None


@pytest.mark.parametrize(
    ("state", "expected_error"),
    [
        ({}, "MissingYahooFinanceInput"),
        (
            {
                "yahoo_finance_input": {
                    "symbol": " ",
                    "period": "4mo",
                }
            },
            "YahooFinanceInputValidationError",
        ),
    ],
)
async def test_node_rejects_invalid_input(
    state: AgentState,
    expected_error: str,
) -> None:
    """缺失或非法输入不应调用 Client。"""

    client = FakeYahooHistoryClient(output=None)
    tool = YahooFinanceTool(client=client)

    update = await run_yahoo_finance_node(state, tool)

    assert client.received_query is None
    assert update["yahoo_finance_output"] is None
    assert update["yahoo_finance_error_type"] == expected_error


async def test_node_records_upstream_failure() -> None:
    """上游失败应写入 State，而不是导致工作流崩溃。"""

    tool = YahooFinanceTool(
        client=FailingYahooHistoryClient()
    )
    state: AgentState = {
        "yahoo_finance_input": {
            "symbol": "TSLA",
            "period": "1mo",
            "interval": "1d",
        }
    }

    update = await run_yahoo_finance_node(state, tool)

    assert update["yahoo_finance_output"] is None
    assert update["yahoo_finance_error_type"] == "TimeoutError"
    assert (
        update["yahoo_finance_error_message"]
        == "Yahoo Finance 请求超时"
    )