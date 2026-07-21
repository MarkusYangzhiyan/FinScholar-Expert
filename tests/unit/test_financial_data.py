"""测试统一金融数据点契约。"""

from datetime import date
from decimal import Decimal
from uuid import UUID
import pytest
from pydantic import ValidationError
from finscholar.schemas.financial_data import FinancialDataPoint


def test_financial_data_point_accepts_tsla_close_price() -> None:
    """FinancialDataPoint 应接受字段完整的 TSLA 收盘价。"""

    # 暂时放在函数内导入，确保 Schema 不存在时测试正常失败。
    from finscholar.schemas.financial_data import FinancialDataPoint

    data_point = FinancialDataPoint(
        symbol="TSLA",
        metric_name="close_price",
        value=Decimal("407.760010"),
        currency="USD",
        unit="per_share",
        period_start=None,
        period_end=None,
        as_of_date=date(2026, 7, 10),
        provider="Yahoo Finance",
        evidence_id=UUID("d50e140e-f8ab-41eb-8de0-8e6a1c7ca268"),
    )

    assert data_point.symbol == "TSLA"
    assert data_point.metric_name == "close_price"
    assert data_point.value == Decimal("407.760010")
    assert isinstance(data_point.value, Decimal)
    assert data_point.currency == "USD"
    assert data_point.unit == "per_share"
    assert data_point.period_start is None
    assert data_point.period_end is None
    assert data_point.as_of_date == date(2026, 7, 10)
    assert data_point.provider == "Yahoo Finance"
    assert data_point.evidence_id == UUID("d50e140e-f8ab-41eb-8de0-8e6a1c7ca268")


def test_financial_data_point_rejects_float_value() -> None:
    """金融数值不得直接接受二进制 float。"""

    with pytest.raises(ValidationError, match="value"):
        FinancialDataPoint.model_validate(
            {
                "symbol": "TSLA",
                "metric_name": "close_price",
                # 故意传入二进制浮点数。
                "value": 407.760010,
                "currency": "USD",
                "unit": "per_share",
                "period_start": None,
                "period_end": None,
                "as_of_date": date(2026, 7, 10),
                "provider": "Yahoo Finance",
                "evidence_id": UUID("468a9ce4-211f-47be-910b-6577d024bded"),
            }
        )


def test_financial_data_point_rejects_unknown_fields() -> None:
    """FinancialDataPoint 应拒绝契约中未定义的字段。"""

    with pytest.raises(ValidationError, match="unexpected_field"):
        FinancialDataPoint.model_validate(
            {
                "symbol": "TSLA",
                "metric_name": "close_price",
                "value": Decimal("407.760010"),
                "currency": "USD",
                "unit": "per_share",
                "period_start": None,
                "period_end": None,
                "as_of_date": date(2026, 7, 10),
                "provider": "Yahoo Finance",
                "evidence_id": UUID("fb531b0d-f4ac-4cbb-a0dc-d43fd2e8033a"),
                "unexpected_field": "不应被接受",
            }
        )


def test_financial_data_point_requires_time_context() -> None:
    """金融数据必须包含时点日期或报告期间。"""

    with pytest.raises(ValidationError, match="必须提供 as_of_date"):
        FinancialDataPoint(
            symbol="TSLA",
            metric_name="close_price",
            value=Decimal("407.760010"),
            currency="USD",
            unit="per_share",
            period_start=None,
            period_end=None,
            as_of_date=None,
            provider="Yahoo Finance",
            evidence_id=UUID("0b008122-c796-43ec-bc20-287115be018d"),
        )


@pytest.mark.parametrize(
    ("period_start", "period_end"),
    [
        (date(2026, 1, 1), None),
        (None, date(2026, 3, 31)),
    ],
)
def test_financial_data_point_requires_complete_period(
    period_start: date | None,
    period_end: date | None,
) -> None:
    """period_start 和 period_end 必须同时提供或同时为空。"""

    with pytest.raises(
        ValidationError,
        match="period_start 和 period_end 必须同时提供",
    ):
        FinancialDataPoint(
            symbol="TSLA",
            metric_name="total_revenue",
            value=Decimal("25500000000"),
            currency="USD",
            unit="currency",
            period_start=period_start,
            period_end=period_end,
            as_of_date=None,
            provider="Yahoo Finance",
            evidence_id=UUID("30fa3061-e6d5-490b-b686-64d37929334e"),
        )


