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

    def critique_image(self, image: bytes, goal: str, criteria: str = "", *,
                       model: str = "", **options) -> dict:
        """Chấm ảnh so mục tiêu (harness critic) — trả {score:0..10, passed:bool,
        feedback:str}. Provider không có vision (ComfyUI/OpenAI Images/Codex) dùng
        mặc định này → báo lỗi rõ. Engine kiểm tra `supports_critique()` TRƯỚC khi
        chạy nên không tốn lượt sinh ảnh rồi mới chết."""
        raise ProviderError(
            f"Provider '{self.name}' không hỗ trợ chấm ảnh (harness). "
            "Cấu hình một critic Gemini trong ⚙ Cài đặt.")

    @classmethod
    def supports_critique(cls) -> bool:
        """True nếu provider override critique_image (có vision chấm ảnh)."""
        return cls.critique_image is not ImageProvider.critique_image

    def detect_region(self, image: bytes, target: str, *, model: str = "",
                      **options) -> list[float]:
        """Tìm bbox CHUẨN HÓA [x0,y0,x1,y1] (0..1) của đối tượng `target` trong ảnh
        (node Trích vùng). Provider không vision dùng mặc định này → báo lỗi rõ."""
        raise ProviderError(
            f"Provider '{self.name}' không hỗ trợ trích vùng (detect_region). "
            "Dùng cấu hình Gemini cho node Trích vùng.")
