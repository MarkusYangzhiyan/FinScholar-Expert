"""测试全局正则配置加载器。"""

from finscholar.config.reg_patterns import get_regex_pattern


def test_get_regex_pattern_loads_router_profit_pattern() -> None:
    """可以从 reg_patterns.toml 加载 router.profit 正则。"""

    pattern = get_regex_pattern("router.profit")
    match = pattern.search("利润为25，收入为100")

    assert match is not None
    assert match.group("value") == "25"