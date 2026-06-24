"""Kiểm tra bản mới trên GitHub Releases (OTA dạng notify-only).

App gọi GET /api/update-check lúc khởi động → so version đang chạy (config.APP_VERSION)
với release MỚI NHẤT trên GitHub. Chỉ THÔNG BÁO + link tải; KHÔNG tự cập nhật để né
rắc rối khóa file .exe trên Windows và Gatekeeper macOS với bản chưa ký.

Fail mềm: không có mạng / GitHub lỗi → trả error chứ không làm hỏng app.
"""
import re
import time

import httpx

from . import config

# Cache kết quả thành công để không spam GitHub API (giới hạn 60 req/h/IP ẩn danh).
_CACHE_TTL = 3600.0  # giây
_cache = {"at": 0.0, "data": None}

_GITHUB_API = "https://api.github.com/repos/{repo}/releases/latest"


def _parse_version(text: str) -> tuple[int, ...]:
    """'v0.2.0' / '0.2.0-beta' → (0, 2, 0) để so sánh số học. Bỏ tiền tố 'v'/hậu tố."""
    nums = re.findall(r"\d+", text or "")
    return tuple(int(n) for n in nums) or (0,)


def _is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


async def check_for_update(force: bool = False) -> dict:
    """Trả {current, latest, update_available, url, error}. Luôn HTTP 200 (fail mềm)."""
    now = time.monotonic()
    if not force and _cache["data"] is not None and now - _cache["at"] < _CACHE_TTL:
        return _cache["data"]

    current = config.APP_VERSION
    result = {
        "current": current,
        "latest": None,
        "update_available": False,
        "url": None,
        "error": None,
    }
    try:
        url = _GITHUB_API.format(repo=config.GITHUB_REPO)
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers={"Accept": "application/vnd.github+json"})
        if resp.status_code == 200:
            data = resp.json()
            tag = (data.get("tag_name") or "").strip()
            result["latest"] = tag.lstrip("v") or None
            result["url"] = data.get("html_url")
            result["update_available"] = bool(tag) and _is_newer(tag, current)
        elif resp.status_code == 404:
            result["error"] = "no_release"  # repo chưa có release nào
        else:
            result["error"] = f"http_{resp.status_code}"
    except Exception as e:  # noqa: BLE001 — offline / DNS / timeout: app vẫn chạy
        result["error"] = str(e)

    # Chỉ cache khi tra cứu thành công → lần sau (vd vừa có mạng lại) còn thử lại.
    if result["error"] is None:
        _cache["at"], _cache["data"] = now, result
    return result
