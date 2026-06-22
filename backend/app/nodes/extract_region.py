"""Node "Trích vùng (AI)" — trích/crop một đối tượng theo mô tả.

Vision model trả bbox CHUẨN HÓA [x0,y0,x1,y1] (0..1) cho đối tượng mô tả; backend
crop bằng PIL (GIỮ NGUYÊN pixel gốc — không qua model sinh ảnh). Tổng quát: mô tả gì
trích nấy (mặt/bò/chó/áo). Dùng làm bước pre-process tin cậy trước khi ghép ảnh.
"""
import io

from PIL import Image

from ..providers import provider_options, resolve_model_config
from .base import BaseNode, Param, Port, register_node
from ._errors import NodeInputError
from .prompt_merge import merge_prompt


def crop_region(data: bytes, bbox, padding: float = 0.08) -> bytes:
    """Crop ảnh theo bbox chuẩn hóa 0..1, nới `padding` (theo cạnh box) + clamp khung.

    bbox không hợp lệ (sai số phần tử / ngoài [0,1] / đảo cạnh) → ValueError."""
    if not (isinstance(bbox, (list, tuple)) and len(bbox) == 4):
        raise ValueError(f"bbox phải có 4 số [x0,y0,x1,y1], nhận: {bbox}")
    x0, y0, x1, y1 = (float(v) for v in bbox)
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise ValueError(f"bbox ngoài [0,1] hoặc cạnh đảo: {bbox}")
    img = Image.open(io.BytesIO(data))
    w, h = img.size
    bw, bh = (x1 - x0) * w, (y1 - y0) * h
    px0 = max(0, int(round(x0 * w - padding * bw)))
    py0 = max(0, int(round(y0 * h - padding * bh)))
    px1 = min(w, int(round(x1 * w + padding * bw)))
    py1 = min(h, int(round(y1 * h + padding * bh)))
    buf = io.BytesIO()
    img.crop((px0, py0, px1, py1)).save(buf, format="PNG")
    return buf.getvalue()


@register_node
class ExtractRegionNode(BaseNode):
    type_name = "extract_region"
    title = "Trích vùng (AI)"
    category = "AI"
    description = ("Trích/crop một đối tượng theo mô tả (mặt/người/áo/con vật...). "
                   "AI tìm vùng → crop giữ nguyên pixel gốc. Mô tả càng rõ càng đúng.")
    inputs = [
        Port("image", "image", "Ảnh"),
        Port("target", "text", "Mô tả đối tượng", required=False),
    ]
    outputs = [Port("image", "image", "Ảnh")]
    # Crop kế thừa nhãn ảnh nguồn nếu không đặt mô tả riêng (giống node Biến đổi).
    label_passthrough_from = "image"
    params = [
        Param("provider", "select", "Model / Provider (vision)", default="",
              dynamic_options=provider_options),
        Param("target", "textarea", "Mô tả đối tượng cần trích", default="",
              supplement_for="target", supplement_label="Mô tả bổ sung"),
        Param("padding", "number", "Nới viền (tỷ lệ)", default=0.08,
              min=0.0, max=1.0, step=0.02),
        Param("image_label", "text", "Mô tả ảnh (đặt tên crop)", default="",
              is_image_label=True),
    ]

    def run(self, inputs, params):
        image = inputs.get("image")
        if not image:
            raise NodeInputError("Node 'Trích vùng' cần ảnh đầu vào.", "extract_no_image")
        target = merge_prompt(inputs.get("target"), params.get("target"))
        if not target.strip():
            raise NodeInputError(
                "Node 'Trích vùng' cần mô tả đối tượng cần trích.", "extract_no_target")
        provider, model = resolve_model_config(params["provider"])
        bbox = provider.detect_region(image, target, model=model)
        # padding=0.0 hợp lệ (crop sát) → KHÔNG dùng `or` (0.0 falsy → rơi default).
        pad = params.get("padding")
        crop = crop_region(image, bbox, 0.08 if pad is None else float(pad))
        return {"image": crop}
