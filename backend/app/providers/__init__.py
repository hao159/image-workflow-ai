from .. import db
from .base import ImageProvider, ProviderError
from .comfyui import ComfyUIProvider
from .fake import FakeProvider
from .gemini import GeminiProvider
from .openai_codex import OpenAICodexProvider
from .openai_provider import OpenAIProvider

PROVIDER_CLASSES: dict[str, type[ImageProvider]] = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "codex": OpenAICodexProvider,
    "comfyui": ComfyUIProvider,
    "fake": FakeProvider,  # dev/test offline — không gọi mạng
}

PROVIDER_NAMES = list(PROVIDER_CLASSES)

# Bật toàn cục (vd run_node.py --fake): mọi node AI dùng FakeProvider bất kể config.
FORCE_FAKE = False


def make_provider(provider_name: str, api_key: str = "", base_url: str = "") -> ImageProvider:
    cls = PROVIDER_CLASSES.get(provider_name)
    if cls is None:
        raise ProviderError(f"Provider không hỗ trợ: {provider_name}")
    if provider_name == "fake":
        return cls()  # không cần api_key / mạng
    if provider_name == "comfyui":
        return cls(base_url=base_url)
    if provider_name == "codex":
        return cls()  # token OAuth, không cần api_key
    return cls(api_key=api_key)


def resolve_model_config(selection: str) -> tuple[ImageProvider, str]:
    """Trả về (provider, model mặc định) cho lựa chọn trong node.

    `selection` là tên một cấu hình model trong DB (vd "Google - Gemini 3").
    Provider thô không còn là lựa chọn hợp lệ trong node — phải tạo cấu hình
    đặt tên trong ⚙ Cài đặt model.
    """
    if FORCE_FAKE:
        return FakeProvider(), ""
    cfg = db.get_model_config(selection)
    if cfg:
        provider = make_provider(cfg["provider"], api_key=cfg["api_key"],
                                 base_url=cfg["base_url"])
        return provider, cfg["model"] or ""
    raise ProviderError(
        f"Cấu hình model '{selection}' không tồn tại. Mở ⚙ Cài đặt model để thêm.")


def provider_options() -> list[str]:
    """Danh sách lựa chọn cho param 'provider' của node: chỉ cấu hình đã đặt tên."""
    return [c["name"] for c in db.list_model_configs()]
