"""定义 Router 节点的结构化决策契约。

Router 负责根据用户问题选择后续工具。
当前最小版本只支持 Math_Calculator 和 Unsupported 两种结果。
后续接入 Qwen3.5 RouterClient 时，也必须输出符合本模块 Schema 的结构化结果。
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from finscholar.schemas.calculator import CalculatorInput
from finscholar.schemas.yahoo_finance import YahooFinanceHistoryInput



ToolName = Literal[
    "Math_Calculator",
    "Yahoo_Finance_Tool",
    "Unsupported",
]


class RouterDecision(BaseModel):
    """Router 的结构化决策结果。"""

    model_config = ConfigDict(extra="forbid")

    # 当前选择的工具。Unsupported 表示当前 Router 无法安全处理该问题。
    selected_tool: ToolName

    # 选择该工具的原因，后续会写入审计或调试日志。
    reason: str = Field(
        min_length=1,
        max_length=500,
    )

    # 当 selected_tool 为 Math_Calculator 时必须提供。
    calculator_input: CalculatorInput | None = None

    # 当 selected_tool 为 Yahoo_Finance_Tool 时必须提供。
    yahoo_finance_input: YahooFinanceHistoryInput | None = None

    @model_validator(mode="after")
    def validate_tool_payload(self) -> Self:
        """校验工具选择和工具参数是否匹配。"""

        if self.selected_tool == "Math_Calculator":
            if self.calculator_input is None:
                raise ValueError(
                    "选择 Math_Calculator 时必须提供 calculator_input"
                )

            if self.yahoo_finance_input is not None:
                raise ValueError(
                    "选择 Math_Calculator 时不得提供 yahoo_finance_input"
                )

        elif self.selected_tool == "Yahoo_Finance_Tool":
            if self.yahoo_finance_input is None:
                raise ValueError(
                    "选择 Yahoo_Finance_Tool 时必须提供 "
                    "yahoo_finance_input"
                )

            if self.calculator_input is not None:
                raise ValueError(
                    "选择 Yahoo_Finance_Tool 时不得提供 "
                    "calculator_input"
                )

        elif (
            self.calculator_input is not None
            or self.yahoo_finance_input is not None
        ):
            raise ValueError(
                "选择 Unsupported 时不得提供任何工具参数"
            )

        return self


__all__ = [
    "RouterDecision",
    "ToolName",
]
