"""模型客户端：结构化 JSON 输出、重试、超时与用量统计。

设计要点：
- **只允许结构化输出**：调用方给出 Pydantic schema，客户端负责校验；
  校验失败会把错误信息回灌给模型重试，而不是让脏数据流进业务层。
- **失败可降级**：所有异常统一包装为 ``LLMError``，由上层决定回退到规则方案。
- **用量可观测**：token 与调用次数随响应返回，便于展示与成本控制。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Protocol, TypeVar

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from pydantic import BaseModel, ValidationError

from geophysics_agent.core.config import Settings

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMError(RuntimeError):
    """模型调用失败（未配置、网络错误、输出不合法且重试耗尽）。"""


@dataclass
class UsageStats:
    """累计用量。"""

    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def add(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.calls += 1
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens


class LLMClient(Protocol):
    """模型客户端协议；测试用 Fake 实现即可替换。"""

    usage: UsageStats

    def complete_json(self, *, system: str, user: str, schema: type[SchemaT]) -> SchemaT: ...


class OpenAICompatibleLLM:
    """兼容 OpenAI Chat Completions 协议的实现（DeepSeek 等）。"""

    def __init__(self, settings: Settings) -> None:
        if not settings.llm_api_key or not settings.llm_model:
            raise LLMError("未配置 LLM_API_KEY 或 LLM_MODEL，请在本机 .env 中填写")
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or None,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
        )
        self.usage = UsageStats()

    def complete_json(self, *, system: str, user: str, schema: type[SchemaT]) -> SchemaT:
        """请求模型并返回校验后的结构化对象。"""
        attempts = max(0, self._settings.llm_max_retries) + 1
        correction = ""
        last_error: Exception | None = None

        for attempt in range(attempts):
            payload = (
                user if not correction else f"{user}\n\n【上一次输出不合法，请修正】\n{correction}"
            )
            try:
                completion = self._client.chat.completions.create(
                    model=self._settings.llm_model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": payload},
                    ],
                    temperature=self._settings.llm_temperature,
                    response_format={"type": "json_object"},
                )
            except (APITimeoutError, APIConnectionError, APIStatusError) as exc:
                last_error = exc
                if attempt < attempts - 1:
                    time.sleep(0.8 * (attempt + 1))
                    continue
                raise LLMError(f"模型服务调用失败：{type(exc).__name__}") from exc

            usage = getattr(completion, "usage", None)
            self.usage.add(
                int(getattr(usage, "prompt_tokens", 0) or 0),
                int(getattr(usage, "completion_tokens", 0) or 0),
            )

            content = completion.choices[0].message.content or ""
            try:
                return schema.model_validate(json.loads(content))
            except json.JSONDecodeError as exc:
                last_error = exc
                correction = (
                    f"返回内容不是合法 JSON（{exc.msg}）。请只输出一个 JSON 对象，不要使用代码块。"
                )
            except ValidationError as exc:
                last_error = exc
                correction = "输出不满足 schema：" + "；".join(
                    f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                    for error in exc.errors()[:4]
                )

        raise LLMError(f"模型输出无法解析为 {schema.__name__}：{last_error}")


def build_llm(settings: Settings) -> LLMClient | None:
    """按配置构造客户端；未配置或禁用时返回 ``None``（触发规则方案降级）。"""
    if not settings.enable_llm:
        return None
    try:
        return OpenAICompatibleLLM(settings)
    except LLMError:
        return None
