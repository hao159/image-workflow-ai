"""OAuth "Sign in with ChatGPT" cho Codex — dùng chung token với Codex CLI.

Token lưu ở ~/.codex/auth.json (cấu trúc Codex CLI 0.47):
    {
      "auth_mode": "chatgpt",
      "OPENAI_API_KEY": null,
      "tokens": {"id_token": JWT, "access_token": JWT,
                 "refresh_token": str, "account_id": uuid},
      "last_refresh": ISO8601
    }

Module thuần (không phụ thuộc FastAPI). Mọi I/O mạng đồng bộ qua httpx —
engine gọi provider trong thread pool nên không chặn event loop.
"""
import base64
import json
import secrets
import time
from hashlib import sha256
from urllib.parse import urlencode

import httpx

from .. import config
from .base import ProviderError

# Client công khai + endpoint của Codex CLI (redirect_uri đăng ký cứng cổng 1455).
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"
TOKEN_URL = "https://auth.openai.com/oauth/token"
REDIRECT_URI = "http://localhost:1455/auth/callback"
SCOPE = "openid profile email offline_access"
ORIGINATOR = "codex_cli_rs"
# claim trong id_token chứa account id khi đăng nhập mới
_AUTH_CLAIM = "https://api.openai.com/auth"
# refresh trước khi hết hạn để tránh 401 giữa chừng
_EXPIRY_SKEW_SECONDS = 300


# ---------- PKCE + authorize URL ----------

def generate_pkce() -> tuple[str, str]:
    """Trả về (code_verifier, code_challenge) theo PKCE S256."""
    verifier = secrets.token_urlsafe(64)
    digest = sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def build_authorize_url(code_challenge: str, state: str) -> str:
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "originator": ORIGINATOR,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


# ---------- JWT (decode payload, không verify chữ ký — chỉ đọc claim local) ----------

def _decode_jwt_payload(token: str) -> dict:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError, json.JSONDecodeError):
        return {}


def _account_id_from_id_token(id_token: str) -> str:
    claims = _decode_jwt_payload(id_token)
    auth = claims.get(_AUTH_CLAIM) or {}
    return auth.get("chatgpt_account_id", "")


# ---------- Token exchange + refresh ----------

def _post_token(data: dict) -> dict:
    try:
        resp = httpx.post(TOKEN_URL, data=data, timeout=30,
                          headers={"Content-Type": "application/x-www-form-urlencoded"})
    except httpx.HTTPError as e:
        raise ProviderError(f"Không gọi được endpoint token OpenAI: {e}") from e
    if resp.status_code >= 400:
        raise ProviderError(
            f"OpenAI từ chối yêu cầu token (HTTP {resp.status_code}). "
            "Thử đăng nhập lại trong ⚙ Cài đặt model.")
    return resp.json()


def exchange_code(code: str, code_verifier: str) -> dict:
    """Đổi authorization code lấy token (kết thúc login flow)."""
    return _post_token({
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    })


def refresh_access_token(refresh_token: str) -> dict:
    return _post_token({
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token,
        "scope": SCOPE,
    })


# ---------- auth.json I/O ----------

def read_auth() -> dict | None:
    path = config.CODEX_AUTH_FILE
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_auth(tokens: dict) -> None:
    """Ghi đè khối tokens vào auth.json, giữ nguyên các field khác."""
    path = config.CODEX_AUTH_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_auth() or {}
    existing["auth_mode"] = "chatgpt"
    existing.setdefault("OPENAI_API_KEY", None)
    existing["tokens"] = tokens
    existing["last_refresh"] = _now_iso()
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2),
                    encoding="utf-8")


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"


def store_login(token_resp: dict) -> dict:
    """Chuẩn hóa response token từ login mới → khối tokens và lưu file."""
    id_token = token_resp.get("id_token", "")
    tokens = {
        "id_token": id_token,
        "access_token": token_resp.get("access_token", ""),
        "refresh_token": token_resp.get("refresh_token", ""),
        "account_id": (token_resp.get("account_id")
                       or _account_id_from_id_token(id_token)),
    }
    write_auth(tokens)
    return tokens


# ---------- Trạng thái + access token hợp lệ ----------

def _is_expired(access_token: str) -> bool:
    exp = _decode_jwt_payload(access_token).get("exp")
    if not isinstance(exp, (int, float)):
        return True  # không đọc được hạn → coi như cần refresh
    return time.time() >= exp - _EXPIRY_SKEW_SECONDS


def status() -> dict:
    """Thông tin login an toàn để trả ra API (không lộ token)."""
    auth = read_auth()
    tokens = (auth or {}).get("tokens") or {}
    if not tokens.get("access_token"):
        return {"logged_in": False}
    return {
        "logged_in": True,
        "account_id": tokens.get("account_id", ""),
        "expired": _is_expired(tokens["access_token"]),
    }


def get_valid_access_token() -> tuple[str, str]:
    """Trả (access_token, account_id) còn hạn — tự refresh nếu cần.

    Raise ProviderError nếu chưa đăng nhập (không có gì để refresh).
    """
    auth = read_auth()
    tokens = (auth or {}).get("tokens") or {}
    access_token = tokens.get("access_token", "")
    account_id = tokens.get("account_id", "")
    if not access_token:
        raise ProviderError(
            "Chưa đăng nhập OpenAI (Codex). Mở ⚙ Cài đặt model để đăng nhập.")

    if _is_expired(access_token):
        refresh_token = tokens.get("refresh_token", "")
        if not refresh_token:
            raise ProviderError(
                "Phiên OpenAI hết hạn và không refresh được. Đăng nhập lại.")
        resp = refresh_access_token(refresh_token)
        # refresh có thể không trả refresh_token mới → giữ cái cũ
        resp.setdefault("refresh_token", refresh_token)
        resp.setdefault("account_id", account_id)
        tokens = store_login(resp)
        access_token = tokens["access_token"]
        account_id = tokens["account_id"] or account_id

    return access_token, account_id
