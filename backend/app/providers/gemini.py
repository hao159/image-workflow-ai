from .. import config
from .base import (ImageProvider, ProviderError, ProviderErrorWithCode,
                   numbered_image_caption, parse_bbox_json)

DEFAULT_MODEL = "gemini-2.5-flash-image"
# Model cho sinh text (enhance prompt...). Model "-image" chỉ trả ảnh nên
# không dùng được — nếu cấu hình đang trỏ model ảnh thì tự thay bằng model này.
TEXT_DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiProvider(ImageProvider):
    name = "gemini"

    def __init__(self, api_key: str = ""):
        self._api_key = api_key or config.GEMINI_API_KEY
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise ProviderErrorWithCode(
                    "Chưa có API key cho Gemini. Thêm cấu hình trong ⚙ Cài đặt model "
                    "hoặc đặt GEMINI_API_KEY trong file .env.",
                    "gemini_no_api_key")
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _extract_image(self, response) -> bytes:
        for part in response.parts or []:
            if part.inline_data and part.inline_data.data:
                return part.inline_data.data
        text = getattr(response, "text", None)
        raise ProviderErrorWithCode(
            f"Gemini không trả về ảnh nào. Phản hồi: {text or 'rỗng'}",
            "provider_no_image")

    def generate(self, prompt: str, *, model: str = "", aspect_ratio: str = "1:1",
                 **options) -> bytes:
        from google.genai import types
        client = self._get_client()
        response = client.models.generate_content(
            model=model or DEFAULT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
            ),
        )
        return self._extract_image(response)

    def generate_text(self, prompt: str, *, model: str = "", system: str = "",
                      **options) -> str:
        from google.genai import types
        client = self._get_client()
        use_model = model or TEXT_DEFAULT_MODEL
        if "image" in use_model:
            use_model = TEXT_DEFAULT_MODEL
        response = client.models.generate_content(
            model=use_model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system or None),
        )
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise ProviderErrorWithCode("Gemini không trả về text nào.", "provider_no_text")
        return text

    def detect_region(self, image: bytes, target: str, *, model: str = "",
                      **options) -> list[float]:
        """Tìm bbox chuẩn hóa [x0,y0,x1,y1] (0..1) của `target` trong ảnh.

        Dùng model vision TEXT (model "-image" chỉ trả ảnh → tự swap). Ép JSON. Không
        thấy → ProviderError rõ; JSON sai → ProviderError."""
        from google.genai import types
        client = self._get_client()
        use_model = model or TEXT_DEFAULT_MODEL
        if "image" in use_model:
            use_model = TEXT_DEFAULT_MODEL
        instruction = (
            f"Tìm đối tượng sau trong ảnh: \"{target}\".\n"
            "Trả JSON đúng schema: {\"found\": true/false, \"box\": [x0,y0,x1,y1]}. "
            "Toạ độ CHUẨN HÓA 0..1: (x0,y0) góc trên-trái, (x1,y1) góc dưới-phải, "
            "x0<x1, y0<y1. Khung bao SÁT đối tượng. Không thấy → {\"found\": false}.")
        response = client.models.generate_content(
            model=use_model,
            contents=[types.Part.from_bytes(data=image, mime_type="image/png"),
                      instruction],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT"], response_mime_type="application/json"),
        )
        # Gemini trả toạ độ 0..1 → scale=1.0
        return parse_bbox_json(getattr(response, "text", None) or "",
                               scale=1.0, target=target)

    def edit(self, images: list[bytes], prompt: str, *, model: str = "",
             image_labels: list[str] | None = None, **options) -> bytes:
        from google.genai import types
        client = self._get_client()
        # Xen caption "Ảnh N: <tên>" ngay trước từng Part ảnh (nếu có nhãn) → model
        # neo đúng ảnh-nào-là-ai. Không nhãn → ảnh trần như cũ (backward compat).
        contents: list = [prompt]
        for i, img in enumerate(images):
            if image_labels:
                label = image_labels[i] if i < len(image_labels) else ""
                contents.append(numbered_image_caption(i, label))
            contents.append(types.Part.from_bytes(data=img, mime_type="image/png"))
        response = client.models.generate_content(
            model=model or DEFAULT_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
        return self._extract_image(response)
