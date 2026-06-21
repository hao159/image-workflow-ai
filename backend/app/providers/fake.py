"""Provider giả lập (kịch bản C) — KHÔNG gọi mạng, không tốn token.

Vẽ prompt lên ảnh PNG placeholder (nền màu theo hash prompt) để test code node
mới offline. Tạo cấu hình provider "fake" trong ⚙ Cài đặt, hoặc bật FORCE_FAKE.
"""
import hashlib
import io
import textwrap

from PIL import Image, ImageDraw

from .base import ImageProvider


class FakeProvider(ImageProvider):
    name = "fake"

    def _bg(self, text: str) -> tuple:
        """Màu nền tối-vừa (theo hash text) để chữ trắng dễ đọc."""
        h = hashlib.md5(text.encode("utf-8")).digest()
        return (40 + h[0] % 120, 40 + h[1] % 120, 40 + h[2] % 120)

    def _size(self, aspect_ratio: str) -> tuple:
        try:
            a, b = (int(x) for x in str(aspect_ratio).split(":"))
            a, b = max(1, a), max(1, b)
        except Exception:  # noqa: BLE001 — tỷ lệ lạ → vuông
            a, b = 1, 1
        base = 512
        if a >= b:
            return base, max(1, round(base * b / a))
        return max(1, round(base * a / b)), base

    def _render(self, text: str, base: bytes = None, size: tuple = (512, 512)) -> bytes:
        if base is not None:
            img = Image.open(io.BytesIO(base)).convert("RGB")
        else:
            img = Image.new("RGB", size, self._bg(text))
        draw = ImageDraw.Draw(img)
        wrapped = textwrap.fill(text, width=max(12, img.width // 12))
        # stroke đen để chữ đọc được trên mọi nền (font mặc định, không cần file font)
        draw.multiline_text((16, 16), wrapped, fill=(255, 255, 255),
                            stroke_width=2, stroke_fill=(0, 0, 0), spacing=4)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def generate(self, prompt: str, *, model: str = "", aspect_ratio: str = "1:1",
                 **options) -> bytes:
        return self._render(f"GEN: {prompt}", size=self._size(aspect_ratio))

    def edit(self, images: list, prompt: str, *, model: str = "", **options) -> bytes:
        return self._render(f"EDIT: {prompt}", base=images[0] if images else None)

    def generate_text(self, prompt: str, *, model: str = "", system: str = "",
                      **options) -> str:
        return f"[fake] {prompt[:120]}"

    def detect_region(self, image: bytes, target: str, *, model: str = "",
                      **options) -> list[float]:
        # Offline: trả vùng giữa ảnh (50%) để test crop --fake không gọi mạng.
        return [0.25, 0.25, 0.75, 0.75]
