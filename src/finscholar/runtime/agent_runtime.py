from dataclasses import dataclass
from typing import Self

from langgraph.graph.state import CompiledStateGraph

from finscholar.clients.deepseek_router_client import DeepSeekRouterClient
from finscholar.clients.qwen_router_client import QwenRouterClient
from finscholar.clients.router_client import ManagedRouterClient
from finscholar.clients.yahoo_finance_client import YahooFinanceClient
from finscholar.clients.yfinance_gateway_client import YFinanceHistoryGateway
from finscholar.config.settings import Settings
from finscholar.graph.agent_graph import build_agent_graph, invoke_agent_graph
from finscholar.state.agent_state import AgentState
from finscholar.tools.yahoo_finance import YahooFinanceTool


@dataclass(slots=True)
class AgentRuntime:
    """持有并管理完整的 FinScholar Agent。"""

    _compiled_graph: CompiledStateGraph
    _router_client: ManagedRouterClient

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        """根据统一配置创建完整 Agent。"""

        if settings.router_backend == "vllm":
            router_client = QwenRouterClient.from_settings(settings)
        elif settings.router_backend == "deepseek":
            router_client = DeepSeekRouterClient.from_settings(settings)

        else:
            raise ValueError(f"不支持的 Router 后端：{settings.router_backend}")

        yahoo_gateway = YFinanceHistoryGateway(
            timeout_seconds=(settings.yfinance_request_timeout_seconds)
        )

        yahoo_client = YahooFinanceClient(gateway=yahoo_gateway)

        yahoo_tool = YahooFinanceTool(client=yahoo_client)

        compiled_graph = build_agent_graph(
            router_client=router_client, yahoo_finance_tool=yahoo_tool
        )

        return cls(_compiled_graph=compiled_graph, _router_client=router_client)

    async def invoke(
        self,
        user_query: str,
    ) -> AgentState:
        """执行一次完整 Agent 工作流。"""

        return await invoke_agent_graph(
            compiled_graph=self._compiled_graph,
            user_query=user_query,
        )

    async def close(self) -> None:
        """释放 Runtime 持有的网络资源。"""

        await self._router_client.close()


__all__ = ["AgentRuntime"]
