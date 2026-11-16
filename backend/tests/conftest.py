"""测试公共夹具：离线 Fake 模型与常用构造器。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from geophysics_agent.agent.llm import LLMError, UsageStats
from geophysics_agent.agent.runner import AgentRunner
from geophysics_agent.core.config import Settings
from geophysics_agent.domain.plan import PlanDraft


class FakeLLM:
    """按脚本返回方案草案的假模型，绝不访问网络。"""

    def __init__(
        self,
        drafts: list[PlanDraft] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.usage = UsageStats()
        self.calls = 0
        self._drafts = list(drafts or [])
        self._error = error

    def complete_json(self, *, system: str, user: str, schema):
        self.calls += 1
        self.usage.add(prompt_tokens=12, completion_tokens=34)
        if self._error is not None:
            raise self._error
        if not self._drafts:
            raise AssertionError("FakeLLM 没有剩余脚本，但被调用了")
        return self._drafts.pop(0)


@pytest.fixture
def settings() -> Settings:
    """不读 .env 的测试配置。"""
    return Settings(enable_llm=False, llm_temperature=0.0, planner_max_repairs=1, _env_file=None)


@pytest.fixture
def make_runner(settings: Settings) -> Callable[..., AgentRunner]:
    """构造使用 Fake 模型的 runner。"""

    def _factory(llm=None) -> AgentRunner:
        return AgentRunner(settings=settings, llm=llm)

    return _factory


__all__ = ["FakeLLM", "LLMError"]
