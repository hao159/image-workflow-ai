"""Listener tạm trên cổng 1455 để bắt OAuth callback của Codex.

redirect_uri của client công khai Codex đăng ký cứng http://localhost:1455/
auth/callback, nên không thể đổi cổng. Mở server chỉ trong lúc đăng nhập, bắt
1 request callback rồi đóng.
"""
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from .providers.base import ProviderError

CALLBACK_PATH = "/auth/callback"
CALLBACK_PORT = 1455

_SUCCESS_HTML = """<!doctype html><html lang="vi"><head><meta charset="utf-8">
<title>Đăng nhập thành công</title>
<style>body{font-family:system-ui,sans-serif;background:#0f1117;color:#e6e6e6;
display:flex;height:100vh;align-items:center;justify-content:center;margin:0}
.box{text-align:center}.ok{font-size:48px}</style></head>
<body><div class="box"><div class="ok">✓</div>
<h2>Đăng nhập OpenAI thành công</h2>
<p>Bạn có thể đóng tab này và quay lại Image Workflow.</p></div></body></html>"""


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 — tên do BaseHTTPRequestHandler quy định
        parsed = urlparse(self.path)
        if parsed.path != CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return
        qs = parse_qs(parsed.query)
        self.server.auth_result = {  # type: ignore[attr-defined]
            "code": qs.get("code", [None])[0],
            "state": qs.get("state", [None])[0],
            "error": qs.get("error", [None])[0],
        }
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(_SUCCESS_HTML.encode("utf-8"))

    def log_message(self, *_args):  # tắt log ra stderr
        pass


def wait_for_callback(expected_state: str, timeout: int = 180) -> str:
    """Chờ OAuth callback trên cổng 1455, trả authorization code.

    Raise ProviderError nếu timeout / state sai / có error / cổng bận.
    """
    try:
        server = HTTPServer(("127.0.0.1", CALLBACK_PORT), _CallbackHandler)
    except OSError as e:
        raise ProviderError(
            f"Không mở được cổng {CALLBACK_PORT} (có thể Codex CLI đang đăng nhập). "
            f"Đóng tiến trình đang dùng cổng rồi thử lại. ({e})") from e

    server.auth_result = None  # type: ignore[attr-defined]
    server.timeout = 5
    deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            server.handle_request()  # xử lý 1 request (hoặc timeout 5s)
            if getattr(server, "auth_result", None):
                break
    finally:
        server.server_close()

    result = getattr(server, "auth_result", None)
    if not result:
        raise ProviderError("Hết thời gian chờ đăng nhập (không nhận được callback).")
    if result.get("error"):
        raise ProviderError(f"OpenAI từ chối đăng nhập: {result['error']}")
    if expected_state and result.get("state") != expected_state:
        raise ProviderError("State callback không khớp — hủy để tránh giả mạo, thử lại.")
    if not result.get("code"):
        raise ProviderError("Không nhận được authorization code từ OpenAI.")
    return result["code"]
