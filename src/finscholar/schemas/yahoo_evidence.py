from datetime import UTC, datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

"""
描述这条数据从哪里来、什么时候取得、原始内容是什么、之后如何验证它没有被修改？
"""


class Evidence(BaseModel):
    """记录外部数据的来源、定位信息和原始内容。"""

    model_config = ConfigDict(extra="forbid")

    # 证据唯一标识，供金融数据点引用。
    evidence_id: UUID

    # 来源类型，例如 market_data、web、document。
    source_type: str

    # 用户可理解的来源名称。
    source_name: str

    # 原始数据或接口地址。
    source_uri: str

    # 文档定位字段；Yahoo API 场景可以为空。
    document_id: str | None = None
    page_number: int | None = Field(
        default=None,
        ge=1,
        description="来源文档页码；不适用时为空，提供时从1开始",
    )
    section_title: str | None = None
    chunk_id: str | None = None

    # 数据获取时间，UTC 校验。
    retrieved_at: AwareDatetime

    # 用于审计的原始内容或规范化内容。
    content: str

    # 内容哈希；后续会增加 SHA-256 格式校验。
    content_hash: str = Field(
        pattern=r"^[0-9a-f]{64}$",
        description="规范化的小写 SHA-256 十六进制字符串",
    )

    @field_validator("retrieved_at")
    @classmethod
    def normalize_retrieved_at_to_utc(
        cls,
        value: datetime,
    ) -> datetime:
        """将带时区的抓取时间统一转换为 UTC。"""

        return value.astimezone(UTC)


__all__ = ["Evidence"]
