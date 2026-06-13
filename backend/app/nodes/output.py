import re
import time

from .. import config
from .base import BaseNode, Param, Port, register_node


@register_node
class SaveImageNode(BaseNode):
    type_name = "save_image"
    title = "Lưu ảnh"
    category = "Đầu ra"
    description = "Lưu ảnh vào thư mục outputs/ và hiển thị kết quả."
    inputs = [Port("image", "image", "Ảnh")]
    outputs = [Port("path", "text", "Đường dẫn")]
    params = [Param("prefix", "text", "Tên file (prefix)", default="result")]

    def run(self, inputs, params):
        image = inputs.get("image")
        if not image:
            raise ValueError("Node 'Lưu ảnh' cần ảnh đầu vào.")
        prefix = re.sub(r"[^\w\-]", "_", params.get("prefix") or "result")
        filename = f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}_{int(time.time()*1000)%1000:03d}.png"
        path = config.OUTPUTS_DIR / filename
        path.write_bytes(image)
        return {"path": f"/api/outputs/{filename}"}
