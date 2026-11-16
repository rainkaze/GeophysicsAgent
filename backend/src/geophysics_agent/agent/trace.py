"""执行轨迹记录：把 agent 每一步的耗时与结论沉淀下来。

轨迹既是前端时间线的数据源，也是复盘"为什么给出这个方案"的唯一依据。
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Literal

from geophysics_agent.domain.schemas import TraceStep

Status = Literal["ok", "warn", "error", "skipped"]


@dataclass
class _Handle:
    """在 ``with`` 块内可修改的单步状态。"""

    step: str
    status: Status = "ok"
    detail: str = ""

    def warn(self, detail: str) -> None:
        self.status = "warn"
        self.detail = detail

    def fail(self, detail: str) -> None:
        self.status = "error"
        self.detail = detail


@dataclass
class TraceRecorder:
    """按顺序记录 agent 的每一步。"""

    steps: list[TraceStep] = field(default_factory=list)

    @contextmanager
    def step(self, name: str, detail: str = "") -> Iterator[_Handle]:
        """记录一步的耗时；块内抛异常时自动标记为 error。"""
        handle = _Handle(step=name, detail=detail)
        started = time.perf_counter()
        try:
            yield handle
        except Exception as exc:
            handle.status = "error"
            handle.detail = f"{handle.detail}｜异常：{exc}".strip("｜")
            raise
        finally:
            elapsed = int((time.perf_counter() - started) * 1000)
            self.steps.append(
                TraceStep(
                    step=handle.step,
                    status=handle.status,
                    detail=handle.detail or "-",
                    duration_ms=elapsed,
                )
            )

    def add(self, name: str, status: Status, detail: str, duration_ms: int = 0) -> None:
        """直接追加一步（用于已经完成的动作）。"""
        self.steps.append(
            TraceStep(step=name, status=status, detail=detail, duration_ms=duration_ms)
        )
