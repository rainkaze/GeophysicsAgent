"""会话记忆：保存每个对话已确认的场地条件，支撑多轮追问。

存的是**结构化条件**而不是聊天记录，原因：
- 追问场景只需要"已确认事实"，不需要重放对话；
- 条件可合并、可校验、可测试，比拼接历史消息稳定；
- 也避免把上一轮可能错误的模型文本再次喂给模型。
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field

from geophysics_agent.domain.conditions import SiteConditions


@dataclass
class SessionState:
    """一个会话的已确认状态。"""

    conversation_id: str
    conditions: SiteConditions = field(default_factory=SiteConditions)
    turns: int = 0
    last_primary: str | None = None
    updated_at: float = field(default_factory=time.time)


class SessionStore:
    """线程安全的会话存储，带 TTL 与容量上限。"""

    def __init__(self, max_sessions: int = 200, ttl_minutes: int = 120) -> None:
        self._max_sessions = max(1, max_sessions)
        self._ttl_seconds = max(1, ttl_minutes) * 60
        self._sessions: OrderedDict[str, SessionState] = OrderedDict()
        self._lock = threading.Lock()

    def get_or_create(self, conversation_id: str) -> SessionState:
        """取出会话；不存在则新建。"""
        with self._lock:
            self._purge_locked()
            state = self._sessions.get(conversation_id)
            if state is None:
                state = SessionState(conversation_id=conversation_id)
                self._sessions[conversation_id] = state
            else:
                self._sessions.move_to_end(conversation_id)
            return state

    def save(self, state: SessionState) -> None:
        """写回会话状态并刷新时间戳。"""
        with self._lock:
            state.updated_at = time.time()
            self._sessions[state.conversation_id] = state
            self._sessions.move_to_end(state.conversation_id)
            self._purge_locked()

    def clear(self, conversation_id: str) -> None:
        """清空指定会话（前端"新对话"按钮使用）。"""
        with self._lock:
            self._sessions.pop(conversation_id, None)

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def _purge_locked(self) -> None:
        """清理过期与超量会话；调用方必须已持有锁。"""
        now = time.time()
        expired = [
            key
            for key, state in self._sessions.items()
            if now - state.updated_at > self._ttl_seconds
        ]
        for key in expired:
            self._sessions.pop(key, None)
        while len(self._sessions) > self._max_sessions:
            self._sessions.popitem(last=False)
