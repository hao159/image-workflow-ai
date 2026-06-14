"""Provider tạo/sửa ảnh + sinh text OpenAI qua đăng nhập ChatGPT (Codex OAuth).

Khác provider `openai` (SDK + API key): provider này gọi endpoint nội bộ của
ChatGPT `backend-api/codex/responses` (Responses API, trả SSE) bằng access
token OAuth — dùng quota subscription thay vì API credit.

Tạo ảnh qua tool `image_generation`; server stream về base64 PNG.
Sinh text (enhance prompt...) gọi cùng endpoint, không kèm tool.
"""
import base64
import uuid

import httpx

from .base import (ImageProvider, ProviderError, numbered_image_caption,
                   parse_bbox_json, parse_critique_json)
from .codex_debug_log import CodexDebugLog
# _parse_image_from_sse re-export tại đây cho test_codex.py import  # noqa: F401
from .codex_sse_parsers import _parse_image_from_sse, _parse_text_from_sse
from .openai_codex_oauth import get_valid_access_token
from .openai_provider import ASPECT_TO_SIZE

RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"
DEFAULT_MODEL = "gpt-5.5"  # model "host"; tool image_generation tự dùng gpt-image
ORIGINATOR = "codex_cli_rs"
# Version client gửi trong header — server gate model mới (vd gpt-5.5) theo giá trị
# này. Lấy từ client_version trong ~/.codex/models_cache.json (Codex thật dùng).
CODEX_VERSION = "0.124.0"
# Endpoint codex/responses bắt buộc có "instructions" (system prompt) — thiếu → 400.
IMAGE_INSTRUCTIONS = "You are an image generation assistant. Use the image_generation tool to create the requested image."
TEXT_INSTRUCTIONS = "You are a helpful writing assistant."
VISION_INSTRUCTIONS = "You are a vision analysis assistant. Inspect the image and reply with ONLY the requested JSON object — no prose, no code fences."
# Trần thời gian cả request (giây). httpx timeout=180 chỉ là timeout MỖI lần đọc
# — server cứ nhỏ giọt event thì request chạy vô hạn; trần này chặn lại.
TOTAL_DEADLINE_S = 300


