"""基于兼容 OpenAI 接口的工具调用 Agent。"""

import json
import uuid
from pathlib import Path

from openai import OpenAI

from geophysics_agent.agent.session_store import get_history, save_exchange
from geophysics_agent.core.config import get_settings
from geophysics_agent.domain.schemas import RecommendResponse
from geophysics_agent.knowledge.retriever import retrieve
from geophysics_agent.tools.geophysical_lookup import geophysical_param_lookup

DISCLAIMER = (
    "本结果为课程演示级辅助建议。物探解释具有多解性，必须结合现场试验、钻孔/原位测试及工程师判断。"
)
PROMPT_PATH = Path(__file__).resolve().parents[4] / "docs" / "dify_system_prompt.md"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")


def run_agent(message: str, conversation_id: str | None = None) -> RecommendResponse:
    settings = get_settings()
    if not settings.llm_api_key or not settings.llm_model:
        raise RuntimeError("未配置 LLM_API_KEY 或 LLM_MODEL，请在本机 .env 中填写。")
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url or None,
        timeout=settings.llm_timeout_seconds,
    )
    evidence = retrieve(message, settings.knowledge_top_k)
    events = [
        {
            "event": "knowledge_search",
            "status": "success" if evidence else "empty",
            "detail": f"检索到 {len(evidence)} 条课程知识",
        }
    ]
    evidence_text = json.dumps([item.model_dump() for item in evidence], ensure_ascii=False)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "geophysical_param_lookup",
                "description": "按目标、介质和埋深查询课程物探方法参数与适用性。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_name": {"type": "string"},
                        "medium": {"type": "string"},
                        "target_depth": {"type": "number"},
                    },
                    "required": ["target_name", "medium", "target_depth"],
                },
            },
        }
    ]
    current_session_id = conversation_id or str(uuid.uuid4())
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n课程检索证据：" + evidence_text},
        *get_history(current_session_id),
        {"role": "user", "content": message},
    ]
    tool_result = None
    for _ in range(3):
        completion = client.chat.completions.create(
            model=settings.llm_model, messages=messages, tools=tools, tool_choice="auto"
        )
        choice = completion.choices[0].message
        if not choice.tool_calls:
            answer = choice.content or "模型未返回有效文本，请重试。"
            break
        messages.append(choice.model_dump(exclude_none=True))
        for call in choice.tool_calls:
            args = json.loads(call.function.arguments)
            tool_result = geophysical_param_lookup(**args)
            events.append(
                {
                    "event": "parameter_tool",
                    "status": "success" if tool_result.get("ok") else "error",
                    "detail": f"查询目标：{args.get('target_name')}，介质：{args.get('medium')}，埋深：{args.get('target_depth')} m",
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                }
            )
    else:
        answer = "Agent 工具调用轮数达到上限，请补充条件后重试。"
    save_exchange(current_session_id, message, answer)
    return RecommendResponse(
        mode="llm",
        conversation_id=current_session_id,
        answer=answer,
        extracted_conditions=(
            {
                "target": tool_result.get("normalized", {}).get("target"),
                "medium": tool_result.get("normalized", {}).get("medium"),
                "depth_m": tool_result.get("normalized", {}).get("depth_m"),
                "depth_basis": tool_result.get("normalized", {}).get("depth_basis"),
            }
            if tool_result and tool_result.get("ok")
            else {}
        ),
        missing_information=(
            []
            if tool_result and tool_result.get("ok")
            else ["探测目标", "主要介质", "目标埋深（或范围）"]
        ),
        evidence=evidence,
        tool_result=tool_result,
        events=events,
        disclaimer=DISCLAIMER,
    )
