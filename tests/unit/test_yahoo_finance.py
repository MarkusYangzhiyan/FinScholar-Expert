"""测试 Yahoo Finance 工具的数据契约。"""
from uuid import UUID
import pytest
from pydantic import ValidationError
from finscholar.schemas.yahoo_finance import YahooFinanceHistoryInput
from datetime import datetime, UTC, date 
from finscholar.schemas.financial_data import FinancialDataPoint
from finscholar.schemas.yahoo_evidence import Evidence
from finscholar.schemas.yahoo_finance import YahooFinanceHistoryInput, YahooFinanceHistoryOutput
from decimal import Decimal

EVIDENCE_ID = UUID("54a2b985-d251-4bd1-a96c-499bbbca1026")


def _make_history_evidence() -> Evidence:
    """创建历史行情测试证据。"""

    return Evidence(
        evidence_id=EVIDENCE_ID,
        source_type="market_data",
        source_name="Yahoo Finance",
        source_uri="https://query2.finance.yahoo.com/v8/finance/chart/TSLA",
        retrieved_at=datetime(2026, 7, 13, 9, 0, tzinfo=UTC),
        content='{"symbol":"TSLA","period":"1mo","interval":"1d"}',
        content_hash="a" * 64,
    )


def _make_close_price(evidence_id: UUID) -> FinancialDataPoint:
    """创建一条收盘价测试数据。"""

    return FinancialDataPoint(
        symbol="TSLA",
        metric_name="close_price",
        value=Decimal("407.760010"),
        currency="USD",
        unit="per_share",
        as_of_date=date(2026, 7, 10),
        provider="Yahoo Finance",
        evidence_id=evidence_id,
    )

def test_history_input_accepts_period_query() -> None:
    """历史行情输入应接受 period + interval 查询。"""

    query = YahooFinanceHistoryInput(
        symbol=" tsla ",
        period="1mo",
        interval="1d",
    )

    assert query.symbol == "TSLA"
    assert query.period == "1mo"
    assert query.interval == "1d"
    assert query.auto_adjust is False


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("period", "4mo"),
        ("interval", "4h"),
    ],
)
def test_history_input_rejects_unsupported_query_values(
    field_name: str,
    invalid_value: str,
) -> None:
    """历史行情输入应拒绝 Yahoo Finance 不支持的查询值。"""


    input_data: dict[str, object] = {
        "symbol": "TSLA",
        "period": "1mo",
        "interval": "1d",
    }
    input_data[field_name] = invalid_value

    with pytest.raises(ValidationError, match=field_name):
        YahooFinanceHistoryInput.model_validate(input_data)


def test_history_output_connects_query_evidence_and_data() -> None:
    """历史行情输出应保留查询、证据和标准化数据点。"""

    query = YahooFinanceHistoryInput(
        symbol="TSLA",
        period="1mo",
        interval="1d",
    )
    evidence = _make_history_evidence()
    data_point = _make_close_price(evidence.evidence_id)

    output = YahooFinanceHistoryOutput(
        query=query,
        evidence=evidence,
        data_points=[data_point],
    )

    assert output.query == query
    assert output.evidence == evidence
    assert output.data_points == [data_point]


def test_history_output_rejects_unlinked_evidence() -> None:
    """金融数据点必须关联到本次行情请求产生的 Evidence。"""

    with pytest.raises(ValidationError, match="evidence_id"):
        YahooFinanceHistoryOutput(
            query=YahooFinanceHistoryInput(symbol="TSLA"),
            evidence=_make_history_evidence(),
            data_points=[
                _make_close_price(
                    UUID("704d269e-4161-483a-b7d5-b49975579462")
                )
            ],
        )