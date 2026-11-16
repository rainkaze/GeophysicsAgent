"""工具模块：物探参数查表（Agent 唯一可调用的工具）。

工具名：geophysical_param_lookup
输入：target_name（探测目标）、medium（介质类型）、target_depth（目标埋深，m）
输出：JSON，包含 GPR / DC / 面波 / 磁法 / FDEM / DAS 六种方法的
      最大探测深度、纵向分辨率、相对成本、关键限制，以及适用性判定。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from geophysics_agent.tools.param_table import (
    MEDIUM_ALIASES,
    TARGET_ALIASES,
    build_lookup_result,
    coerce_depth,
    normalize_medium,
    normalize_target,
)

TOOL_NAME = "geophysical_param_lookup"

# OpenAI / DeepSeek 兼容的函数调用描述（function calling schema）
TOOL_SCHEMA_LIST: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": TOOL_NAME,
            "description": (
                "查询工程物探参数表。给定探测目标、介质类型和目标埋深，"
                "返回探地雷达 GPR、直流电阻率 DC、面波、磁法、频域电磁 FDEM、"
                "分布式光纤声学 DAS 六种方法的最大探测深度、纵向分辨率、"
                "相对成本（低/中/高）、关键限制条件，以及是否满足深度要求的判定。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target_name": {
                        "type": "string",
                        "description": "探测目标，例如：污染羽、地下管线、溶洞、含水层、UXO未爆物、土层液化、工程勘察",
                    },
                    "medium": {
                        "type": "string",
                        "description": "介质类型，例如：黏土、砂土、填土、灰岩、软土、粉土、基岩",
                    },
                    "target_depth": {
                        "type": "number",
                        "description": "目标埋深，单位 m；埋深为范围时取上限（最不利情况）",
                    },
                },
                "required": ["target_name", "medium", "target_depth"],
            },
        },
    }
]


@dataclass
class ToolCallResult:
    """一次工具调用的结果，便于 Agent 判断成功/失败。"""

    ok: bool
    payload: dict[str, Any]
    json_text: str
    error: str | None = None


def _error_payload(message: str, **extra: Any) -> dict[str, Any]:
    """统一的失败返回结构：模型看到后可以自行修正参数重试。"""
    payload: dict[str, Any] = {"ok": False, "tool": TOOL_NAME, "error": message}
    payload.update(extra)
    return payload


def _supported_values() -> dict[str, list[str]]:
    return {
        "target_name": list(TARGET_ALIASES.keys()),
        "medium": list(MEDIUM_ALIASES.keys()),
    }


def geophysical_param_lookup(target_name: str, medium: str, target_depth: Any) -> dict[str, Any]:
    """物探参数查表工具的实现。

    参数
    ----
    target_name : 探测目标（支持同义词，如"未爆物""地下管道"）
    medium      : 介质类型（支持同义词，如"粉质黏土""石灰岩"）
    target_depth: 目标埋深（m），允许数字或 "5~12 m" 这类范围（取上限）

    返回
    ----
    dict : 六种方法的参数 + 适用性 + 汇总提示；输入非法时返回 ok=False 的错误 JSON
    """
    # 1) 目标归一化
    target = normalize_target(str(target_name))
    if target is None:
        return _error_payload(
            f"无法识别的探测目标 target_name='{target_name}'",
            supported=_supported_values(),
            hint="请从支持列表中选择，或使用同义描述（如“未爆物”“地下管道”）。",
        )

    # 2) 介质归一化
    medium_name = normalize_medium(str(medium))
    if medium_name is None:
        return _error_payload(
            f"无法识别的介质类型 medium='{medium}'",
            supported=_supported_values(),
            hint="请使用 黏土/砂土/填土/灰岩/软土/粉土/基岩 之一。",
        )

    # 3) 埋深校验（范围取上限）
    try:
        depth = coerce_depth(target_depth)
    except ValueError as exc:
        return _error_payload(str(exc), hint='target_depth 请传数字（单位 m），例如 12 或 "5~12"。')

    # 4) 查表并组装结果
    return build_lookup_result(
        target=target,
        medium=medium_name,
        depth=depth,
        raw_input={"target_name": target_name, "medium": medium, "target_depth": target_depth},
    )


def execute_tool_call(name: str, raw_arguments: str) -> ToolCallResult:
    """执行模型发起的工具调用，任何异常都转换成可读的错误 JSON。"""
    if name != TOOL_NAME:
        payload = _error_payload(f"未知工具 '{name}'，本 Agent 只提供 {TOOL_NAME}")
        return ToolCallResult(
            False, payload, json.dumps(payload, ensure_ascii=False), payload["error"]
        )

    try:
        arguments = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError as exc:
        payload = _error_payload(f"工具参数不是合法 JSON：{exc.msg}")
        return ToolCallResult(
            False, payload, json.dumps(payload, ensure_ascii=False), payload["error"]
        )

    if not isinstance(arguments, dict):
        payload = _error_payload("工具参数必须是 JSON 对象（包含 target_name/medium/target_depth）")
        return ToolCallResult(
            False, payload, json.dumps(payload, ensure_ascii=False), payload["error"]
        )

    allowed = {"target_name", "medium", "target_depth"}
    missing = [key for key in allowed if key not in arguments]
    if missing:
        payload = _error_payload(
            f"缺少必需参数：{', '.join(missing)}", received=list(arguments.keys())
        )
        return ToolCallResult(
            False, payload, json.dumps(payload, ensure_ascii=False), payload["error"]
        )

    try:
        payload = geophysical_param_lookup(
            target_name=arguments["target_name"],
            medium=arguments["medium"],
            target_depth=arguments["target_depth"],
        )
    except (ValueError, TypeError, KeyError) as exc:
        payload = _error_payload(f"工具执行异常：{exc}")
        return ToolCallResult(
            False, payload, json.dumps(payload, ensure_ascii=False), payload["error"]
        )

    ok = bool(payload.get("ok", False))
    error = None if ok else str(payload.get("error", "工具返回失败"))
    return ToolCallResult(ok, payload, json.dumps(payload, ensure_ascii=False, indent=2), error)
