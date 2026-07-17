"""
定义一个 QwenRouterClient 类
QwenRouterClient 是 Finscholar-Agent 和 Qwen/vLLM 模型服务之间的通信适配器
不是模型本身，不是LangGraph节点


"""

import httpx
import json 
from openai import APIError, AsyncOpenAI
from pydantic import BaseModel, ValidationError
from typing import Self, Any
from finscholar.config.settings import Settings 
from finscholar.schemas.router import RouterDecision
from finscholar.schemas.calculator import CalculatorInput
from finscholar.schemas.yahoo_finance import YahooFinanceHistoryInput
from finscholar.clients.router_client import RouterResponseError, RouterServiceError



_SYSTEM_PROMPT = (
    "你是 FinScholar Expert 的工具路由器。"
    "你必须调用且仅调用一个函数，不要直接回答用户问题。"
    "无法安全确定工具或参数时调用 Unsupported。"
    "reason 只写简短依据，不要输出思维过程。"
)


def _parameters_with_reason(
    model: type[BaseModel],
) -> dict[str,Any]:
    """在工具输入 Schema 中增加简短路由依据。"""

    schema = model.model_json_schema()
    schema['properties']['reason'] = {
        "type":str,
        "minLength":1,
        "maxLength":500,
    }
    schema['required'] = [
        *schema.get('required',[]),
        "reason",
    ]

    return schema 


_TOOLS : list[dict[str,Any]] = [
    {
        "type" : "function",
        "function":{
            "name":"Math_calculator",
            "description":"执行受限且精确的数学计算。",
            "parameters":_parameters_with_reason(
                CalculatorInput
            ),
        },
    },
    {
        "type":"function",
        "function":{
            "name":"Yahoo_Finance_Tool",
            "description":"查询结构化历史行情和金融指标。",
            "parameters":_parameters_with_reason(
                YahooFinanceHistoryInput
            ),
        },
    },
    {
        "type":"function",
        "function":{
            "name":"Unsupported",
            "description":"当前工具无法安全处理用户请求。",
            "parameters":{
                "type":"object",
                "properties":{
                    "reason":{
                        "type":str,
                        "minLength":1,
                        "maxLength":500,
                    }
                },
                "required":['reason'],
                "additionalProperties":False 
            }
        }
    }
]

class QwenRouterClient:
    """调用 OpenAI-compatible vLLM 服务完成工具路由。"""

    def __init__(self,*,client:AsyncOpenAI,model:str,enable_thinking:bool) -> None:
        self._client = client
        self._model = model
        self._enable_thinking = enable_thinking


    @classmethod
    def from_settings(cls,settings:Settings) -> Self:
        """使用统一配置创建 Qwen Router Client。"""

        timeout = httpx.Timeout(
            settings.qwen_request_timeout_seconds,
            connect = settings.http_connect_timeout_seconds

        )

        client = AsyncOpenAI(
            api_key = settings.qwen_api_key.get_secret_value(),
            base_url = settings.qwen_base_url,
            timeout = timeout,
            max_retries = settings.http_max_retries,
        )

        return  cls(
            client = client,
            model = settings.qwen_model,
            enable_thinking = settings.qwen_enable_thinking
        )
    

    async def route(
            self,
            user_query : str ,
    ) -> RouterDecision:
        """请求 Qwen 并返回结构化路由决策。"""
        
        query = user_query.strip()

        if not query:
            raise RouterResponseError("user_query can not be empty")
        
        try:
            response = await self._client.chat.completions.create(
                model = self._model, 
                messages = [
                    {
                        "role":"system",
                        "content":_SYSTEM_PROMPT,
                    },
                    {
                        "role":"user",
                        "content":query
                    }
                ],
                tools = _TOOLS,
                tool_choice = "required",
                parallel_tool_calls = False,
                temperature = 0.1,
                extra_body = {
                    "chat_template_kwargs":{
                        "enable_thinking":(
                            self._enable_thinking
                        )
                    }
                }
            )
        
        except APIError as exc:
            raise RouterServiceError("Qwen Router 服务调用失败") from exc

        tool_calls = (
            response.choices[0].message.tool_calls if len(response.choices) == 1 else None
        )

        if tool_calls is None or len(tool_calls) != 1:
            raise RouterResponseError("wen Router 必须返回一次工具调用")

        tool_call = tool_calls[0]

        return _parse_tool_call(
            name = tool_call.function.name,
            raw_arguments = tool_call.function.arguments
        )


def _parse_tool_call(
    *,
    name : str ,
    raw_arguments : str,
) -> RouterDecision:
    """将 Qwen 工具调用转换成 RouterDecision。"""

    try:
        arguments = json.loads(raw_arguments)

        if not isinstance(arguments,dict):
            raise ValueError("工具参数必须是 JSON 对象")

        reason = arguments.pop("reason",None)

        if not isinstance(reason,str) or not reason.strip():
            raise ValueError("工具参数缺少 reason")

        if name == "Math_Calculator":
            return  RouterDecision(
                selected_tool = name,
                reason = reason,
                calculator_input = (
                    CalculatorInput.model_validator(arguments)
                )
            )

        if name == "Yahoo_Finance_Tool":
            return RouterDecision(
                selected_tool = name,
                reason = reason,
                yahoo_finance_input=(
                    YahooFinanceHistoryInput.model_validator(arguments)
                )
            )
        
        if name == "Unsupported" and not arguments:
            return RouterDecision(
                selected_tool = name,
                reason = reason 
            )

        raise ValueError("Qwen 返回了未知工具或多余参数")
    
    except (TypeError, ValueError, ValidationError) as exc:
        raise RouterResponseError("Qwen Router 工具调用参数无效") from exc 