class OpenAICodexProvider(ImageProvider):
    name = "codex"

    def __init__(self, *_args, **_kwargs):
        # Không nhận api_key/base_url — token lấy từ ~/.codex/auth.json lúc gọi.
        pass

    # ---------- public API ----------

    def generate(self, prompt: str, *, model: str = "", aspect_ratio: str = "1:1",
                 **options) -> bytes:
        content = [{"type": "input_text", "text": prompt}]
        return self._request_image(model or DEFAULT_MODEL, content,
                                   size=ASPECT_TO_SIZE.get(aspect_ratio, "1024x1024"))

    def edit(self, images: list[bytes], prompt: str, *, model: str = "",
             image_labels: list[str] | None = None, **options) -> bytes:
        # Xen caption "Ảnh N: <tên>" ngay trước từng ảnh (nếu có nhãn) → model neo
        # đúng ảnh-nào-là-ai. Không nhãn → ảnh trần như cũ (backward compat).
        content: list[dict] = [{"type": "input_text", "text": prompt}]
        for i, img in enumerate(images):
            if image_labels:
                label = image_labels[i] if i < len(image_labels) else ""
                content.append({"type": "input_text",
                                "text": numbered_image_caption(i, label)})
            data_url = "data:image/png;base64," + base64.b64encode(img).decode()
            content.append({"type": "input_image", "image_url": data_url})
        try:
            return self._request_image(model or DEFAULT_MODEL, content)
        except ProviderError:
            raise
        except Exception as e:  # noqa: BLE001
            raise ProviderError(
                "Sửa ảnh qua OpenAI (Codex) thất bại. Nếu lặp lại, dùng cấu hình "
                f"OpenAI API key cho node Sửa ảnh. Chi tiết: {e}") from e

    def generate_text(self, prompt: str, *, model: str = "", system: str = "",
                      **options) -> str:
        # Model ảnh (gpt-image-*) không sinh text — rơi về model host mặc định.
        use_model = model or DEFAULT_MODEL
        if "image" in use_model:
            use_model = DEFAULT_MODEL
        body = {
            "model": use_model,
            "instructions": system or TEXT_INSTRUCTIONS,
            "input": [{"role": "user",
                       "content": [{"type": "input_text", "text": prompt}]}],
            "stream": True,
            "store": False,
        }
        return self._stream_request(body, _parse_text_from_sse)

    def detect_region(self, image: bytes, target: str, *, model: str = "",
                      **options) -> list[float]:
        """Tìm bbox của `target` qua model vision (gpt-5.5 multimodal). Toạ độ lưới
        0..999 (chuẩn OpenAI) → chuẩn hóa /999 về 0..1."""
        instruction = (
            f'Find the object: "{target}" in the image. '
            'Return JSON {"found": true|false, "box": [x_min, y_min, x_max, y_max]} '
            'with INTEGER coordinates on a 0..999 grid (top-left origin, x_max>x_min, '
            'y_max>y_min), box tight around the object. Not found → {"found": false}.')
        return parse_bbox_json(self._vision_json(image, instruction, model),
                               scale=999.0, target=target)

    def critique_image(self, image: bytes, goal: str, criteria: str = "", *,
                       model: str = "", **options) -> dict:
        """Chấm ảnh vs mục tiêu (harness critic) qua model vision → JSON."""
        crit = f"\nUser acceptance criteria: {criteria}" if (criteria or "").strip() else ""
        instruction = (
            "You are a strict judge scoring an AI-generated image against a GOAL.\n"
            f"Goal: {goal}{crit}\n"
            'Return JSON {"score": 0..10 number, "passed": true|false, '
            '"feedback": "short, concrete fix to reach the goal"}. '
            "passed=true only if the image is product-ready for the goal.")
        return parse_critique_json(self._vision_json(image, instruction, model))

    # ---------- internal ----------

    def _vision_json(self, image: bytes, instruction: str, model: str = "") -> str:
        """Gửi ẢNH + instruction ở chế độ TEXT (không tool sinh ảnh) → trả text JSON.
        Model "-image" chỉ sinh ảnh → swap về host multimodal mặc định."""
        use_model = model or DEFAULT_MODEL
        if "image" in use_model:
            use_model = DEFAULT_MODEL
        data_url = "data:image/png;base64," + base64.b64encode(image).decode()
        body = {
            "model": use_model,
            "instructions": VISION_INSTRUCTIONS,
            "input": [{"role": "user", "content": [
                {"type": "input_text", "text": instruction},
                {"type": "input_image", "image_url": data_url},
            ]}],
            "stream": True,
            "store": False,
        }
        return self._stream_request(body, _parse_text_from_sse)

    def _headers(self, access_token: str, account_id: str) -> dict:
        return {
            "Authorization": f"Bearer {access_token}",
            "chatgpt-account-id": account_id,
            "OpenAI-Beta": "responses=experimental",
            "originator": ORIGINATOR,
            "session_id": str(uuid.uuid4()),
            "version": CODEX_VERSION,
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

    def _request_image(self, model: str, content: list[dict],
                       size: str = "auto") -> bytes:
        tool: dict = {"type": "image_generation"}
        if size and size != "auto":
            tool["size"] = size
        body = {
            "model": model,
            "instructions": IMAGE_INSTRUCTIONS,
            "input": [{"role": "user", "content": content}],
            "tools": [tool],
            "tool_choice": "auto",
            "stream": True,
            "store": False,
        }
        return self._stream_request(body, _parse_image_from_sse)

    def _stream_request(self, body: dict, parse):
        """POST body lên endpoint Codex, đưa SSE stream qua `parse`, trả kết quả."""
        access_token, account_id = get_valid_access_token()
        log = CodexDebugLog()  # no-op nếu CODEX_DEBUG tắt
        log.request(RESPONSES_URL, body)
        hint = f" — xem log: {log.path}" if log.path else ""
        try:
            with httpx.stream("POST", RESPONSES_URL, json=body,
                              headers=self._headers(access_token, account_id),
                              timeout=180) as resp:
                log.status(resp.status_code)
                if resp.status_code >= 400:
                    detail = resp.read().decode(errors="replace")[:400]
                    raise ProviderError(
                        f"OpenAI (Codex) trả lỗi HTTP {resp.status_code}: {detail}")
                result = parse(log.tee(resp.iter_lines()),
                               deadline_s=TOTAL_DEADLINE_S)
                log.done(f"OK — kết quả {len(result)} bytes/ký tự")
                return result
        except httpx.HTTPError as e:
            log.done(f"LỖI mạng: {e}")
            raise ProviderError(f"Không gọi được endpoint Codex: {e}{hint}") from e
        except ProviderError as e:
            log.done(f"LỖI: {e}")
            if hint:
                raise ProviderError(f"{e}{hint}") from e
            raise
        finally:
            log.close()
