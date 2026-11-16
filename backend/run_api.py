"""PyCharm 可直接运行的 FastAPI 开发服务器入口。"""

from pathlib import Path

import uvicorn

BACKEND_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BACKEND_DIR / "src"


if __name__ == "__main__":
    uvicorn.run(
        "geophysics_agent.main:app",
        app_dir=str(SOURCE_DIR),
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
