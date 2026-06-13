from abc import ABC, abstractmethod


class ProviderError(Exception):
    pass


def numbered_image_caption(index: int, label: str) -> str:
    """Caption '<Ảnh N>: <mô tả>' xen NGAY TRƯỚC ảnh khi gửi provider đa-ảnh.

    Neo identity (ảnh nào là ai) chắc hơn liệt kê rời ở đầu prompt — model khó bốc
    nhầm mặt nguồn. Trống → '(không mô tả)'. index 0 → 'Ảnh 1'."""
    return f"Ảnh {index + 1}: {(label or '').strip() or '(không mô tả)'}"


class ImageProvider(ABC):
    """A backend that can generate an image from text and edit an image with a prompt.

    All methods are synchronous; the engine runs them in a thread pool.
    Images are passed around as PNG/JPEG bytes.
    """

    name: str = "base"

    @abstractmethod
    def generate(self, prompt: str, *, model: str = "", aspect_ratio: str = "1:1",
                 **options) -> bytes: ...

    @abstractmethod
    def edit(self, images: list[bytes], prompt: str, *, model: str = "",
             **options) -> bytes: ...

    def generate_text(self, prompt: str, *, model: str = "", system: str = "",
                      **options) -> str:
        """Sinh text bằng LLM (vd: enhance prompt). Provider nào không có LLM
        text (ComfyUI) dùng mặc định này — báo lỗi rõ thay vì crash khó hiểu."""
        raise ProviderError(
            f"Provider '{self.name}' không hỗ trợ sinh text. "
            "Chọn cấu hình Gemini / OpenAI / Codex cho node này.")
