"""Khởi động backend với cấu hình WebSocket phù hợp node AI chạy lâu.

PHẢI dùng script này thay vì gọi `uvicorn` CLI trực tiếp: cần TẮT hẳn keepalive
ping WS (ws_ping_interval=None) — pong đi qua proxy Vite không về kịp khiến
uvicorn tự ngắt kết nối "keepalive ping timeout" sau ~40s im lặng khi node AI
chạy lâu → ảnh sinh xong nhưng không hiển thị lên node. CLI uvicorn không
truyền được None (websockets check `ping_interval is None`, nên `--ws-ping-interval 0`
vẫn bật ping) — chỉ tắt được qua Python API như dưới đây.

Chạy:  backend\\.venv\\Scripts\\python backend\\run_server.py [--reload]
"""
import sys
from pathlib import Path

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        app_dir=str(Path(__file__).resolve().parent),  # chạy từ đâu cũng được
        host="127.0.0.1",
        port=8000,
        reload="--reload" in sys.argv,
        ws_ping_interval=None,  # tắt keepalive ping (0 KHÔNG tắt)
        ws_ping_timeout=None,
    )
