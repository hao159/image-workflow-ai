import json as _json
from abc import ABC, abstractmethod


class ProviderError(Exception):
    pass


class ProviderErrorWithCode(ProviderError):
    """ProviderError carrying a stable i18n error code slug."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def _extract_json_obj(text: str) -> dict:
    """Parse JSON object từ phản hồi model; bóc cụm {...} nếu có code-fence/rác bao."""
    text = (text or "").strip()
    if not text:
        raise ProviderError("Model không trả về kết quả.")
    try:
        return _json.loads(text)
    except _json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ProviderError(f"Model trả JSON sai: {text[:200]}")
        return _json.loads(text[start:end + 1])


def parse_bbox_json(text: str, scale: float = 1.0, target: str = "") -> list[float]:
    """Parse {"found":bool,"box":[x0,y0,x1,y1]} → bbox CHUẨN HÓA 0..1 (chia `scale`).

    scale=1.0 cho toạ độ 0..1 (Gemini); scale=999.0 cho lưới 0..999 (OpenAI khuyến nghị).
    found=false / thiếu box / box sai 4 phần tử → ProviderError."""
    data = _extract_json_obj(text)
    box = data.get("box")
    if not data.get("found", True) or not box:
        raise ProviderErrorWithCode(
            f"Không tìm thấy '{target}' trong ảnh. Thử mô tả khác hoặc ảnh rõ hơn."
            if target else "Không tìm thấy đối tượng trong ảnh.",
            "region_not_found")
    if not (isinstance(box, (list, tuple)) and len(box) == 4):
        raise ProviderError(f"bbox không hợp lệ (cần 4 số): {box}")
    return [float(v) / scale for v in box]


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
        text dùng mặc định này — báo lỗi rõ thay vì crash khó hiểu."""
        raise ProviderErrorWithCode(
            f"Provider '{self.name}' không hỗ trợ sinh text. "
            "Chọn cấu hình Gemini / OpenAI / Codex cho node này.",
            "provider_no_text_support")

    def detect_region(self, image: bytes, target: str, *, model: str = "",
                      **options) -> list[float]:
        """Tìm bbox CHUẨN HÓA [x0,y0,x1,y1] (0..1) của đối tượng `target` trong ảnh
        (node Trích vùng). Provider không vision dùng mặc định này → báo lỗi rõ."""
        raise ProviderErrorWithCode(
            f"Provider '{self.name}' không hỗ trợ trích vùng (detect_region). "
            "Dùng cấu hình Gemini cho node Trích vùng.",
            "provider_no_vision_support")
