"""REST endpoint cho đăng nhập OpenAI qua Codex OAuth.

Mode "cả hai": /status đọc token sẵn có (vd từ `codex login`); /start chạy
full OAuth flow (mở browser, bắt callback cổng 1455) khi cần đăng nhập mới.
"""
import secrets
import webbrowser

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .codex_login_server import wait_for_callback
from .providers import openai_codex_oauth as oauth
from .providers.base import ProviderError

router = APIRouter(prefix="/api/oauth/openai", tags=["oauth"])


@router.get("/status")
def oauth_status():
    """Đã đăng nhập chưa (không trả token thô)."""
    return oauth.status()


@router.post("/start")
def oauth_start():
    """Chạy OAuth flow: mở browser → bắt callback → đổi token → lưu.

    Endpoint đồng bộ, FastAPI chạy trong thread pool nên chặn tới khi xong
    (≤180s) không ảnh hưởng event loop. Trả trạng thái login sau khi hoàn tất.
    """
    verifier, challenge = oauth.generate_pkce()
    state = secrets.token_urlsafe(24)
    url = oauth.build_authorize_url(challenge, state)

    if not webbrowser.open(url):
        # Không mở được trình duyệt (vd headless) → trả URL ngay, đừng chờ timeout.
        return JSONResponse(
            {"error": "Không tự mở được trình duyệt. Mở link này để đăng nhập rồi thử lại.",
             "authorize_url": url,
             "code": "browser_unavailable"},
            status_code=400)
    try:
        code = wait_for_callback(state, timeout=180)
        token_resp = oauth.exchange_code(code, verifier)
        oauth.store_login(token_resp)
    except ProviderError as e:
        msg = str(e)
        # Map known Codex auth errors to stable codes
        if "Chưa đăng nhập" in msg or "not logged in" in msg.lower():
            err_code = "oauth_not_logged_in"
        elif "hết hạn" in msg or "expired" in msg.lower():
            err_code = "oauth_expired"
        else:
            err_code = "provider_error"
        return JSONResponse({"error": msg, "code": err_code}, status_code=400)

    return oauth.status()
