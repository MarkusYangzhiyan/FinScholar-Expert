"""手动验证 yfinance 的新闻搜索、股票新闻和历史行情调用。"""

from collections.abc import Callable
from pprint import pprint
from typing import Any

import pandas as pd
import yfinance as yf


def search_tesla_news() -> list[dict[str, Any]]:
    """按公司关键词搜索 Yahoo Finance 新闻。返回新闻列表"""

    result = yf.Search(
        "Apple",
        max_results=0,  # 证券代码搜索
        news_count=10,  # 请求新闻数量，不保证最终一定返回这么多条
        lists_count=0,  # Yahoo Finance 推荐列表
        include_cb=False,  # 搜索关键词相关的公司分类信息
        recommended=0,  # 控制推荐内容的返回数量
        timeout=30,  # 主搜索请求最多等待
        raise_errors=True,
    )
    return result.news


def get_tsla_news() -> list[dict[str, Any]]:
    """获取与 TSLA 股票直接关联的新闻。"""

    ticker = yf.Ticker("TSLA")
    return ticker.get_news(count=5, tab="news")


def get_tsla_history() -> pd.DataFrame:
    """获取 TSLA 最近一个月的日线行情。"""

    ticker = yf.Ticker("TSLA")
    return ticker.history(
        period="1mo",
        interval="1d",
        timeout=10,
    )


def show_news(
    title: str,
    loader: Callable[[], list[dict[str, Any]]],
) -> bool:
    """执行新闻请求并展示前两条原始数据。"""

    print(f"\n{'=' * 20} {title} {'=' * 20}")

    try:
        news = loader()
    except Exception as exc:
        print(f"调用失败：{type(exc).__name__}: {exc}")
        return False

    print(f"返回新闻数量：{len(news)}")
    pprint(news[:2], sort_dicts=False)
    return bool(news)


def show_history() -> bool:
    """执行历史行情请求并展示最近五个交易日。"""

    print(f"\n{'=' * 20} TSLA 最近一个月行情 {'=' * 20}")

    try:
        history = get_tsla_history()
    except Exception as exc:
        print(f"调用失败：{type(exc).__name__}: {exc}")
        return False

    if history.empty:
        print("Yahoo Finance 返回了空行情。")
        return False

    print(f"返回记录数：{len(history)}")
    print(history.tail(5).to_string())
    return True


def main() -> None:
    """依次运行三个真实网络调用。"""

    yf.config.network.retries = 1
    yf.config.debug.hide_exceptions = False

    results = [
        show_news("关键词 Tesla 新闻", search_tesla_news),
        show_news("TSLA 股票新闻", get_tsla_news),
        show_history(),
    ]

    success_count = sum(results)
    print(f"\n验证完成：{success_count}/3 项成功。")


if __name__ == "__main__":
    main()
