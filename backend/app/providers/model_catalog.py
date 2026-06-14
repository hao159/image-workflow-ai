"""Danh mục model cho dropdown ⚙ Cài đặt: list tĩnh curated + fetch live theo provider.

- STATIC: hiện ngay không cần mạng/key (nguồn chính).
- fetch_live(): gọi API provider lấy danh sách model thật (bổ sung). Lỗi → raise để
  caller (endpoint) bắt và fail mềm về static.
"""
import httpx

from .. import config

# List tĩnh curated mỗi provider (luôn có). comfyui chỉ live (checkpoint từ server).
STATIC: dict[str, list[str]] = {
    "gemini": ["gemini-2.5-flash-image", "gemini-2.5-flash", "gemini-2.5-pro"],
    "openai": ["gpt-image-1", "gpt-4o", "gpt-4o-mini"],
    "codex": ["gpt-5.5"],
    "comfyui": [],
    "fake": [],
}

# Lọc bớt danh sách openai (API trả vài trăm id) về model dùng được cho app.
_OPENAI_KEEP = ("gpt", "image", "dall")


def _fetch_gemini(api_key: str) -> list[str]:
    if not api_key:
        raise ValueError("Cần API key Gemini để tải danh sách model.")
    from google import genai
    client = genai.Client(api_key=api_key)
    names: list[str] = []
    for m in client.models.list():
        name = getattr(m, "name", "") or ""
        # SDK trả "models/gemini-2.5-flash" → bỏ tiền tố cho gọn.
        names.append(name.split("/", 1)[-1] if name else name)
    return sorted({n for n in names if n})


def _fetch_openai(api_key: str, base_url: str) -> list[str]:
    if not api_key:
        raise ValueError("Cần API key OpenAI để tải danh sách model.")
    base = (base_url or "https://api.openai.com").rstrip("/")
    r = httpx.get(f"{base}/v1/models",
                  headers={"Authorization": f"Bearer {api_key}"}, timeout=20)
    r.raise_for_status()
    ids = [m.get("id", "") for m in r.json().get("data", [])]
    keep = [i for i in ids if i and any(k in i for k in _OPENAI_KEEP)]
    return sorted(set(keep or ids))


def _fetch_comfyui(base_url: str) -> list[str]:
    base = (base_url or config.COMFYUI_URL).rstrip("/")
    r = httpx.get(f"{base}/object_info/CheckpointLoaderSimple", timeout=20)
    r.raise_for_status()
    ckpts = r.json()["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    return list(ckpts or [])


def fetch_live(provider: str, api_key: str = "", base_url: str = "") -> list[str]:
    """Danh sách model live theo provider. Raise (ValueError/httpx/SDK error) khi lỗi.

    codex/fake không list được → trả []."""
    if provider == "gemini":
        return _fetch_gemini(api_key)
    if provider == "openai":
        return _fetch_openai(api_key, base_url)
    if provider == "comfyui":
        return _fetch_comfyui(base_url)
    return []
