"""
定义一个 QwenRouterClient 类
QwenRouterClient 是 Finscholar-Agent 和 Qwen/vLLM 模型服务之间的通信适配器
不是模型本身，不是LangGraph节点


"""

from typing import Self

import httpx
from openai import APIError, AsyncOpenAI

from finscholar.clients.client_router import RouterResponseError, RouterServiceError
from finscholar.config.settings import Settings
from finscholar.routing.router_function_calling import (
    ROUTER_SYSTEM_PROMPT,
    ROUTER_TOOLS,
    parse_router_tool_calls,
)
from finscholar.schemas.schemas_router import RouterBatch, RouterContext


class QwenRouterClient:
    """调用 OpenAI-compatible vLLM 服务完成工具路由。"""

    def __init__(self, *, client: AsyncOpenAI, model: str, enable_thinking: bool) -> None:
        self._client = client
        self._model = model
        self._enable_thinking = enable_thinking

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        """使用统一配置创建 Qwen Router Client。"""

        timeout = httpx.Timeout(
            settings.qwen_request_timeout_seconds, connect=settings.http_connect_timeout_seconds
        )

        client = AsyncOpenAI(
            api_key=settings.qwen_api_key.get_secret_value(),
            base_url=settings.qwen_base_url,
            timeout=timeout,
            max_retries=settings.http_max_retries,
        )

        return cls(
            client=client, model=settings.qwen_model, enable_thinking=settings.qwen_enable_thinking
        )

    async def close(self) -> None:
        """关闭底层 HTTP 连接。"""

        await self._client.close()

    async def route(
        self,
        context: RouterContext,
    ) -> RouterBatch:
        """请求 Qwen 并返回本轮结构化路由批次。"""

        user_query = context.user_query.strip()

        if not user_query:
            raise RouterResponseError("user_query must not be empty")

        normalized_context = context.model_copy(update={"user_query": user_query})

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": ROUTER_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": normalized_context.model_dump_json(exclude_none=True),
                    },
                ],
                tools=ROUTER_TOOLS,
                tool_choice="required",
                parallel_tool_calls=True,
                temperature=0,
                extra_body={"chat_template_kwargs": {"enable_thinking": self._enable_thinking}},
            )

        except APIError as exc:
            raise RouterServiceError("Qwen Router 服务调用失败") from exc

        if len(response.choices) != 1:
            raise RouterResponseError("Qwen Router 必须返回一个响应选项")

        tool_calls = response.choices[0].message.tool_calls

        if not tool_calls:
            raise RouterResponseError("Qwen Router 必须返回至少一次工具调用")

        return parse_router_tool_calls(
            tool_calls=[
                (
                    tool_call.function.name,
                    tool_call.function.arguments,
                )
                for tool_call in tool_calls
            ]
        )


__all__ = ["QwenRouterClient"]
