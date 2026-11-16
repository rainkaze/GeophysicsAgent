"""进程内短期会话上下文；服务重启后自动清空。"""

from collections import OrderedDict
from threading import Lock

MAX_SESSIONS = 100
MAX_MESSAGES_PER_SESSION = 12
_sessions: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
_lock = Lock()


def get_history(session_id: str) -> list[dict[str, str]]:
    with _lock:
        return [message.copy() for message in _sessions.get(session_id, [])]


def save_exchange(session_id: str, user_message: str, assistant_message: str) -> None:
    with _lock:
        history = _sessions.setdefault(session_id, [])
        history.extend(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message},
            ]
        )
        del history[:-MAX_MESSAGES_PER_SESSION]
        _sessions.move_to_end(session_id)
        while len(_sessions) > MAX_SESSIONS:
            _sessions.popitem(last=False)
