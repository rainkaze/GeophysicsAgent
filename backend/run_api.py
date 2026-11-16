"""PyCharm 可直接运行的 FastAPI 开发服务器入口。

本项目只有一个 Python 环境：``backend/.venv``（唯一 pyproject 在 ``backend/``）。
PyCharm 中把解释器指向 ``backend/.venv/Scripts/python.exe``，直接运行本文件即可，
不需要 ``uv run`` 包装，也不需要手动输入 uvicorn 长命令。

可选环境变量（不设置时使用下面的默认值）：
- ``APP_HOST``   监听地址，默认 127.0.0.1
- ``APP_PORT``   监听端口，默认 8000
- ``APP_RELOAD`` 设为 1 时开启热重载（调试断点会失效，需要自动重载时再开）
"""

import os
from pathlib import Path

import uvicorn

BACKEND_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BACKEND_DIR / "src"


if __name__ == "__main__":
    uvicorn.run(
        "geophysics_agent.main:app",
        app_dir=str(SOURCE_DIR),
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=os.getenv("APP_RELOAD", "0") == "1",
    )
