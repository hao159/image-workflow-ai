import io

from PIL import Image, ImageEnhance, ImageFilter

from .base import BaseNode, Param, Port, register_node


def _to_pil(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGBA")


def _to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@register_node
class ResizeNode(BaseNode):
    type_name = "resize"
    title = "Resize"
    category = "Biến đổi"
    description = "Đổi kích thước ảnh (giữ tỷ lệ nếu chọn)."
    inputs = [Port("image", "image", "Ảnh")]
    outputs = [Port("image", "image", "Ảnh")]
    label_passthrough_from = "image"  # nhãn mô tả ảnh sống sót qua node
    params = [
        Param("width", "number", "Rộng (px)", default=1024, min=1, max=8192, step=1),
        Param("height", "number", "Cao (px)", default=1024, min=1, max=8192, step=1),
        Param("keep_aspect", "checkbox", "Giữ tỷ lệ", default=True),
    ]

    def run(self, inputs, params):
        img = _to_pil(inputs["image"])
        w, h = int(params["width"]), int(params["height"])
        if params.get("keep_aspect"):
            img.thumbnail((w, h), Image.LANCZOS)
        else:
            img = img.resize((w, h), Image.LANCZOS)
        return {"image": _to_bytes(img)}


@register_node
class FilterNode(BaseNode):
    type_name = "filter"
    title = "Bộ lọc"
    category = "Biến đổi"
    description = "Áp bộ lọc đơn giản: trắng đen, làm mờ, làm nét..."
    inputs = [Port("image", "image", "Ảnh")]
    outputs = [Port("image", "image", "Ảnh")]
    label_passthrough_from = "image"  # nhãn mô tả ảnh sống sót qua node
    params = [
        Param("filter", "select", "Bộ lọc", default="grayscale",
              options=["grayscale", "blur", "sharpen", "contour", "edge_enhance"]),
        Param("radius", "number", "Độ mờ (blur)", default=4, min=1, max=50, step=1),
    ]

    def run(self, inputs, params):
        img = _to_pil(inputs["image"])
        f = params.get("filter")
        if f == "grayscale":
            img = img.convert("L").convert("RGBA")
        elif f == "blur":
            img = img.filter(ImageFilter.GaussianBlur(int(params.get("radius") or 4)))
        elif f == "sharpen":
            img = img.filter(ImageFilter.SHARPEN)
        elif f == "contour":
            img = img.convert("RGB").filter(ImageFilter.CONTOUR).convert("RGBA")
        elif f == "edge_enhance":
            img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
        return {"image": _to_bytes(img)}


@register_node
class AdjustNode(BaseNode):
    type_name = "adjust"
    title = "Chỉnh màu"
    category = "Biến đổi"
    description = "Chỉnh độ sáng, tương phản, bão hòa màu."
    inputs = [Port("image", "image", "Ảnh")]
    outputs = [Port("image", "image", "Ảnh")]
    label_passthrough_from = "image"  # nhãn mô tả ảnh sống sót qua node
    params = [
        Param("brightness", "number", "Độ sáng", default=1.0, min=0.1, max=3.0, step=0.1),
        Param("contrast", "number", "Tương phản", default=1.0, min=0.1, max=3.0, step=0.1),
        Param("saturation", "number", "Bão hòa", default=1.0, min=0.0, max=3.0, step=0.1),
    ]

    def run(self, inputs, params):
        img = _to_pil(inputs["image"]).convert("RGB")
        img = ImageEnhance.Brightness(img).enhance(float(params["brightness"]))
        img = ImageEnhance.Contrast(img).enhance(float(params["contrast"]))
        img = ImageEnhance.Color(img).enhance(float(params["saturation"]))
        return {"image": _to_bytes(img.convert("RGBA"))}
