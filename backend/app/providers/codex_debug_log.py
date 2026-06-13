"""Ghi log debug request/response SSE cho provider codex.

Bật bằng biến môi trường CODEX_DEBUG=1 (đặt trong .env hoặc trước khi chạy
uvicorn). Mỗi lần gọi tạo 1 file trong logs/codex/ chứa: request body (base64
ảnh input đã rút gọn), HTTP status, từng event SSE nhận được kèm timestamp,
và kết quả cuối — dùng để xác định vì sao tạo ảnh treo lâu hoặc lỗi.

Token Authorization KHÔNG được ghi vào log (chỉ log body, không log headers).
"""
import copy
import json
import time
import uuid

from ..config import CODEX_DEBUG, LOGS_DIR

# Dòng SSE chứa partial_image base64 có thể dài hàng trăm KB — cắt bớt để log
# đọc được; phần đầu vẫn đủ thấy type event và message lỗi nếu có.
_MAX_SSE_LINE = 2000


class CodexDebugLog:
    """Logger 1 file / 1 request. Khi CODEX_DEBUG tắt mọi method là no-op."""

    def __init__(self):
        self.path = None
        self._fh = None
        if not CODEX_DEBUG:
            return
        log_dir = LOGS_DIR / "codex"
        log_dir.mkdir(parents=True, exist_ok=True)
        name = time.strftime("%y%m%d-%H%M%S-") + uuid.uuid4().hex[:6] + ".log"
        self.path = log_dir / name
        self._fh = open(self.path, "w", encoding="utf-8")

    def _write(self, text: str):
        if self._fh:
            self._fh.write(f"[{time.strftime('%H:%M:%S')}] {text}\n")
            self._fh.flush()  # flush ngay — log phải đọc được khi request còn treo

    def request(self, url: str, body: dict):
        self._write(f"REQUEST POST {url}\n{json.dumps(_slim_body(body), ensure_ascii=False, indent=2)}")

    def status(self, code: int):
        self._write(f"HTTP {code}")

    def sse(self, raw: str):
        if len(raw) > _MAX_SSE_LINE:
            raw = raw[:_MAX_SSE_LINE] + f"… (đã cắt, dòng gốc {len(raw)} ký tự)"
        self._write(f"SSE  {raw}")

    def tee(self, lines):
        """Bọc iterator dòng SSE: ghi log từng dòng rồi chuyển tiếp cho parser."""
        if not self._fh:
            return lines
        return self._tee(lines)

    def _tee(self, lines):
        for raw in lines:
            self.sse(raw)
            yield raw

    def done(self, msg: str):
        self._write(f"KẾT QUẢ {msg}")

    def close(self):
        if self._fh:
            self._fh.close()
            self._fh = None


def _slim_body(body: dict) -> dict:
    """Copy body, rút gọn data URL base64 của ảnh input để log không phình to."""
    slim = copy.deepcopy(body)
    for msg in slim.get("input", []):
        for part in msg.get("content", []):
            url = part.get("image_url")
            if part.get("type") == "input_image" and isinstance(url, str):
                part["image_url"] = url[:48] + f"… ({len(url)} ký tự)"
    return slim
