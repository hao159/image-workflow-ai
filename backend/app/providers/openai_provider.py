import base64
import io

from .. import config
from .base import ImageProvider, ProviderError

DEFAULT_MODEL = "gpt-image-1"
# Model cho sinh text (enhance prompt...). gpt-image-* chỉ trả ảnh — nếu cấu
# hình đang trỏ model ảnh thì tự thay bằng model này.
TEXT_DEFAULT_MODEL = "gpt-4o-mini"

# gpt-image-1 chỉ chấp nhận các size cố định; map từ aspect ratio gần nhất
ASPECT_TO_SIZE = {
    "1:1": "1024x1024",
    "3:2": "1536x1024",
    "16:9": "1536x1024",
    "2:3": "1024x1536",
    "9:16": "1024x1536",
}


class OpenAIProvider(ImageProvider):
    name = "openai"

    def __init__(self, api_key: str = ""):
        self._api_key = api_key or config.OPENAI_API_KEY
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise ProviderError(
                    "Chưa có API key cho OpenAI. Thêm cấu hình trong ⚙ Cài đặt model "
                    "hoặc đặt OPENAI_API_KEY trong file .env.")
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def generate(self, prompt: str, *, model: str = "", aspect_ratio: str = "1:1",
                 **options) -> bytes:
        client = self._get_client()
        result = client.images.generate(
            model=model or DEFAULT_MODEL,
            prompt=prompt,
            size=ASPECT_TO_SIZE.get(aspect_ratio, "1024x1024"),
            n=1,
        )
        b64 = result.data[0].b64_json
        if not b64:
            raise ProviderError("OpenAI không trả về dữ liệu ảnh.")
        return base64.b64decode(b64)

    def generate_text(self, prompt: str, *, model: str = "", system: str = "",
                      **options) -> str:
        client = self._get_client()
        use_model = model or TEXT_DEFAULT_MODEL
        if "image" in use_model:
            use_model = TEXT_DEFAULT_MODEL
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(model=use_model, messages=messages)
        if not resp.choices:
            raise ProviderError("OpenAI không trả về lựa chọn nào (có thể bị content filter).")
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            raise ProviderError("OpenAI không trả về text nào.")
        return text

    def edit(self, images: list[bytes], prompt: str, *, model: str = "",
             **options) -> bytes:
        client = self._get_client()
        files = []
        for i, img in enumerate(images):
            f = io.BytesIO(img)
            f.name = f"input_{i}.png"
            files.append(f)
        result = client.images.edit(
            model=model or DEFAULT_MODEL,
            image=files if len(files) > 1 else files[0],
            prompt=prompt,
            n=1,
        )
        b64 = result.data[0].b64_json
        if not b64:
            raise ProviderError("OpenAI không trả về dữ liệu ảnh.")
        return base64.b64decode(b64)
