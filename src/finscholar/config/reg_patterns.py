"""加载 FinScholar Expert 的全局正则配置。

本模块只提供通用正则加载能力，不绑定具体业务模块。
所有长期维护的正则规则统一写在项目根目录的 reg_patterns.toml 中。

业务代码通过正则项名称读取规则，例如：

    get_regex_pattern("router.profit")
    get_regex_pattern("router.revenue")
    get_regex_pattern("document.page_number")

正则项名称使用 TOML 路径表示。
例如 reg_patterns.toml 中的 [router.profit]，
对应调用名称就是 "router.profit"。
"""

import re
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from finscholar.config.settings import get_settings


class RegexPatternConfigError(ValueError):
    """正则配置文件缺失、格式错误或正则编译失败。"""


@lru_cache(maxsize=1)
def load_regex_config() -> dict[str, Any]:
    """读取并缓存 reg_patterns.toml 的原始配置。"""

    settings = get_settings()
    config_path = settings.project_root / "reg_patterns.toml"

    return load_regex_config_from_path(config_path)


def load_regex_config_from_path(config_path: Path) -> dict[str, Any]:
    """从指定路径读取正则配置文件。"""

    if not config_path.is_file():
        raise RegexPatternConfigError(
            f"正则配置文件不存在：{config_path}"
        )

    with config_path.open("rb") as file:
        raw_config = tomllib.load(file)

    if not isinstance(raw_config, dict):
        raise RegexPatternConfigError(
            "reg_patterns.toml 顶层配置格式错误"
        )

    return raw_config


@lru_cache(maxsize=256)
def get_regex_pattern(pattern_name: str) -> re.Pattern[str]:
    """按正则项名称读取并编译正则。"""

    config = load_regex_config()
    pattern_config = _find_pattern_config(
        config=config,
        pattern_name=pattern_name,
    )

    return _compile_pattern(
        pattern_name=pattern_name,
        pattern_config=pattern_config,
    )


def clear_regex_patterns_cache() -> None:
    """清空正则配置与已编译正则缓存。"""

    load_regex_config.cache_clear()
    get_regex_pattern.cache_clear()


def _find_pattern_config(
    config: Mapping[str, Any],
    pattern_name: str,
) -> Mapping[str, Any]:
    """根据点分路径查找某个正则配置项。"""

    if not pattern_name.strip():
        raise RegexPatternConfigError("正则项名称不得为空")

    parts = pattern_name.split(".")

    if any(not part for part in parts):
        raise RegexPatternConfigError(
            f"正则项名称格式错误：{pattern_name}"
        )

    current: Any = config

    for part in parts:
        if not isinstance(current, Mapping):
            raise RegexPatternConfigError(
                f"正则项路径无效：{pattern_name}"
            )

        if part not in current:
            raise RegexPatternConfigError(
                f"正则项不存在：{pattern_name}"
            )

        current = current[part]

    if not isinstance(current, Mapping):
        raise RegexPatternConfigError(
            f"正则项配置格式错误：{pattern_name}"
        )

    return current


def _compile_pattern(
    pattern_name: str,
    pattern_config: Mapping[str, Any],
) -> re.Pattern[str]:
    """读取单个正则配置项并编译。"""

    pattern = pattern_config.get("pattern")

    if not isinstance(pattern, str) or not pattern:
        raise RegexPatternConfigError(
            f"正则 {pattern_name}.pattern 必须是非空字符串"
        )

    flags = _build_regex_flags(
        pattern_name=pattern_name,
        pattern_config=pattern_config,
    )

    try:
        return re.compile(pattern, flags=flags)
    except re.error as exc:
        raise RegexPatternConfigError(
            f"正则 {pattern_name} 编译失败：{exc}"
        ) from exc


def _build_regex_flags(
    pattern_name: str,
    pattern_config: Mapping[str, Any],
) -> int:
    """根据配置生成 re.compile 使用的 flags。"""

    flag_mapping = {
        "ignore_case": re.IGNORECASE,
        "multiline": re.MULTILINE,
        "dotall": re.DOTALL,
        "verbose": re.VERBOSE,
    }

    flags = 0

    for option_name, flag_value in flag_mapping.items():
        option_value = pattern_config.get(option_name, False)

        if not isinstance(option_value, bool):
            raise RegexPatternConfigError(
                f"正则 {pattern_name}.{option_name} 必须是布尔值"
            )

        if option_value:
            flags |= flag_value

    return flags


__all__ = [
    "RegexPatternConfigError",
    "clear_regex_patterns_cache",
    "get_regex_pattern",
    "load_regex_config",
    "load_regex_config_from_path",
]