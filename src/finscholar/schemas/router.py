"""定义 Router 节点的结构化决策契约。

Router 负责根据用户问题选择后续工具。
当前最小版本只支持 Math_Calculator 和 Unsupported 两种结果。
后续接入 Qwen3.5 RouterClient 时，也必须输出符合本模块 Schema 的结构化结果。
"""

from typing import Literal, Self
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field, model_validator

from finscholar.schemas.calculator import CalculatorInput
from finscholar.schemas.yahoo_finance import YahooFinanceHistoryInput



ToolName = Literal[
    "Math_Calculator",
    "Yahoo_Finance_Tool",
    "Unsupported",
]

RouterBatchStatus = Literal[
    "execute",                  # 执行action中的工具
    "finalize",                 # 证据足够，进入最终答案生成
    "unsupported"               # 当前系统无法安全处理
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
    

class RouterAction(RouterDecision):
    """当前轮需要执行的一次具体工具调用"""

    action_id : UUID = Field(default_factory = uuid4)

class RouterBatch(BaseModel):
    """Router 为当前执行轮次生成的工具批次。"""

    model_config = ConfigDict(extra = "forbid")

    status : RouterBatchStatus

    reason : str  = Field(min_length = 1, max_length = 500)

    actions : list[RouterAction] = Field(default_factory = list,max_length = 7)

    @model_validator(mode = 'after')
    def validate_batch(self) -> Self:
        """校验批次状态与工具调用是否匹配。"""

        if self.status == "execute":
            if not self.actions:
                raise ValueError("execute 状态必须至少包含一个 action")
            
            if any(action.selected_tool == 'Unsupported' for action in self.actions):
                raise ValueError("execute 状态不得包含 Unsupported")
            
        elif self.actions:
            raise ValueError("finalize 或 unsupported 状态不得包含 action")

        action_ids = [action.action_id for action in self.actions]

        if len(action_ids) != len(set(action_ids)):
            raise ValueError("同一个批次中的 action_id 不得重复")
    
        return self 



__all__ = [
    "RouterAction",
    "RouterBatch",
    "RouterBatchStatus",
    "RouterDecision",
    "ToolName",
]