from .. import config
from .base import BaseNode, Param, Port, register_node


@register_node
class TextPromptNode(BaseNode):
    type_name = "text_prompt"
    title = "Prompt"
    category = "Đầu vào"
    description = "Nhập đoạn text/prompt để nối vào các node khác."
    inputs = []
    outputs = [Port("text", "text", "Text")]
    params = [Param("text", "textarea", "Nội dung", default="")]

    def run(self, inputs, params):
        return {"text": params.get("text") or ""}


@register_node
class LoadImageNode(BaseNode):
    type_name = "load_image"
    title = "Tải ảnh lên"
    category = "Đầu vào"
    description = "Tải một ảnh từ máy lên làm đầu vào cho workflow."
    inputs = []
    outputs = [Port("image", "image", "Ảnh")]
    params = [
        Param("file_id", "image_upload", "Ảnh", default=""),
        Param("image_label", "text", "Mô tả ảnh", default="", is_image_label=True),
    ]

    def run(self, inputs, params):
        file_id = params.get("file_id") or ""
        path = (config.UPLOADS_DIR / file_id).resolve()
        if not file_id or not path.is_relative_to(config.UPLOADS_DIR) or not path.exists():
            raise ValueError("Node 'Tải ảnh lên' chưa có ảnh nào được upload.")
        return {"image": path.read_bytes()}


@register_node
class CombineTextNode(BaseNode):
    type_name = "combine_text"
    title = "Ghép prompt"
    category = "Đầu vào"
    description = "Ghép nhiều đoạn text thành một (mỗi đoạn một dòng). Nối bao nhiêu dây cũng được."
    inputs = [Port("texts", "text", "Các prompt", required=False, multiple=True)]
    outputs = [Port("text", "text", "Text")]
    params = []

    def run(self, inputs, params):
        parts = list(inputs.get("texts") or [])
        # Tương thích workflow lưu trước khi gộp cổng: cổng cũ "a"/"b"
        for legacy in ("a", "b"):
            if inputs.get(legacy):
                parts.append(inputs[legacy])
        return {"text": "\n".join(p.strip() for p in parts if p and p.strip())}
