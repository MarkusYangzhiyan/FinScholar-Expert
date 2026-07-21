"""测试统一证据对象的数据契约。"""

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from finscholar.schemas.yahoo_evidence import Evidence


def test_evidence_accepts_yahoo_market_data() -> None:
    """Evidence 应接受字段完整、时间明确的 Yahoo Finance 数据来源。"""

    # 暂时放在测试函数内导入。
    # 因为生产 Schema 尚不存在，本次测试应该在这里失败。

    retrieved_at = datetime(
        2026,
        7,
        13,
        8,
        30,
        tzinfo=UTC,
    )

    evidence = Evidence(
        evidence_id=UUID("f8e866ad-7b86-4b21-a43d-39888e2a8872"),
        source_type="market_data",
        source_name="Yahoo Finance",
        source_uri="https://query2.finance.yahoo.com/v8/finance/chart/TSLA",
        document_id=None,
        page_number=None,
        section_title="TSLA historical prices",
        chunk_id=None,
        retrieved_at=retrieved_at,
        content='{"symbol":"TSLA","period":"1mo","interval":"1d"}',
        content_hash="a" * 64,
    )

    assert evidence.source_type == "market_data"
    assert evidence.source_name == "Yahoo Finance"
    assert evidence.document_id is None
    assert evidence.page_number is None
    assert evidence.retrieved_at == retrieved_at
    assert evidence.retrieved_at.tzinfo is UTC
    assert evidence.content_hash == "a" * 64


def test_evidence_allows_omitting_document_location() -> None:
    """API 没有文档定位字段时，应允许调用方直接省略。"""

    evidence = Evidence(
        evidence_id=UUID("e2729696-f27a-44bb-af96-d16ada71cfc1"),
        source_type="market_data",
        source_name="Yahoo Finance",
        source_uri="https://query2.finance.yahoo.com/v8/finance/chart/TSLA",
        retrieved_at=datetime(
            2026,
            7,
            13,
            9,
            0,
            tzinfo=UTC,
        ),
        content='{"symbol":"TSLA","period":"1mo","interval":"1d"}',
        content_hash="b" * 64,
    )

    assert evidence.document_id is None
    assert evidence.page_number is None
    assert evidence.section_title is None
    assert evidence.chunk_id is None


def test_evidence_rejects_unknown_fields() -> None:
    """Evidence 应拒绝契约中未定义的字段。"""

    with pytest.raises(ValidationError, match="unexpected_field"):
        Evidence.model_validate(
            {
                "evidence_id": UUID("83882c28-a9c7-45c8-bac8-77139a0cd16a"),
                "source_type": "market_data",
                "source_name": "Yahoo Finance",
                "source_uri": ("https://query2.finance.yahoo.com/v8/finance/chart/TSLA"),
                "retrieved_at": datetime(
                    2026,
                    7,
                    13,
                    9,
                    30,
                    tzinfo=UTC,
                ),
                "content": '{"symbol":"TSLA"}',
                "content_hash": "c" * 64,
                "unexpected_field": "不应被静默接受",
            }
        )


def test_evidence_rejects_naive_retrieved_at() -> None:
    """retrieved_at 没有时区信息时必须拒绝。"""

    with pytest.raises(ValidationError, match="retrieved_at"):
        Evidence(
            evidence_id=UUID("93940fe0-d525-4251-b105-7986496014c3"),
            source_type="market_data",
            source_name="Yahoo Finance",
            source_uri="https://query2.finance.yahoo.com/v8/finance/chart/TSLA",
            # 没有 tzinfo，是无法定位时区的 naive datetime。
            retrieved_at=datetime(2026, 7, 13, 10, 0),
            content='{"symbol":"TSLA"}',
            content_hash="d" * 64,
        )


def test_evidence_normalizes_retrieved_at_to_utc() -> None:
    """带其他时区的抓取时间应统一转换为 UTC。"""

    beijing_timezone = timezone(timedelta(hours=8))
    beijing_time = datetime(
        2026,
        7,
        13,
        18,
        0,
        tzinfo=beijing_timezone,
    )

    evidence = Evidence(
        evidence_id=UUID("696cd7fc-00cb-4dad-a986-73ee1b748350"),
        source_type="market_data",
        source_name="Yahoo Finance",
        source_uri="https://query2.finance.yahoo.com/v8/finance/chart/TSLA",
        retrieved_at=beijing_time,
        content='{"symbol":"TSLA"}',
        content_hash="e" * 64,
    )

    assert evidence.retrieved_at == datetime(
        2026,
        7,
        13,
        10,
        0,
        tzinfo=UTC,
    )
    assert evidence.retrieved_at.tzinfo is UTC


@pytest.mark.parametrize(
    "invalid_hash",
    [
        "abc",  # 长度不足64位
        "g" * 64,  # g 不是十六进制字符
        "A" * 64,  # 要求使用规范化的小写格式
    ],
)
def test_evidence_rejects_invalid_content_hash(
    invalid_hash: str,
) -> None:
    """content_hash 必须是64位小写 SHA-256 十六进制字符串。"""

    with pytest.raises(ValidationError, match="content_hash"):
        Evidence(
            evidence_id=UUID("28ccb667-7703-4dba-9f82-cd4cb3801ae0"),
            source_type="market_data",
            source_name="Yahoo Finance",
            source_uri="https://query2.finance.yahoo.com/v8/finance/chart/TSLA",
            retrieved_at=datetime(
                2026,
                7,
                13,
                10,
                30,
                tzinfo=UTC,
            ),
            content='{"symbol":"TSLA"}',
            content_hash=invalid_hash,
        )


@pytest.mark.parametrize(
    "invalid_page_number",
    [
        0,
        -1,
    ],
)
def test_evidence_rejects_non_positive_page_number(
    invalid_page_number: int,
) -> None:
    """page_number 提供时必须从1开始。"""
    with pytest.raises(ValidationError, match="page_number"):
        Evidence(
            evidence_id=UUID("52d341d0-0852-4984-bdae-5d0d2eec86c8"),
            source_type="document",
            source_name="Example Financial Report",
            source_uri="file:///documents/example-report.pdf",
            document_id="example-report",
            page_number=invalid_page_number,
            retrieved_at=datetime(
                2026,
                7,
                13,
                11,
                0,
                tzinfo=UTC,
            ),
            content="Example financial report content.",
            content_hash="f" * 64,
        )