def test_financial_data_point_rejects_reversed_period() -> None:
    """报告期开始日期不得晚于结束日期。"""
    with pytest.raises(
        ValidationError,
        match="period_start 不得晚于 period_end",
    ):
        FinancialDataPoint(
            symbol="TSLA",
            metric_name="total_revenue",
            value=Decimal("25500000000"),
            currency="USD",
            unit="currency",
            period_start=date(2026, 4, 1),
            period_end=date(2026, 3, 31),
            as_of_date=None,
            provider="Yahoo Finance",
            evidence_id=UUID("61690eef-f458-4a75-9c3d-f3d764ae6db1"),
        )


def test_point_in_time_data_allows_omitting_period_and_currency() -> None:
    """成交量等时点型指标应允许省略币种和报告期间。"""

    data_point = FinancialDataPoint(
        symbol="TSLA",
        metric_name="volume",
        value=Decimal("33342700"),
        unit="shares",
        as_of_date=date(2026, 7, 10),
        provider="Yahoo Finance",
        evidence_id=UUID("08e5ecbd-210f-423c-b8bf-09ff982ce61c"),
    )

    assert data_point.currency is None
    assert data_point.period_start is None
    assert data_point.period_end is None


def test_period_data_allows_omitting_as_of_date() -> None:
    """期间型指标具有完整报告期时应允许省略 as_of_date。"""

    data_point = FinancialDataPoint(
        symbol="TSLA",
        metric_name="total_revenue",
        value=Decimal("25500000000"),
        currency="USD",
        unit="currency",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        provider="Yahoo Finance",
        evidence_id=UUID("0390bee3-15ad-4450-bbd2-29a704c7a0e1"),
    )

    assert data_point.as_of_date is None


def test_financial_data_point_normalizes_symbol() -> None:
    """股票代码应清理首尾空格并转换为大写。"""
    data_point = FinancialDataPoint(
        symbol=" tsla ",
        metric_name="close_price",
        value=Decimal("407.760010"),
        currency="USD",
        unit="per_share",
        as_of_date=date(2026, 7, 10),
        provider="Yahoo Finance",
        evidence_id=UUID("f4efb8b2-fd70-4a85-925e-7fa33f9ae6ed"),
    )

    assert data_point.symbol == "TSLA"


def test_financial_data_point_rejects_blank_symbol() -> None:
    """股票代码不得为空白字符串。"""

    with pytest.raises(ValidationError, match="symbol 不得为空"):
        FinancialDataPoint(
            symbol="   ",
            metric_name="close_price",
            value=Decimal("407.760010"),
            currency="USD",
            unit="per_share",
            as_of_date=date(2026, 7, 10),
            provider="Yahoo Finance",
            evidence_id=UUID("3ef7f7a3-a4f0-443d-a063-de9e8245b48e"),
        )


def test_financial_data_point_normalizes_descriptive_fields() -> None:
    """指标名、单位、币种和提供方应使用规范化格式。"""

    data_point = FinancialDataPoint(
        symbol="TSLA",
        metric_name=" Close_Price ",
        value=Decimal("407.760010"),
        currency=" usd ",
        unit=" Per_Share ",
        as_of_date=date(2026, 7, 10),
        provider=" Yahoo Finance ",
        evidence_id=UUID("8d9ad65e-e2e3-495c-8c7d-439604d074c9"),
    )

    assert data_point.metric_name == "close_price"
    assert data_point.currency == "USD"
    assert data_point.unit == "per_share"
    assert data_point.provider == "Yahoo Finance"


@pytest.mark.parametrize(
    ("field_name", "blank_value"),
    [
        ("metric_name", "   "),
        ("unit", "   "),
        ("provider", "   "),
        ("currency", "   "),
    ],
)
def test_financial_data_point_rejects_blank_descriptive_fields(
    field_name: str,
    blank_value: str,
) -> None:
    """已提供的金融描述字段不得为空白。"""

    input_data: dict[str, object] = {
        "symbol": "TSLA",
        "metric_name": "close_price",
        "value": Decimal("407.760010"),
        "currency": "USD",
        "unit": "per_share",
        "as_of_date": date(2026, 7, 10),
        "provider": "Yahoo Finance",
        "evidence_id": UUID("0463d0c9-64aa-4915-9d5b-f28f4e26a297"),
    }
    input_data[field_name] = blank_value

    with pytest.raises(ValidationError, match=field_name):
        FinancialDataPoint.model_validate(input_data)
