"""定义 Router 节点的结构化决策契约。

Router 负责根据用户问题选择后续工具。
当前最小版本只支持 Math_Calculator 和 Unsupported 两种结果。
后续接入 Qwen3.5 RouterClient 时，也必须输出符合本模块 Schema 的结构化结果。
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from finscholar.schemas.calculator import CalculatorInput

ToolName = Literal[
    "Math_Calculator",
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

    @model_validator(mode="after")
    def validate_tool_payload(self) -> Self:
        """校验工具选择与工具参数是否匹配。"""

        if self.selected_tool == "Math_Calculator" and self.calculator_input is None:
            raise ValueError("selected_tool 为 Math_Calculator 时，必须提供 calculator_input")

        if self.selected_tool == "Unsupported" and self.calculator_input is not None:
            raise ValueError("selected_tool 为 Unsupported 时，不得提供 calculator_input")

        return self


__all__ = [
    "RouterDecision",
    "ToolName",
]
