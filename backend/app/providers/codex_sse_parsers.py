"""Parse SSE stream của ChatGPT Responses API (endpoint codex/responses).

Hai parser: ảnh (tool image_generation → base64 PNG) và text (message →
output_text). Cả hai chung vòng đọc event + deadline tổng.
"""
import base64
import json
import time

from .base import ProviderError


def _iter_events(lines, deadline_s: float | None, missing_what: str):
    """Decode từng event JSON từ SSE stream.

    `deadline_s`: trần thời gian cho cả stream — hết hạn raise lỗi thay vì
    để node chạy vô hạn khi server cứ stream event mà không ra kết quả.
    """
    start = time.monotonic()
    for raw in lines:
        if deadline_s is not None and time.monotonic() - start > deadline_s:
            raise ProviderError(
                f"OpenAI (Codex) chạy quá {int(deadline_s)}s chưa trả {missing_what} — đã hủy. "
                "Bật CODEX_DEBUG=1 để ghi log request/response rồi thử lại.")
        if not raw or not raw.startswith("data:"):
            continue
        payload = raw[len("data:"):].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            yield json.loads(payload)
        except json.JSONDecodeError:
            continue


def _raise_if_error_event(ev: dict, what: str) -> None:
    if ev.get("type", "") in ("response.failed", "error", "response.error"):
        msg = (ev.get("response") or ev).get("error") or ev.get("message") or ev
        raise ProviderError(f"OpenAI (Codex) báo lỗi sinh {what}: {msg}")


def _parse_image_from_sse(lines, deadline_s: float | None = None) -> bytes:
    """Đọc SSE stream, trả PNG bytes của ảnh sinh ra.

    Chỉ nhận ảnh hoàn chỉnh: `response.output_item.done` (item.type ==
    image_generation_call, item.result base64) hoặc quét response.completed.
    KHÔNG dùng partial_image làm kết quả (chỉ là preview dở dang) — stream đứt
    giữa chừng raise lỗi rõ thay vì trả ảnh mờ âm thầm.
    """
    for ev in _iter_events(lines, deadline_s, "ảnh"):
        etype = ev.get("type", "")
        if etype == "response.output_item.done":
            item = ev.get("item") or {}
            if item.get("type") == "image_generation_call" and item.get("result"):
                return base64.b64decode(item["result"])
        elif etype in ("response.completed", "response.done"):
            for item in (ev.get("response") or {}).get("output", []):
                if item.get("type") == "image_generation_call" and item.get("result"):
                    return base64.b64decode(item["result"])
        else:
            _raise_if_error_event(ev, "ảnh")
    raise ProviderError(
        "OpenAI (Codex) không trả về ảnh hoàn chỉnh (stream kết thúc sớm). "
        "Thử lại; nếu lặp lại, bật CODEX_DEBUG=1 để ghi log request/response.")


def _message_text(item: dict) -> str:
    parts = item.get("content") or []
    return "".join(p.get("text", "") for p in parts if p.get("type") == "output_text")


def _parse_text_from_sse(lines, deadline_s: float | None = None) -> str:
    """Đọc SSE stream, trả text của message đầu tiên có nội dung."""
    for ev in _iter_events(lines, deadline_s, "text"):
        etype = ev.get("type", "")
        if etype == "response.output_item.done":
            item = ev.get("item") or {}
            if item.get("type") == "message" and (text := _message_text(item).strip()):
                return text
        elif etype in ("response.completed", "response.done"):
            for item in (ev.get("response") or {}).get("output", []):
                if item.get("type") == "message" and (text := _message_text(item).strip()):
                    return text
        else:
            _raise_if_error_event(ev, "text")
    raise ProviderError(
        "OpenAI (Codex) không trả về text nào (stream kết thúc sớm). Thử lại.")
