"""定义 Agent 查询接口的请求和响应契约。"""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from finscholar.schemas.calculator import CalculatorOutput
from finscholar.schemas.schemas_router import RouterDecision
from finscholar.schemas.yahoo_finance import (
    YahooFinanceHistoryOutput,
)


AgentExecutionStage = Literal[
    "router",
    "calculator",
    "yahoo_finance",
]


class AgentQueryRequest(BaseModel):
    """Agent 查询请求。"""

    model_config = ConfigDict(extra="forbid")

    user_query: str = Field(
        min_length=1,
        max_length=200,
    )

    @field_validator("user_query")
    @classmethod
    def normalize_user_query(cls, value: str) -> str:
        """清理并校验用户问题。"""

        normalized = value.strip()

        if not normalized:
            raise ValueError("user_query must not be empty")

        return normalized


class AgentExecutionError(BaseModel):
    """Agent 某个执行阶段产生的结构化错误。"""

    model_config = ConfigDict(extra="forbid")

    stage: AgentExecutionStage
    error_type: str = Field(min_length=1)
    message: str = Field(min_length=1)


class AgentQueryResponse(BaseModel):
    """Agent 查询的结构化响应。"""

    model_config = ConfigDict(extra="forbid")

    user_query: str
    router_decision: RouterDecision | None = None
    calculator_output: CalculatorOutput | None = None
    yahoo_finance_output: YahooFinanceHistoryOutput | None = None
    errors: list[AgentExecutionError] = Field(default_factory=list)


__all__ = [
    "AgentExecutionError",
    "AgentExecutionStage",
    "AgentQueryRequest",
    "AgentQueryResponse",
]
