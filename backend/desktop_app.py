"""Điểm vào bản đóng gói desktop: bật uvicorn + mở trình duyệt. KHÔNG --reload.

Khác run_server.py (dùng cho dev): script này chọn cổng trống nếu 8000 bận, tự mở
trình duyệt tới SPA, và là entry mà PyInstaller đóng gói thành ImageWorkflow.exe.

GIỮ NGUYÊN ws_ping_interval/ws_ping_timeout=None: pong WS qua proxy/đời thực không
về kịp khi node AI chạy lâu (>40s) → uvicorn tự ngắt "keepalive ping timeout" làm
ảnh sinh xong không hiện. (Xem run_server.py.) CLI uvicorn không truyền được None
nên phải qua Python API.
"""
import socket
import threading
import webbrowser
from pathlib import Path

import uvicorn


def _free_port(preferred: int = 8000) -> int:
    """Trả về `preferred` nếu còn trống, ngược lại xin OS một cổng trống bất kỳ."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s2:
        s2.bind(("127.0.0.1", 0))
        return s2.getsockname()[1]


def main() -> None:
    port = _free_port(8000)
    url = f"http://127.0.0.1:{port}"
    # Server chạy blocking ở main thread → mở trình duyệt sau một nhịp ngắn.
    # Mở hơi sớm cũng không sao: trình duyệt tự nạp lại khi uvicorn sẵn sàng.
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(
        "app.main:app",
        app_dir=str(Path(__file__).resolve().parent),  # chạy từ đâu cũng được
        host="127.0.0.1",
        port=port,
        ws_ping_interval=None,  # tắt keepalive ping (0 KHÔNG tắt) — xem docstring
        ws_ping_timeout=None,
    )


if __name__ == "__main__":
    main()
