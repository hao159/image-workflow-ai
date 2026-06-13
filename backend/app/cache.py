"""Cache output node trên đĩa — sống qua `--reload`, tái dùng output đã sinh.

Layout (dưới `config.CACHE_DIR`):
  nodes/{key}.json  — manifest: outputs (image→blob sha, text→inline) + preview base64
  blobs/{sha}.bin   — bytes ảnh, dedupe theo content-sha

Auto-trim: sau mỗi `save()`, nếu tổng blobs vượt `CACHE_MAX_BYTES` → xóa blob cũ
nhất theo mtime (`_evict_if_needed`). `load()` `os.utime` blob được đọc → blob đang
dùng "trẻ lại" (xấp xỉ LRU). Manifest mồ côi (trỏ blob đã evict) → `load` trả None
= cache miss an toàn, không crash.

Test override đường dẫn / ngưỡng bằng cách GÁN `cache.CACHE_DIR` / `cache.CACHE_MAX_BYTES`
— các hàm đọc động hai biến module này (KHÔNG bind hằng lúc import).
"""
import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from typing import Optional, Union

from . import config

CACHE_DIR = config.CACHE_DIR
CACHE_MAX_BYTES = config.CACHE_MAX_BYTES


@dataclass
class CachedResult:
    outputs: dict[str, Union[bytes, str]]  # handle -> bytes (ảnh) | str (text)
    preview: Optional[str]                 # data-URL preview hoặc None


def _dirs() -> tuple:
    """(nodes_dir, blobs_dir) dưới CACHE_DIR hiện tại; tạo nếu thiếu."""
    nodes = CACHE_DIR / "nodes"
    blobs = CACHE_DIR / "blobs"
    nodes.mkdir(parents=True, exist_ok=True)
    blobs.mkdir(parents=True, exist_ok=True)
    return nodes, blobs


def load(key: str) -> Optional[CachedResult]:
    """Đọc cache theo key. Trả None nếu thiếu manifest hoặc thiếu blob (đã evict)."""
    nodes, blobs = _dirs()
    manifest_path = nodes / f"{key}.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    outputs: dict[str, Union[bytes, str]] = {}
    for handle, spec in manifest.get("outputs", {}).items():
        if spec.get("dtype") == "image":
            blob_path = blobs / f"{spec['blob']}.bin"
            if not blob_path.exists():
                return None  # blob bị evict → coi như miss (an toàn)
            outputs[handle] = blob_path.read_bytes()
            try:
                os.utime(blob_path, None)  # touch mtime → LRU thô
            except OSError:
                pass
        else:
            outputs[handle] = spec.get("value", "")
    return CachedResult(outputs=outputs, preview=manifest.get("preview"))


def save(key: str, outputs: dict, preview: Optional[str]) -> None:
    """Ghi outputs + preview vào cache. Ảnh ghi ra blob dedupe; text inline."""
    nodes, blobs = _dirs()
    manifest_outputs: dict[str, dict] = {}
    for handle, value in outputs.items():
        if isinstance(value, bytes):
            sha = hashlib.sha256(value).hexdigest()
            blob_path = blobs / f"{sha}.bin"
            if not blob_path.exists():
                blob_path.write_bytes(value)
            manifest_outputs[handle] = {"dtype": "image", "blob": sha}
        else:
            manifest_outputs[handle] = {"dtype": "text", "value": str(value)}
    manifest = {"outputs": manifest_outputs, "preview": preview}
    (nodes / f"{key}.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    _evict_if_needed()


def clear() -> None:
    """Xóa sạch cache rồi tạo lại thư mục rỗng."""
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR, ignore_errors=True)
    _dirs()


def _evict_if_needed() -> None:
    """Tổng blobs > CACHE_MAX_BYTES → xóa blob cũ nhất (mtime nhỏ nhất) tới khi vừa."""
    _, blobs = _dirs()
    files = []
    total = 0
    for p in blobs.glob("*.bin"):
        try:
            st = p.stat()
        except OSError:
            continue
        files.append((p, st.st_mtime, st.st_size))
        total += st.st_size
    if total <= CACHE_MAX_BYTES:
        return
    files.sort(key=lambda f: f[1])  # cũ nhất trước
    for path, _mtime, size in files:
        if total <= CACHE_MAX_BYTES:
            break
        try:
            path.unlink()
            total -= size
        except OSError:
            pass
